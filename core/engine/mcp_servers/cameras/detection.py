"""
DetectionService — per-camera human detection using YOLO.

Each camera with detection.enabled=true gets an independent async loop.
Detected frames are:
  1. Always saved to .skillpilot/cameras/detections/{date}/{camera_id}_{ts}.jpg
  2. Sent as detection_event via WebRTC data channel (if connected)
  3. Sent as Discord DM via engine internal API (throttled, 15 min per camera)
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from camera_manager import CameraManager

logger = logging.getLogger(__name__)

_PROJECT_DIR = Path(__file__).resolve().parents[4]
_DETECTIONS_DIR = _PROJECT_DIR / ".skillpilot" / "cameras" / "detections"
_DISCORD_COOLDOWN_SECS = 900  # 15 minutes
_SETTINGS_PATH = _PROJECT_DIR / "config" / "settings.json5"


def _get_engine_port() -> int:
    try:
        import json5_io as json5

        data = json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        engine = data.get("services", {}).get("engine", {})
        mode = (os.getenv("SKILL_PILOT_RUNTIME_MODE", "production") or "production").strip().lower()
        if mode in {"dev", "development"}:
            mode = "development"
        else:
            mode = "production"
        mode_config = engine.get(mode, {}) if isinstance(engine, dict) else {}
        if not isinstance(engine, dict):
            engine = {}
        if not isinstance(mode_config, dict):
            mode_config = {}
        return int(mode_config.get("port", 3002 if mode == "development" else 3001))
    except Exception:
        return 3001


class DetectionService:
    def __init__(self, camera_manager: CameraManager) -> None:
        self._camera_manager = camera_manager
        self._tasks: dict[str, asyncio.Task] = {}
        self._task_specs: dict[str, tuple[float, str]] = {}
        self._last_discord_at: dict[str, float] = {}
        self._dc_send_fn: Any = None  # Set by WebRTCService once data channel is open

    def set_dc_send(self, fn) -> None:
        """Register a callable that sends a JSON message via the WebRTC data channel."""
        self._dc_send_fn = fn

    def sync_loops(self) -> None:
        """Start or stop detection loops to match current camera configs."""
        enabled_ids: set[str] = set()
        for cam in self._camera_manager.get_added_cameras():
            cid = cam["id"]
            detection = cam.get("detection", {})
            enabled = bool(detection.get("enabled", False))
            fps = float(detection.get("fps", 1))
            model_name = str(detection.get("model", "yolov8n"))
            spec = (fps, model_name)
            if enabled:
                enabled_ids.add(cid)
            should_restart = self._task_specs.get(cid) != spec
            if enabled and (cid not in self._tasks or self._tasks[cid].done() or should_restart):
                if cid in self._tasks and not self._tasks[cid].done():
                    self._tasks[cid].cancel()
                self._tasks[cid] = asyncio.create_task(self._loop(cam))
                self._task_specs[cid] = spec
            elif not enabled and cid in self._tasks and not self._tasks[cid].done():
                self._tasks[cid].cancel()
                self._task_specs.pop(cid, None)

        # Cancel loops for removed or no-longer-enabled cameras.
        stale_ids = [cid for cid in self._tasks if cid not in enabled_ids]
        for cid in stale_ids:
            task = self._tasks.get(cid)
            if task and not task.done():
                task.cancel()
            self._task_specs.pop(cid, None)

    async def _loop(self, cam: dict[str, Any]) -> None:
        cid = cam["id"]
        detection = cam.get("detection", {})
        fps = float(detection.get("fps", 1))
        model_name = detection.get("model", "yolov8n")
        interval = max(0.1, 1.0 / fps) if fps > 0 else 1.0

        model = await self._load_model(model_name)
        if model is None:
            logger.error("Could not load YOLO model %s for camera %s", model_name, cid)
            return

        logger.info("Detection loop started for camera %s (fps=%.2f model=%s)", cid, fps, model_name)
        while True:
            try:
                snapshot_b64 = await self._camera_manager.get_snapshot_b64(cid)
                if snapshot_b64:
                    img_bytes = base64.b64decode(snapshot_b64)
                    detections = await asyncio.get_event_loop().run_in_executor(
                        None, self._run_inference, model, img_bytes
                    )
                    if detections:
                        await self._on_detected(cam, img_bytes, detections)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Detection loop error camera %s: %s", cid, exc)
            await asyncio.sleep(interval)

        self._tasks.pop(cid, None)
        self._task_specs.pop(cid, None)
        logger.info("Detection loop stopped for camera %s", cid)

    async def _load_model(self, model_name: str):
        try:
            from ultralytics import YOLO
            model = await asyncio.get_event_loop().run_in_executor(None, YOLO, model_name)
            return model
        except Exception as exc:
            logger.error(
                "Failed to load YOLO model %s: %s. Run './skillpilot.sh enable human-detection' to install it.",
                model_name,
                exc,
            )
            return None

    def _run_inference(self, model, img_bytes: bytes) -> list[dict]:
        """Run YOLO inference; return list of person detections."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            results = model(img, verbose=False)
            detections = []
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    # class 0 = person in COCO
                    if cls_id == 0:
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        detections.append({"class": "person", "confidence": conf, "bbox": xyxy})
            return detections
        except Exception as exc:
            logger.warning("Inference error: %s", exc)
            return []

    async def _on_detected(
        self, cam: dict[str, Any], img_bytes: bytes, detections: list[dict]
    ) -> None:
        cid = cam["id"]
        ts = datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        date_str = ts.strftime("%Y-%m-%d")

        # 1. Always save image
        save_dir = _DETECTIONS_DIR / date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        img_path = save_dir / f"{cid}_{ts_str}.jpg"
        try:
            img_path.write_bytes(img_bytes)
        except Exception as exc:
            logger.warning("Failed to save detection image: %s", exc)

        # 2. Send detection_event via data channel
        if self._dc_send_fn:
            try:
                self._dc_send_fn({
                    "type": "detection_event",
                    "payload": {
                        "camera_id": cid,
                        "camera_name": cam.get("name", ""),
                        "detections": detections,
                        "timestamp": ts.isoformat(),
                    },
                })
            except Exception as exc:
                logger.warning("Failed to send detection_event via data channel: %s", exc)

        # 3. Discord DM (throttled per-camera, 15-min cooldown)
        last = self._last_discord_at.get(cid, 0.0)
        if time.monotonic() - last >= _DISCORD_COOLDOWN_SECS:
            self._last_discord_at[cid] = time.monotonic()
            asyncio.create_task(
                self._send_discord_notify(cam, img_path, ts)
            )

    async def _send_discord_notify(
        self, cam: dict[str, Any], img_path: Path, ts: datetime
    ) -> None:
        engine_port = _get_engine_port()
        url = f"http://127.0.0.1:{engine_port}/api/internal/discord/notify"
        msg = f"[Camera: {cam.get('name', cam['id'])}] Human detected at {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"message": msg, "image_path": str(img_path)},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status not in (200, 204):
                        logger.warning("Discord notify returned HTTP %d", resp.status)
        except Exception as exc:
            logger.warning("Discord notify request failed: %s", exc)
