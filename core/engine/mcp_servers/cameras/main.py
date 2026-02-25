#!/usr/bin/env python3
"""
Cameras MCP Server

Provides WebRTC signaling tools for the cameras system.
Once the WebRTC data channel is open, all camera operations
(ONVIF discovery, add/delete, screenshots, play/stop video,
human detection) are handled via JSON messages on the data channel.

Run:
    uv run mcp_servers/cameras/main.py

Tools:
    webrtc_offer         — Accept SDP offer, create peer connection, return SDP answer
    webrtc_ice_candidate — Relay ICE candidate to the peer connection
"""

from __future__ import annotations

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from camera_manager import CameraManager
from webrtc_service import WebRTCService
from detection import DetectionService
from tools import register_tools


camera_manager = CameraManager()
detection_service = DetectionService(camera_manager)
webrtc_service = WebRTCService(camera_manager, detection_service)


@asynccontextmanager
async def _lifespan(app):
    # Event loop is running here — safe to create tasks.
    detection_service.sync_loops()
    yield


mcp = FastMCP("Cameras MCP Server", lifespan=_lifespan)
register_tools(mcp, webrtc_service)


def _cleanup_and_exit(*_args) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(webrtc_service.close())
        else:
            loop.run_until_complete(webrtc_service.close())
    except Exception:
        pass
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
