"""
MCP tool registration for the cameras server.

Only two tools are registered — both are for WebRTC signaling only.
All camera operations after connection establishment go through
the WebRTC data channel.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from webrtc_service import WebRTCService

logger = logging.getLogger(__name__)

_webrtc_service: WebRTCService | None = None


def register_tools(mcp: FastMCP, webrtc_service: WebRTCService) -> None:
    global _webrtc_service
    _webrtc_service = webrtc_service

    @mcp.tool()
    async def webrtc_offer(
        sdp: str,
        sdp_type: str = "offer",
        candidates: list[dict] | None = None,
    ) -> str:
        """
        Accept a WebRTC SDP offer from the WebUI, create the server-side
        RTCPeerConnection with a data channel, and return the SDP answer.

        After this call the WebUI should call webrtc_ice_candidate for each
        ICE candidate, then open the data channel and use JSON messages for
        all camera operations.

        Args:
            sdp: The SDP offer string from the browser RTCPeerConnection.
            sdp_type: SDP type, usually "offer".

        Returns:
            JSON string with keys "sdp" and "type" (the server SDP answer).
        """
        logger.info(
            "[mcp.camera] webrtc_offer recv sdp_type=%s remote_candidates=%d",
            sdp_type,
            len(candidates or []),
        )
        answer = await _webrtc_service.handle_offer(
            sdp=sdp,
            sdp_type=sdp_type,
            remote_candidates=candidates or [],
        )
        logger.info(
            "[mcp.camera] webrtc_offer answer type=%s candidates=%d",
            answer.get("type"),
            len(answer.get("candidates", [])) if isinstance(answer.get("candidates"), list) else 0,
        )
        return json.dumps(answer)

    @mcp.tool()
    async def webrtc_ice_candidate(
        candidate: str,
        sdp_mid: str = "",
        sdp_mline_index: int = 0,
    ) -> str:
        """
        Relay a WebRTC ICE candidate from the WebUI to the server peer connection.

        Args:
            candidate: The ICE candidate string (e.g. "candidate:...").
            sdp_mid: The m-line identifier (sdpMid) of the ICE candidate.
            sdp_mline_index: The m-line index (sdpMLineIndex) of the candidate.

        Returns:
            JSON string with key "status": "ok".
        """
        logger.info(
            "[mcp.camera] webrtc_ice_candidate recv mid=%s mline=%s",
            sdp_mid,
            sdp_mline_index,
        )
        await _webrtc_service.add_ice_candidate(
            candidate=candidate,
            sdp_mid=sdp_mid,
            sdp_mline_index=sdp_mline_index,
        )
        return json.dumps({"status": "ok"})
