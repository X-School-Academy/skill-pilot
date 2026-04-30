from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes
import routes_shared


def test_cleanup_webui_tmux_session_saves_history_before_kill(monkeypatch, tmp_path):
    histories_dir = tmp_path / "terminal-histories"
    killed: list[str] = []
    captured_before_kill: list[bool] = []

    def fake_capture(session_name: str):
        captured_before_kill.append(not killed)
        return {
            "session": session_name,
            "pane_target": f"{session_name}:0.0",
            "command": "tmux capture-pane",
            "content": "line one\nline two\n",
        }

    monkeypatch.setattr(routes_shared, "_terminal_histories_dir", lambda: histories_dir)
    monkeypatch.setattr(routes_shared, "_capture_tmux_pane_history_any", fake_capture)
    monkeypatch.setattr(
        routes_shared,
        "_kill_tmux_session",
        lambda session_name: killed.append(session_name) or True,
    )

    removed = routes_shared._cleanup_webui_tmux_session("webui-live-session")

    assert removed is True
    assert captured_before_kill == [True]
    assert killed == ["webui-live-session"]
    saved_files = list(histories_dir.glob("*.md"))
    assert len(saved_files) == 1
    assert saved_files[0].read_text(encoding="utf-8") == "line one\nline two\n"


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


def test_saved_terminal_histories_are_listed_newest_first(monkeypatch, tmp_path):
    histories_dir = tmp_path / "terminal-histories"
    histories_dir.mkdir()
    older = histories_dir / "20260430T010000Z-aaaaaa-webui-live-old.md"
    newer = histories_dir / "20260430T020000Z-bbbbbb-webui-live-new.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    now = time.time()
    older_time = now - 60
    newer_time = now
    older.touch()
    newer.touch()
    import os
    os.utime(older, (older_time, older_time))
    os.utime(newer, (newer_time, newer_time))

    monkeypatch.setattr(routes_shared, "_terminal_histories_dir", lambda: histories_dir)

    histories = routes_shared._list_saved_terminal_histories()

    assert [item["id"] for item in histories] == [newer.name, older.name]
    assert histories[0]["session"] == "webui-live-new"


def test_saved_terminal_history_fetch_returns_content_payload(monkeypatch, tmp_path):
    histories_dir = tmp_path / "terminal-histories"
    histories_dir.mkdir()
    history_file = histories_dir / "20260430T030000Z-cccccc-webui-live-fetch.md"
    history_file.write_text("captured output\n", encoding="utf-8")

    monkeypatch.setattr(routes_shared, "_terminal_histories_dir", lambda: histories_dir)

    payload = routes_shared._read_saved_terminal_history(history_file.name)

    assert payload["id"] == history_file.name
    assert payload["session"] == "webui-live-fetch"
    assert payload["content"] == "captured output\n"


def test_saved_terminal_history_delete_removes_only_valid_history_files(monkeypatch, tmp_path):
    histories_dir = tmp_path / "terminal-histories"
    histories_dir.mkdir()
    history_file = histories_dir / "20260430T040000Z-dddddd-webui-live-delete.md"
    history_file.write_text("delete me", encoding="utf-8")
    sibling = tmp_path / "outside.md"
    sibling.write_text("keep me", encoding="utf-8")

    monkeypatch.setattr(routes_shared, "_terminal_histories_dir", lambda: histories_dir)

    assert routes_shared._delete_saved_terminal_history(history_file.name) is True
    assert not history_file.exists()
    assert sibling.exists()


def test_invalid_saved_terminal_history_ids_are_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(routes_shared, "_terminal_histories_dir", lambda: tmp_path / "terminal-histories")

    response = routes.terminal_tmux_saved_history("../outside.md")

    assert response.status_code == 400
