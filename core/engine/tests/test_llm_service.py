import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import llm_service


def test_llm_get_text():

    result = llm_service.llm_get_text(
        [{"role": "user", "content": "Return exactly TEST_OK and nothing else."}],
    )

    assert "TEST_OK" in result


def test_llm_get_json():

    result = llm_service.llm_get_json(
        [
            {
                "role": "user",
                "content": 'Return exactly this JSON object and nothing else: {"ok": true, "value": 3}',
            }
        ]
    )

    assert result["ok"] is True
    assert result["value"] == 3


def test_llm_stream():

    chunks = list(
        llm_service.llm_stream(
            "Return exactly STREAM_OK and nothing else."
        )
    )

    assert chunks[-1] == b"[-DONE-]"
    streamed_text = b"".join(chunk for chunk in chunks if chunk not in {b"[-DONE-]", b"[-ERROR-]"}).decode(
        "utf-8",
        errors="replace",
    )
    assert "STREAM_OK" in streamed_text


def test_run_llm_once():

    result = llm_service.run_llm_once(
        "Return exactly RUN_ONCE_OK and nothing else.",
        client_id="test-client-run-once",
    )

    assert "RUN_ONCE_OK" in result
