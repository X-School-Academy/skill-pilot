"""
WebRTCService — single RTCPeerConnection for the cameras server.

One connection serves the whole session:
  - One data channel carries all JSON camera commands
  - Video/audio tracks are added/removed dynamically for camera playback

Signaling (offer/answer + ICE) is done once via MCP tools.
After that, renegotiation for video tracks flows through the data channel.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from camera_manager import CameraManager
    from detection import DetectionService

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path(__file__).resolve().parents[4] / "config" / "settings.json5"


def _get_ice_servers() -> list[dict]:
    servers = [{"urls": "stun:stun.l.google.com:19302"}]
    try:
        import json5
        data = json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        turn_urls = (
            os.environ.get("TURN_SERVER_URLS")
            or data.get("turn", {}).get("urls", "")
        ).strip()
        turn_user = (
            os.environ.get("TURN_SERVER_USERNAME")
            or data.get("turn", {}).get("username", "")
        ).strip()
        turn_pass = (
            os.environ.get("TURN_SERVER_PASSWORD")
            or data.get("turn", {}).get("password", "")
        ).strip()
        if turn_urls:
            entry: dict = {"urls": [u.strip() for u in turn_urls.split(",") if u.strip()]}
            if turn_user:
                entry["username"] = turn_user
            if turn_pass:
                entry["credential"] = turn_pass
            servers.append(entry)
    except Exception as exc:
        logger.warning("Failed to read TURN config: %s", exc)
    return servers


class RTSPVideoTrack:
    """Async generator that yields VideoFrames from an RTSP stream."""

    def __init__(self, rtsp_url: str) -> None:
        self.rtsp_url = rtsp_url
        self._container = None
        self._stream = None

    async def open(self):
        import av
        self._container = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: av.open(self.rtsp_url, options={"rtsp_transport": "tcp"}, timeout=10),
        )
        video_streams = self._container.streams.video
        if not video_streams:
            raise ValueError(f"No video stream in {self.rtsp_url}")
        self._stream = video_streams[0]
        self._stream.codec_context.thread_type = "AUTO"

    def close(self):
        try:
            if self._container:
                self._container.close()
        except Exception:
            pass

    async def get_frame_bytes(self) -> bytes | None:
        try:
            def _read() -> bytes | None:
                for packet in self._container.demux(self._stream):
                    for frame in packet.decode():
                        img = frame.to_image()
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        return buf.getvalue()
                return None
            return await asyncio.get_event_loop().run_in_executor(None, _read)
        except Exception as exc:
            logger.warning("RTSP frame error %s: %s", self.rtsp_url, exc)
        return None


class CameraVideoTrack:
    """aiortc VideoStreamTrack that relays frames from RTSP."""

    def __init__(self, rtsp_url: str) -> None:
        from aiortc import VideoStreamTrack
        from av import VideoFrame

        class _Track(VideoStreamTrack):
            def __init__(self_inner):
                super().__init__()
                self_inner._rtsp = RTSPVideoTrack(rtsp_url)
                self_inner._started = False
                self_inner._pts = 0
                self_inner._first_frame_logged = False

            async def recv(self_inner):
                if not self_inner._started:
                    await self_inner._rtsp.open()
                    self_inner._started = True
                img_bytes = await self_inner._rtsp.get_frame_bytes()
                if img_bytes:
                    from PIL import Image
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    frame = VideoFrame.from_image(img)
                    if not self_inner._first_frame_logged:
                        self_inner._first_frame_logged = True
                        logger.info("[mcp.camera] first video frame received rtsp=%s", rtsp_url)
                else:
                    import numpy as np
                    frame = VideoFrame(width=640, height=480, format="rgb24")
                frame.pts = self_inner._pts
                frame.time_base = Fraction(1, 30)
                self_inner._pts += 1
                return frame

        self._track = _Track()

    @property
    def track(self):
        return self._track

    def stop(self):
        try:
            self._track._rtsp.close()
        except Exception:
            pass


class RTSPAudioTrack:
    """Async reader that yields AudioFrames from an RTSP stream."""

    def __init__(self, rtsp_url: str) -> None:
        self.rtsp_url = rtsp_url
        self._container = None
        self._stream = None

    async def open(self):
        import av
        self._container = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: av.open(self.rtsp_url, options={"rtsp_transport": "tcp"}, timeout=10),
        )
        audio_streams = self._container.streams.audio
        if not audio_streams:
            raise ValueError(f"No audio stream in {self.rtsp_url}")
        self._stream = audio_streams[0]

    def close(self):
        try:
            if self._container:
                self._container.close()
        except Exception:
            pass

    async def get_audio_frame(self):
        try:
            def _read():
                for packet in self._container.demux(self._stream):
                    for frame in packet.decode():
                        return frame
                return None
            return await asyncio.get_event_loop().run_in_executor(None, _read)
        except Exception as exc:
            logger.warning("RTSP audio error %s: %s", self.rtsp_url, exc)
        return None


class CameraAudioTrack:
    """aiortc AudioStreamTrack that relays frames from RTSP."""

    def __init__(self, rtsp_url: str) -> None:
        from aiortc import AudioStreamTrack
        from av import AudioFrame

        class _Track(AudioStreamTrack):
            def __init__(self_inner):
                super().__init__()
                self_inner._rtsp = RTSPAudioTrack(rtsp_url)
                self_inner._started = False
                self_inner._pts = 0
                self_inner._sample_rate = 48000
                self_inner._samples_per_frame = 960

            async def recv(self_inner):
                if not self_inner._started:
                    await self_inner._rtsp.open()
                    self_inner._started = True
                frame = await self_inner._rtsp.get_audio_frame()
                if frame is not None:
                    return frame

                # Fallback to silence frame on temporary decode failures.
                import numpy as np
                silent = AudioFrame.from_ndarray(
                    np.zeros((1, self_inner._samples_per_frame), dtype=np.int16),
                    format="s16",
                    layout="mono",
                )
                silent.sample_rate = self_inner._sample_rate
                silent.pts = self_inner._pts
                silent.time_base = Fraction(1, self_inner._sample_rate)
                self_inner._pts += self_inner._samples_per_frame
                await asyncio.sleep(self_inner._samples_per_frame / self_inner._sample_rate)
                return silent

        self._track = _Track()

    @property
    def track(self):
        return self._track

    def stop(self):
        try:
            self._track._rtsp.close()
        except Exception:
            pass


class WebRTCService:
    def __init__(self, camera_manager: CameraManager, detection_service: DetectionService) -> None:
        self._camera_manager = camera_manager
        self._detection_service = detection_service
        self._pc = None
        self._dc = None
        self._video_tracks: dict[str, CameraVideoTrack] = {}
        self._audio_tracks: dict[str, CameraAudioTrack] = {}
        self._camera_senders: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        logger.info("[mcp.camera] closing active peer and tracks")
        for t in self._video_tracks.values():
            t.stop()
        for t in self._audio_tracks.values():
            t.stop()
        self._video_tracks.clear()
        self._audio_tracks.clear()
        self._camera_senders.clear()
        if self._pc:
            await self._pc.close()
            self._pc = None
        self._detection_service.set_dc_send(None)

    # ── Signaling (called from MCP tools) ────────────────────────────────────

    async def handle_offer(
        self,
        sdp: str,
        sdp_type: str = "offer",
        remote_candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process SDP offer, set initial remote ICE candidates, return answer + local candidates."""
        from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
        started = time.monotonic()
        logger.info(
            "[mcp.camera] handle_offer start sdp_type=%s remote_candidates=%d",
            sdp_type,
            len(remote_candidates or []),
        )

        # Close any existing connection
        await self.close()

        ice_servers = _get_ice_servers()
        rtc_ice_servers = []
        for s in ice_servers:
            urls = s.get("urls")
            if isinstance(urls, str):
                urls = [urls]
            rtc_ice_servers.append(
                RTCIceServer(
                    urls=urls,
                    username=s.get("username"),
                    credential=s.get("credential"),
                )
            )

        config = RTCConfiguration(iceServers=rtc_ice_servers)
        pc = RTCPeerConnection(configuration=config)
        self._pc = pc

        @pc.on("datachannel")
        def on_datachannel(channel):
            if pc is not self._pc:
                # Ignore late datachannel events from stale peer connections.
                return
            self._dc = channel
            logger.info("[mcp.camera] data channel opened label=%s", channel.label)
            self._detection_service.set_dc_send(
                lambda msg: channel.send(json.dumps(msg))
            )

            @channel.on("message")
            def on_message(raw):
                asyncio.ensure_future(self._handle_dc_message(raw))

        @pc.on("connectionstatechange")
        async def on_connection_state():
            logger.info("[mcp.camera] connection state=%s", pc.connectionState)
            if pc is not self._pc:
                # Stale peer state updates must not tear down the active peer.
                return
            # "disconnected" can be transient (e.g. network handover/ICE re-check).
            # Closing immediately makes refresh/reconnect/play less stable.
            if pc.connectionState in ("failed", "closed"):
                await self.close()

        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await pc.setRemoteDescription(offer)
        if remote_candidates:
            for candidate in remote_candidates:
                if not isinstance(candidate, dict):
                    continue
                cand = candidate.get("candidate")
                if not isinstance(cand, str) or not cand.strip():
                    continue
                sdp_mid = candidate.get("sdpMid") if isinstance(candidate.get("sdpMid"), str) else ""
                sdp_mline_index_raw = candidate.get("sdpMLineIndex", 0)
                try:
                    sdp_mline_index = int(sdp_mline_index_raw)
                except Exception:
                    sdp_mline_index = 0
                await self.add_ice_candidate(
                    candidate=cand,
                    sdp_mid=sdp_mid,
                    sdp_mline_index=sdp_mline_index,
                )
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Fast reconnect path: return once we have at least one local candidate.
        await self._wait_ice_ready(pc, timeout=1.0)

        local_sdp = pc.localDescription.sdp
        candidates = self._extract_candidates_from_sdp(local_sdp)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[mcp.camera] handle_offer done elapsed_ms=%d answer_type=%s local_candidates=%d",
            elapsed_ms,
            pc.localDescription.type,
            len(candidates),
        )
        return {
            "sdp": local_sdp,
            "type": pc.localDescription.type,
            "candidates": candidates,
        }

    async def add_ice_candidate(self, candidate: str, sdp_mid: str, sdp_mline_index: int) -> None:
        if self._pc is None:
            raise RuntimeError("No active peer connection")
        # mDNS host candidates (".local") often incur DNS timeout on the server side.
        # Skip them and rely on routable host/srflx/relay candidates.
        if ".local" in candidate:
            logger.info("[mcp.camera] skip mdns candidate mid=%s mline=%s", sdp_mid, sdp_mline_index)
            return
        from aiortc.sdp import candidate_from_sdp
        ice = candidate_from_sdp(candidate)
        ice.sdpMid = sdp_mid
        ice.sdpMLineIndex = sdp_mline_index
        await self._pc.addIceCandidate(ice)
        logger.info("[mcp.camera] remote ice added mid=%s mline=%s", sdp_mid, sdp_mline_index)

    @staticmethod
    async def _wait_ice_complete(pc, timeout: float = 30.0) -> None:
        deadline = asyncio.get_event_loop().time() + timeout
        while pc.iceGatheringState != "complete":
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                logger.warning("ICE gathering timed out")
                break
            await asyncio.sleep(0.1)

    async def _wait_ice_ready(self, pc, timeout: float = 1.0) -> None:
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            sdp = pc.localDescription.sdp or ""
            if self._extract_candidates_from_sdp(sdp):
                return
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                # Fall back to whatever SDP we currently have.
                return
            await asyncio.sleep(0.05)

    @staticmethod
    def _extract_candidates_from_sdp(sdp: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        current_mid = ""
        current_mline_index = -1
        for raw in sdp.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("m="):
                current_mline_index += 1
                continue
            if line.startswith("a=mid:"):
                current_mid = line[6:]
                continue
            if line.startswith("a=candidate:"):
                candidates.append(
                    {
                        "candidate": line[2:],  # strip "a="
                        "sdpMid": current_mid,
                        "sdpMLineIndex": max(current_mline_index, 0),
                    }
                )
        return candidates

    # ── Data channel message dispatch ─────────────────────────────────────────

    async def _handle_dc_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except Exception:
            logger.warning("Invalid JSON on data channel: %s", raw[:200])
            return

        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        handlers = {
            "get_cameras": self._dc_get_cameras,
            "start_discovery": self._dc_start_discovery,
            "stop_discovery": self._dc_stop_discovery,
            "add_camera": self._dc_add_camera,
            "delete_camera": self._dc_delete_camera,
            "get_screenshot": self._dc_get_screenshot,
            "start_video": self._dc_start_video,
            "stop_video": self._dc_stop_video,
            "update_detection": self._dc_update_detection,
            "renegotiate_answer": self._dc_renegotiate_answer,
            "ping": self._dc_ping,
        }

        handler = handlers.get(msg_type)
        if handler:
            try:
                await handler(payload)
            except Exception as exc:
                logger.error("Data channel handler error %s: %s", msg_type, exc)
                self._dc_send({"type": "error", "payload": {"code": msg_type, "message": str(exc)}})
        else:
            logger.warning("Unknown data channel message type: %s", msg_type)

    def _dc_send(self, msg: dict) -> None:
        if self._dc and self._dc.readyState == "open":
            try:
                self._dc.send(json.dumps(msg))
            except Exception as exc:
                logger.warning("Data channel send error: %s", exc)

    # ── Data channel handlers ─────────────────────────────────────────────────

    async def _dc_get_cameras(self, _payload: dict) -> None:
        cameras = self._camera_manager.get_cameras()
        # Don't expose passwords
        safe = [{k: v for k, v in c.items() if k != "password"} for c in cameras]
        self._dc_send({"type": "cameras_list", "payload": {"cameras": safe}})

    async def _dc_start_discovery(self, _payload: dict) -> None:
        def on_update(discovered):
            safe = [{k: v for k, v in d.items() if k != "password"} for d in discovered]
            self._dc_send({
                "type": "discovery_update",
                "payload": {"status": "running", "discovered": safe},
            })
        self._camera_manager.start_discovery(on_update=on_update)
        self._dc_send({
            "type": "discovery_update",
            "payload": {"status": "started", "discovered": []},
        })

    async def _dc_stop_discovery(self, _payload: dict) -> None:
        self._camera_manager.stop_discovery()
        discovered = [{k: v for k, v in d.items() if k != "password"} for d in self._camera_manager.get_cameras() if d.get("added") is False]
        self._dc_send({
            "type": "discovery_update",
            "payload": {"status": "stopped", "discovered": discovered},
        })

    async def _dc_add_camera(self, payload: dict) -> None:
        # If onvif_camera_id provided, resolve RTSP first
        onvif_id = payload.get("onvif_camera_id", "")
        username = payload.get("username", "")
        password = payload.get("password", "")
        rtsp_url = payload.get("rtsp_url", "")
        snapshot_url = payload.get("snapshot_url", "")

        if onvif_id and not rtsp_url:
            resolved = await self._camera_manager.resolve_onvif_rtsp(onvif_id, username, password)
            if resolved:
                rtsp_url = resolved
                # Try to get snapshot URL from ONVIF device
                cam = self._camera_manager.get_camera_by_id(onvif_id)
                if cam:
                    snapshot_url = cam.get("snapshot_url", "")

        if not rtsp_url:
            self._dc_send({"type": "error", "payload": {"code": "add_camera", "message": "rtsp_url is required"}})
            return

        cam = self._camera_manager.add_camera(
            name=payload.get("name", "Camera"),
            rtsp_url=rtsp_url,
            snapshot_url=snapshot_url,
            source="onvif" if onvif_id else "manual",
            onvif_host=payload.get("onvif_host", ""),
            onvif_port=int(payload.get("onvif_port", 80)),
            username=username,
            password=password,
        )
        if onvif_id:
            self._camera_manager.remove_discovered(camera_id=onvif_id, onvif_host=cam.get("onvif_host", ""))
        # Sync detection loops after adding
        self._detection_service.sync_loops()
        safe = {k: v for k, v in cam.items() if k != "password"}
        self._dc_send({"type": "camera_added", "payload": {"camera": safe}})

    async def _dc_delete_camera(self, payload: dict) -> None:
        camera_id = payload.get("camera_id", "")
        # Stop video if playing
        if camera_id in self._video_tracks:
            await self._dc_stop_video({"camera_id": camera_id})
        ok = self._camera_manager.delete_camera(camera_id)
        # Sync detection loops
        self._detection_service.sync_loops()
        self._dc_send({"type": "camera_deleted", "payload": {"camera_id": camera_id, "ok": ok}})

    async def _dc_get_screenshot(self, payload: dict) -> None:
        camera_id = payload.get("camera_id", "")
        from datetime import datetime, timezone
        b64 = await self._camera_manager.get_snapshot_b64(camera_id)
        if b64:
            self._dc_send({
                "type": "screenshot",
                "payload": {
                    "camera_id": camera_id,
                    "image": b64,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            })
        else:
            self._dc_send({"type": "error", "payload": {"code": "screenshot", "message": "Failed to get snapshot"}})

    async def _dc_start_video(self, payload: dict) -> None:
        if self._pc is None:
            return
        started = time.monotonic()
        camera_id = payload.get("camera_id", "")
        logger.info("[mcp.camera] start_video recv camera_id=%s", camera_id)
        cam = self._camera_manager.get_camera_by_id(camera_id)
        if cam is None:
            self._dc_send({"type": "error", "payload": {"code": "start_video", "message": "Camera not found"}})
            return

        rtsp_url = cam.get("rtsp_url", "")
        if not rtsp_url:
            self._dc_send({"type": "error", "payload": {"code": "start_video", "message": "No RTSP URL"}})
            return

        await self._remove_camera_tracks(camera_id, renegotiate=False)
        video_track_wrapper = CameraVideoTrack(rtsp_url)
        self._video_tracks[camera_id] = video_track_wrapper
        sender_map: dict[str, Any] = {}
        sender_map["video"] = self._pc.addTrack(video_track_wrapper.track)

        if await self._has_audio_stream(rtsp_url):
            try:
                audio_track_wrapper = CameraAudioTrack(rtsp_url)
                self._audio_tracks[camera_id] = audio_track_wrapper
                sender_map["audio"] = self._pc.addTrack(audio_track_wrapper.track)
            except Exception as exc:
                logger.warning("Failed to add audio track for %s: %s", camera_id, exc)
        self._camera_senders[camera_id] = sender_map

        # Renegotiate: server creates new offer and sends via data channel
        await self._renegotiate(camera_id=camera_id, reason="start_video")
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info("[mcp.camera] start_video sent renegotiate camera_id=%s elapsed_ms=%d", camera_id, elapsed_ms)

    async def _dc_stop_video(self, payload: dict) -> None:
        camera_id = payload.get("camera_id", "")
        removed = await self._remove_camera_tracks(camera_id, renegotiate=True)
        if not removed:
            logger.info("stop_video requested for non-playing camera %s", camera_id)
        self._dc_send({"type": "video_stopped", "payload": {"camera_id": camera_id}})

    async def _dc_update_detection(self, payload: dict) -> None:
        camera_id = payload.get("camera_id", "")
        enabled = bool(payload.get("enabled", False))
        fps = float(payload.get("fps", 1))
        model = str(payload.get("model", "yolov8n"))
        ok = self._camera_manager.update_detection(camera_id, enabled, fps, model)
        self._detection_service.sync_loops()
        self._dc_send({"type": "detection_updated", "payload": {"camera_id": camera_id, "ok": ok}})

    async def _dc_renegotiate_answer(self, payload: dict) -> None:
        if self._pc is None:
            return
        from aiortc import RTCSessionDescription
        sdp = payload.get("sdp", "")
        sdp_type = payload.get("sdpType", "answer")
        answer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await self._pc.setRemoteDescription(answer)
        logger.info("[mcp.camera] renegotiation complete")

    async def _dc_ping(self, payload: dict) -> None:
        self._dc_send({"type": "pong", "payload": {"ts": payload.get("ts")}})

    async def _renegotiate(self, *, camera_id: str, reason: str) -> None:
        if self._pc is None:
            return
        try:
            offer = await self._pc.createOffer()
            await self._pc.setLocalDescription(offer)
            await self._wait_ice_ready(self._pc, timeout=0.8)
            self._dc_send({
                "type": "renegotiate",
                "payload": {
                    "camera_id": camera_id,
                    "reason": reason,
                    "sdp": self._pc.localDescription.sdp,
                    "sdpType": self._pc.localDescription.type,
                },
            })
            logger.info("[mcp.camera] renegotiate offer sent camera_id=%s reason=%s", camera_id, reason)
        except Exception as exc:
            logger.error("Renegotiation error for camera %s: %s", camera_id, exc)
            self._dc_send({"type": "error", "payload": {"code": reason, "message": str(exc)}})

    async def _remove_camera_tracks(self, camera_id: str, *, renegotiate: bool) -> bool:
        if self._pc is None:
            return False
        sender_map = self._camera_senders.pop(camera_id, {})
        removed = False
        for sender in sender_map.values():
            try:
                self._pc.removeTrack(sender)
                removed = True
            except Exception as exc:
                logger.warning("Failed removing sender for %s: %s", camera_id, exc)

        video = self._video_tracks.pop(camera_id, None)
        if video is not None:
            video.stop()
            removed = True
        audio = self._audio_tracks.pop(camera_id, None)
        if audio is not None:
            audio.stop()
            removed = True

        if removed and renegotiate:
            await self._renegotiate(camera_id=camera_id, reason="stop_video")
        return removed

    @staticmethod
    async def _has_audio_stream(rtsp_url: str) -> bool:
        def _probe() -> bool:
            try:
                import av
                container = av.open(rtsp_url, options={"rtsp_transport": "tcp"}, timeout=2)
                has_audio = bool(container.streams.audio)
                container.close()
                return has_audio
            except Exception:
                return False

        return await asyncio.get_event_loop().run_in_executor(None, _probe)
