from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes_shared


def test_cleanup_webui_tmux_session_kills_webui_live_session(monkeypatch):
    killed: list[str] = []
    monkeypatch.setattr(
        routes_shared,
        "_kill_tmux_session",
        lambda session_name: killed.append(session_name) or True,
    )

    removed = routes_shared._cleanup_webui_tmux_session("webui-live-session")

    assert removed is True
    assert killed == ["webui-live-session"]


def test_cleanup_webui_tmux_session_requires_webui_live_session(monkeypatch):
    monkeypatch.setattr(
        routes_shared,
        "_kill_tmux_session",
        lambda session_name: (_ for _ in ()).throw(AssertionError("unexpected kill")),
    )

    try:
        routes_shared._cleanup_webui_tmux_session("sp-engine-prod")
    except ValueError as exc:
        assert "webui-live-" in str(exc)
    else:
        raise AssertionError("expected non-webui tmux session to be rejected")
