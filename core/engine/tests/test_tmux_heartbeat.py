from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes_shared


def setup_function() -> None:
    routes_shared._tmux_session_heartbeat_times.clear()


def teardown_function() -> None:
    routes_shared._tmux_session_heartbeat_times.clear()


def test_cleanup_stale_webui_tmux_sessions_only_kills_stale(monkeypatch):
    killed: list[str] = []
    monkeypatch.setattr(routes_shared.time, "time", lambda: 100.0)
    monkeypatch.setattr(
        routes_shared,
        "_list_webui_tmux_sessions",
        lambda: [
            {"name": "webui-live-fresh", "created_at": 95},
            {"name": "webui-live-stale", "created_at": 40},
            {"name": "webui-live-created-stale", "created_at": 50},
        ],
    )
    monkeypatch.setattr(
        routes_shared,
        "_kill_tmux_session",
        lambda session_name: killed.append(session_name) or True,
    )

    routes_shared._record_tmux_session_heartbeat("webui-live-fresh")
    routes_shared._tmux_session_heartbeat_times["webui-live-stale"] = 60.0

    removed_count = routes_shared._cleanup_stale_webui_tmux_sessions()

    assert removed_count == 2
    assert killed == ["webui-live-stale", "webui-live-created-stale"]
    assert routes_shared._tmux_session_heartbeat_times == {"webui-live-fresh": 100.0}


def test_record_tmux_session_heartbeat_requires_webui_live_session():
    try:
        routes_shared._record_tmux_session_heartbeat("sp-engine-prod")
    except ValueError as exc:
        assert "webui-live-" in str(exc)
    else:
        raise AssertionError("expected non-webui tmux session to be rejected")
