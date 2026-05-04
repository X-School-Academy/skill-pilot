"""
CameraManager — CRUD, ONVIF discovery, snapshot retrieval.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import aiohttp
import json5
import sys

logger = logging.getLogger(__name__)

_PROJECT_DIR = Path(__file__).resolve().parents[4]
_ENGINE_DIR = Path(__file__).resolve().parents[2]
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))
_CONFIG_PATH = _PROJECT_DIR / "config" / "cameras.json5"

_DEFAULT_DETECTION = {"enabled": False, "fps": 1, "model": "yolov8n"}


def _default_camera(
    *,
    name: str,
    rtsp_url: str,
    snapshot_url: str = "",
    source: str = "manual",
    onvif_host: str = "",
    onvif_port: int = 80,
    username: str = "",
    password: str = "",
) -> dict[str, Any]:
    from datetime import datetime, timezone
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "source": source,
        "rtsp_url": rtsp_url,
        "snapshot_url": snapshot_url,
        "onvif_host": onvif_host,
        "onvif_port": onvif_port,
        "username": username,
        "password": password,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "detection": dict(_DEFAULT_DETECTION),
    }


class CameraManager:
    def __init__(self) -> None:
        self._cameras: list[dict[str, Any]] = []
        self._discovered: list[dict[str, Any]] = []
        self._discovery_task: asyncio.Task | None = None
        self._discovery_stop_at: float = 0.0
        self._load_config()

    # ── Config I/O ────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        try:
            if _CONFIG_PATH.exists():
                data = json5.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                self._cameras = data.get("cameras", [])
        except Exception as exc:
            logger.warning("Failed to load cameras config: %s", exc)
            self._cameras = []

    def _save_config(self) -> None:
        try:
            from json5_io import write_preserving_comments
            write_preserving_comments(_CONFIG_PATH, {"cameras": self._cameras})
        except Exception as exc:
            logger.error("Failed to save cameras config: %s", exc)

    # ── Public accessors ──────────────────────────────────────────────────────

    def get_cameras(self) -> list[dict[str, Any]]:
        """Return added cameras + in-memory discovered-but-not-added cameras."""
        added_ids = {c["id"] for c in self._cameras}
        pending = [d for d in self._discovered if d["id"] not in added_ids]
        return self._cameras + pending

    def get_added_cameras(self) -> list[dict[str, Any]]:
        """Return only persisted cameras from config."""
        return list(self._cameras)

    def get_camera_by_id(self, camera_id: str) -> dict[str, Any] | None:
        for c in self._cameras:
            if c["id"] == camera_id:
                return c
        for d in self._discovered:
            if d["id"] == camera_id:
                return d
        return None

    def add_camera(
        self,
        *,
        name: str,
        rtsp_url: str,
        snapshot_url: str = "",
        source: str = "manual",
        onvif_host: str = "",
        onvif_port: int = 80,
        username: str = "",
        password: str = "",
    ) -> dict[str, Any]:
        cam = _default_camera(
            name=name,
            rtsp_url=rtsp_url,
            snapshot_url=snapshot_url,
            source=source,
            onvif_host=onvif_host,
            onvif_port=onvif_port,
            username=username,
            password=password,
        )
        self._cameras.append(cam)
        # Remove matching discovered entry if present.
        self.remove_discovered(rtsp_url=rtsp_url, onvif_host=onvif_host)
        self._save_config()
        return cam

    def delete_camera(self, camera_id: str) -> bool:
        before = len(self._cameras)
        self._cameras = [c for c in self._cameras if c["id"] != camera_id]
        if len(self._cameras) < before:
            self._save_config()
            return True
        return False

    def update_detection(self, camera_id: str, enabled: bool, fps: float, model: str) -> bool:
        cam = self.get_camera_by_id(camera_id)
        if cam is None or cam not in self._cameras:
            return False
        cam["detection"] = {"enabled": enabled, "fps": fps, "model": model}
        self._save_config()
        return True

    # ── ONVIF Discovery ───────────────────────────────────────────────────────

    def start_discovery(self, on_update=None) -> None:
        """Start or extend ONVIF discovery window (max 3 min from latest call)."""
        now = time.monotonic()
        deadline = now + 180  # max 3 min from latest call
        self._discovery_stop_at = max(self._discovery_stop_at, deadline)

        if self._discovery_task is None or self._discovery_task.done():
            self._discovery_task = asyncio.create_task(
                self._run_discovery(on_update)
            )

    async def _run_discovery(self, on_update=None) -> None:
        try:
            from onvif import ONVIFDiscovery
        except ImportError:
            logger.error("onvif-python is not installed")
            return

        logger.info("ONVIF discovery started")
        discovery = ONVIFDiscovery(timeout=5)
        try:
            while time.monotonic() < self._discovery_stop_at:
                devices = await asyncio.get_event_loop().run_in_executor(None, discovery.discover)
                for dev in devices:
                    await self._probe_discovered_device(dev)
                if on_update:
                    on_update(self._discovered)
                await asyncio.sleep(2)
        finally:
            self._discovery_task = None
            logger.info("ONVIF discovery stopped")

    def stop_discovery(self) -> None:
        """Stop ONVIF discovery early."""
        self._discovery_stop_at = time.monotonic()
        if self._discovery_task and not self._discovery_task.done():
            self._discovery_task.cancel()
        self._discovery_task = None

    def remove_discovered(
        self,
        *,
        camera_id: str = "",
        rtsp_url: str = "",
        onvif_host: str = "",
    ) -> None:
        """Remove discovered entries that match the given identifiers."""
        self._discovered = [
            d for d in self._discovered
            if not (
                (camera_id and d.get("id") == camera_id)
                or (rtsp_url and d.get("rtsp_url") == rtsp_url)
                or (onvif_host and d.get("onvif_host") == onvif_host)
            )
        ]

    async def _probe_discovered_device(self, device: dict[str, Any]) -> None:
        """Normalize ONVIF discovery output to the local discovered-camera shape."""
        host = str(device.get("host") or "").strip()
        if not host:
            return
        try:
            port = int(device.get("port") or 80)
        except (TypeError, ValueError):
            port = 80

        # Avoid duplicates
        if any(d.get("onvif_host") == host for d in self._discovered):
            return

        xaddrs = device.get("xaddrs") if isinstance(device.get("xaddrs"), list) else []
        xaddr = xaddrs[0] if xaddrs else ""
        # Build a discovered entry (credentials unknown at discovery time)
        entry: dict = {
            "id": str(uuid.uuid4()),
            "name": f"Camera @ {host}",
            "source": "onvif",
            "rtsp_url": "",
            "snapshot_url": "",
            "onvif_host": host,
            "onvif_port": port,
            "username": "",
            "password": "",
            "added": False,
            "xaddr": xaddr,
        }
        self._discovered.append(entry)
        logger.info("Discovered ONVIF device at %s:%d", host, port)

    async def resolve_onvif_rtsp(
        self, camera_id: str, username: str, password: str
    ) -> str | None:
        """Use credentials to fetch the RTSP stream URI from an ONVIF device."""
        cam = self.get_camera_by_id(camera_id)
        if cam is None:
            return None
        host = cam.get("onvif_host", "")
        port = cam.get("onvif_port", 80)
        if not host:
            return None
        try:
            from onvif import ONVIFClient
            client = ONVIFClient(host, int(port), username, password)
            media = client.media()
            profiles = await asyncio.get_event_loop().run_in_executor(None, media.GetProfiles)
            if not profiles:
                return None
            first_profile = profiles[0]
            token = getattr(first_profile, "token", None)
            if token is None and isinstance(first_profile, dict):
                token = first_profile.get("token")
            if not token:
                return None
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: media.GetStreamUri(
                    ProfileToken=token,
                    StreamSetup={"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}},
                ),
            )
            uri = getattr(result, "Uri", None)
            if uri is None and isinstance(result, dict):
                uri = result.get("Uri")
            if not isinstance(uri, str) or not uri:
                return None
            # Inject credentials into URI if not present
            if username and "@" not in uri:
                uri = uri.replace("rtsp://", f"rtsp://{username}:{password}@")
            return uri
        except Exception as exc:
            logger.warning("Failed to get RTSP URI from ONVIF device %s: %s", host, exc)
            return None

    # ── Snapshot retrieval ────────────────────────────────────────────────────

    async def get_snapshot_b64(self, camera_id: str) -> str | None:
        """Return base64-encoded JPEG snapshot, or None on failure."""
        cam = self.get_camera_by_id(camera_id)
        if cam is None:
            return None

        snapshot_url = cam.get("snapshot_url", "")
        if snapshot_url:
            data = await self._fetch_snapshot_url(snapshot_url, cam)
            if data:
                return base64.b64encode(data).decode()

        rtsp_url = cam.get("rtsp_url", "")
        if rtsp_url:
            data = await self._grab_rtsp_frame(rtsp_url)
            if data:
                return base64.b64encode(data).decode()

        return None

    async def _fetch_snapshot_url(
        self, url: str, cam: dict[str, Any]
    ) -> bytes | None:
        username = cam.get("username", "")
        password = cam.get("password", "")
        try:
            auth = aiohttp.BasicAuth(username, password) if username else None
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as exc:
            logger.warning("Snapshot URL fetch failed for %s: %s", url, exc)
        return None

    async def _grab_rtsp_frame(self, rtsp_url: str) -> bytes | None:
        """Grab a single JPEG frame from an RTSP stream using av."""
        try:
            import av
            container = await asyncio.get_event_loop().run_in_executor(
                None, lambda: av.open(rtsp_url, options={"rtsp_transport": "tcp"})
            )
            frame = None
            for packet in container.demux(video=0):
                for f in packet.decode():
                    frame = f
                    break
                if frame:
                    break
            container.close()
            if frame is None:
                return None
            from PIL import Image
            img = frame.to_image()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception as exc:
            logger.warning("RTSP frame grab failed for %s: %s", rtsp_url, exc)
        return None
