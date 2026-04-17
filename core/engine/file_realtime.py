import asyncio
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from uuid import uuid4

from watchfiles import Change, watch


@dataclass
class _Subscriber:
    dir_path: str
    file_path: str | None
    queue: asyncio.Queue[dict[str, Any]]
    loop: asyncio.AbstractEventLoop


def _normalize_watch_change(change: Change) -> str:
    if change == Change.added:
        return "created"
    if change == Change.deleted:
        return "deleted"
    return "modified"


def path_within_scope(path: str, dir_path: str, file_path: str | None) -> bool:
    if file_path and path == file_path:
        return True
    if dir_path == "/":
        return True
    return path == dir_path or path.startswith(f"{dir_path}/")


class FileRealtimeHub:
    def __init__(
        self,
        roots: Path | Iterable[Path] | Callable[[], Iterable[Path]],
        *,
        skip_dir_names: set[str] | frozenset[str],
        normalize_path: Callable[[Path], str | None],
    ) -> None:
        self._roots_source = roots
        self._skip_dir_names = set(skip_dir_names)
        self._normalize_path = normalize_path
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = threading.Lock()
        self._started = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._revision = 0
        self._last_error: str | None = None
        self._last_error_at: int | None = None
        self._last_event_at: int | None = None
        self._last_start_at: int | None = None

    def ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._last_start_at = int(time.time() * 1000)
            self._thread = threading.Thread(
                target=self._watch_loop,
                name="file-realtime-watch",
                daemon=True,
            )
            self._thread.start()
            self._started = True

    def subscribe(
        self,
        *,
        dir_path: str,
        file_path: str | None,
        queue: asyncio.Queue[dict[str, Any]],
        loop: asyncio.AbstractEventLoop,
    ) -> str:
        self.ensure_started()
        subscriber_id = uuid4().hex
        with self._lock:
            self._subscribers[subscriber_id] = _Subscriber(
                dir_path=dir_path,
                file_path=file_path,
                queue=queue,
                loop=loop,
            )
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def status(self) -> dict[str, Any]:
        with self._lock:
            thread_alive = self._thread is not None and self._thread.is_alive()
            return {
                "healthy": bool(self._started and thread_alive),
                "started": self._started,
                "thread_alive": thread_alive,
                "subscriber_count": len(self._subscribers),
                "last_error": self._last_error,
                "last_error_at": self._last_error_at,
                "last_event_at": self._last_event_at,
                "last_start_at": self._last_start_at,
            }

    def _resolve_roots(self) -> list[Path]:
        source = self._roots_source() if callable(self._roots_source) else self._roots_source
        if isinstance(source, Path):
            items = [source]
        else:
            items = list(source)

        roots: list[Path] = []
        seen: set[str] = set()
        for item in items:
            try:
                resolved = Path(item).resolve()
            except OSError:
                continue
            key = os.path.normcase(str(resolved))
            if key in seen or not resolved.exists():
                continue
            seen.add(key)
            roots.append(resolved)
        return roots

    def _watch_filter(self, _change: Change, raw_path: str) -> bool:
        path = Path(raw_path)
        for part in path.parts:
            if part in self._skip_dir_names:
                return False
        return True

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    self._last_error = None
                    self._last_error_at = None
                roots = self._resolve_roots()
                if not roots:
                    self._record_error("no file watcher roots configured")
                    time.sleep(1.0)
                    continue
                for changes in watch(
                    *roots,
                    watch_filter=self._watch_filter,
                    stop_event=self._stop_event,
                    debounce=150,
                    step=50,
                    raise_interrupt=False,
                ):
                    if self._stop_event.is_set():
                        break
                    payload_paths: list[dict[str, str]] = []
                    seen: set[tuple[str, str]] = set()
                    for change, raw_path in changes:
                        normalized = self._normalize_path(Path(raw_path))
                        if not normalized:
                            continue
                        change_name = _normalize_watch_change(change)
                        key = (normalized, change_name)
                        if key in seen:
                            continue
                        seen.add(key)
                        payload_paths.append(
                            {
                                "path": normalized,
                                "kind": "file",
                                "change": change_name,
                            }
                        )
                    if not payload_paths:
                        continue
                    self._publish(payload_paths)
                if self._stop_event.is_set():
                    break
                self._record_error("file watcher stopped unexpectedly")
            except Exception as exc:
                self._record_error(str(exc))
            if not self._stop_event.is_set():
                time.sleep(1.0)

    def _publish(self, payload_paths: list[dict[str, str]]) -> None:
        with self._lock:
            self._revision += 1
            revision = self._revision
            self._last_event_at = int(time.time() * 1000)
            subscribers = list(self._subscribers.items())
        event = {
            "revision": revision,
            "paths": payload_paths,
            "timestamp": int(time.time() * 1000),
        }
        stale_subscribers: list[str] = []
        for subscriber_id, subscriber in subscribers:
            if not any(
                path_within_scope(item["path"], subscriber.dir_path, subscriber.file_path)
                for item in payload_paths
            ):
                continue
            try:
                subscriber.loop.call_soon_threadsafe(self._deliver, subscriber.queue, event)
            except RuntimeError:
                stale_subscribers.append(subscriber_id)
        if stale_subscribers:
            with self._lock:
                for subscriber_id in stale_subscribers:
                    self._subscribers.pop(subscriber_id, None)

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message
            self._last_error_at = int(time.time() * 1000)

    @staticmethod
    def _deliver(queue: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(event)
