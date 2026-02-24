import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from settings import (
    DISCORD_BUFFER_MSG_COUNT,
    DISCORD_MAX_BUFFER_TOKENS,
    DISCORD_SESSIONS_DIR,
    logger,
)

CHARS_PER_TOKEN = 3
MAX_BUFFER_CHARS = DISCORD_MAX_BUFFER_TOKENS * CHARS_PER_TOKEN
SUMMARISE_TRIGGER_CHARS = int(MAX_BUFFER_CHARS * 0.75)

SUMMARISE_SYSTEM_PROMPT = (
    "You are a conversation summariser. Condense the following conversation messages "
    "into a brief summary capturing key facts, user preferences, important decisions, "
    "and any information needed to continue the conversation naturally. "
    "Output only the summary text, no preamble."
)


class ChatSession:
    """Manages one channel's three-tier memory.

    The JSONL file is **append-only** — it is the complete Tier-3 history.
    Summary marker lines are appended (never overwrite) so that the full
    conversation record is preserved for crash recovery and auditing.
    On load, the *last* summary marker becomes Tier-1 and only messages
    *after* that marker populate Tier-2.
    """

    def __init__(self, channel_id: str, sessions_dir: Optional[Path] = None) -> None:
        self.channel_id = channel_id
        self.summary: str = ""
        self.buffer: List[Dict[str, str]] = []
        self.channel_name: str = ""
        self.is_dm: bool = False
        self._sessions_dir = sessions_dir or DISCORD_SESSIONS_DIR
        self._cache_path = self._sessions_dir / f"{channel_id}.jsonl"
        self._meta_path = self._sessions_dir / f"{channel_id}.meta.json"
        self._total_chars = 0
        self._lock = asyncio.Lock()

    @property
    def cache_path(self) -> Path:
        return self._cache_path

    def add_message(self, role: str, message: str) -> None:
        entry = {"role": role, "message": message}
        self.buffer.append(entry)
        self._total_chars += len(message)
        self._append_to_cache(entry)

    def get_llm_messages(self) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if self.summary:
            messages.append({"role": "system", "content": self.summary})
        for msg in self.buffer:
            role = msg["role"]
            if role == "system":
                continue
            messages.append({"role": role, "content": msg["message"]})
        return messages

    def needs_summarisation(self) -> bool:
        total = len(self.summary) + self._total_chars
        return total > SUMMARISE_TRIGGER_CHARS

    def summarise(self, llm_fn: Callable[[List[Dict[str, Any]]], str]) -> None:
        if len(self.buffer) <= 1:
            return

        half = max(1, len(self.buffer) // 2)
        old_messages = self.buffer[:half]

        old_text = "\n".join(
            f"{m['role']}: {m['message']}" for m in old_messages
        )
        context = f"Previous summary:\n{self.summary}\n\nNew messages to summarise:\n{old_text}" if self.summary else old_text

        summary_messages = [
            {"role": "system", "content": SUMMARISE_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
        self.summary = llm_fn(summary_messages)

        self.buffer = self.buffer[half:]
        self._recalc_chars()

        # Append summary marker to the JSONL (never rewrite — Tier 3 stays complete).
        self._append_to_cache({"role": "system", "type": "summary", "message": self.summary})

    def set_channel_info(self, name: str, is_dm: bool) -> None:
        """Persist channel display name and type to a sidecar meta file."""
        if self.channel_name == name and self.is_dm == is_dm:
            return
        self.channel_name = name
        self.is_dm = is_dm
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._meta_path.write_text(
                json.dumps({"channel_name": name, "is_dm": is_dm}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to write discord session meta %s: %s", self._meta_path, exc)

    def _load_meta(self) -> None:
        if not self._meta_path.exists():
            return
        try:
            data = json.loads(self._meta_path.read_text(encoding="utf-8"))
            self.channel_name = str(data.get("channel_name") or "")
            self.is_dm = bool(data.get("is_dm", False))
        except Exception:
            pass

    def load_from_cache(self) -> None:
        self._load_meta()
        if not self._cache_path.exists():
            return

        self.summary = ""
        all_entries: List[Dict[str, str]] = []
        last_summary_idx = -1

        lines = self._cache_path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            all_entries.append(entry)
            if entry.get("type") == "summary":
                last_summary_idx = len(all_entries) - 1

        # Use the last summary marker as Tier-1.
        if last_summary_idx >= 0:
            self.summary = all_entries[last_summary_idx].get("message", "")
            # Tier-2 buffer = messages after the last summary marker.
            post_summary = [
                e for e in all_entries[last_summary_idx + 1:]
                if e.get("type") != "summary"
            ]
        else:
            post_summary = [e for e in all_entries if e.get("type") != "summary"]

        self.buffer = [
            {"role": e["role"], "message": e["message"]}
            for e in post_summary
        ]

        # Keep only the most recent messages in the buffer.
        if len(self.buffer) > DISCORD_BUFFER_MSG_COUNT:
            self.buffer = self.buffer[-DISCORD_BUFFER_MSG_COUNT:]

        self._recalc_chars()

    def _append_to_cache(self, entry: Dict[str, str]) -> None:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_full_history(self) -> List[Dict[str, str]]:
        """Read the complete Tier-3 JSONL history for audit display."""
        if not self._cache_path.exists():
            return []
        entries: List[Dict[str, str]] = []
        for line in self._cache_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(entry)
        return entries

    def get_message_count(self) -> int:
        """Return the total number of non-summary messages in the JSONL cache."""
        if not self._cache_path.exists():
            return 0
        count = 0
        for line in self._cache_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "summary":
                count += 1
        return count

    def _recalc_chars(self) -> None:
        self._total_chars = sum(len(m["message"]) for m in self.buffer)


class SessionManager:
    def __init__(self, sessions_dir: Optional[Path] = None) -> None:
        self._sessions_dir = sessions_dir or DISCORD_SESSIONS_DIR
        self._sessions: Dict[str, ChatSession] = {}

    def get_or_create(self, channel_id: str) -> ChatSession:
        if channel_id not in self._sessions:
            session = ChatSession(channel_id, self._sessions_dir)
            session.load_from_cache()
            self._sessions[channel_id] = session
        return self._sessions[channel_id]

    def load_all(self) -> int:
        if not self._sessions_dir.exists():
            return 0

        count = 0
        for path in self._sessions_dir.glob("*.jsonl"):
            channel_id = path.stem
            if channel_id not in self._sessions:
                session = ChatSession(channel_id, self._sessions_dir)
                session.load_from_cache()
                self._sessions[channel_id] = session
                count += 1

        logger.info("Loaded %d Discord sessions from cache", count)
        return count

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return metadata for all known sessions (in-memory + on-disk)."""
        # Discover any on-disk sessions not yet loaded.
        if self._sessions_dir.exists():
            for path in self._sessions_dir.glob("*.jsonl"):
                channel_id = path.stem
                if channel_id not in self._sessions:
                    session = ChatSession(channel_id, self._sessions_dir)
                    session.load_from_cache()
                    self._sessions[channel_id] = session

        result: List[Dict[str, Any]] = []
        for cid, session in sorted(self._sessions.items()):
            result.append({
                "channel_id": cid,
                "channel_name": session.channel_name,
                "is_dm": session.is_dm,
                "message_count": session.get_message_count(),
                "buffer_size": len(session.buffer),
                "has_summary": bool(session.summary),
            })
        return result
