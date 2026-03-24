#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import stat
import subprocess
import threading
import atexit
import errno
import shlex
import shutil
import time
from pathlib import Path
from typing import Any

import json5

from llm_service import build_terminal_command, get_provider, llm_get_text, load_llm_providers
from safe_dotenv import apply_env_key_values, loaded_env_key_names, safe_env
from session_agent_store import get_session_agent_meta, set_session_agent_meta

from .sync import MCPClient, create_client, is_server_enabled, load_mcp_configs


class MCPError(RuntimeError):
    pass


class Bridge:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._repo_root = Path(__file__).resolve().parents[4]
        self._settings_path = self._repo_root / "config" / "settings.json5"
        self._clients: dict[str, MCPClient] = {}
        self._enabled: set[str] = set()
        self._load()

    @staticmethod
    def _coerce_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        return bool(value)

    def _skill_agent_security(self, provider_id: str) -> dict[str, bool]:
        defaults = {"sandbox": True, "auto": True, "network": True}
        if not self._settings_path.is_file():
            return defaults
        try:
            data = json5.loads(self._settings_path.read_text(encoding="utf-8"))
        except Exception:
            return defaults
        if not isinstance(data, dict):
            return defaults
        security = data.get("security", {})
        if not isinstance(security, dict):
            return defaults
        skill_agent = security.get("skillAgent", {})
        if not isinstance(skill_agent, dict):
            return defaults
        # Backward compatibility: old flat object shape under security.skillAgent
        if any(key in skill_agent for key in ("sandbox", "auto", "network")):
            merged = dict(defaults)
            for key in ("sandbox", "auto", "network"):
                if key in skill_agent:
                    merged[key] = bool(skill_agent[key])
            return merged
        provider_sec = skill_agent.get(provider_id)
        if not isinstance(provider_sec, dict):
            return defaults
        merged = dict(defaults)
        for key in ("sandbox", "auto", "network"):
            if key in provider_sec:
                merged[key] = bool(provider_sec[key])
        return merged

    def _run_tmux(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        if shutil.which("tmux") is None:
            raise MCPError("tmux is not installed or not available in PATH")
        proc = subprocess.run(
            ["tmux", *args],
            capture_output=True,
            text=True,
            shell=False,
            env=safe_env(),
        )
        if check and proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip()
            raise MCPError(message or f"tmux command failed: {' '.join(args)}")
        return proc

    def _llm_providers(self) -> list[dict[str, Any]]:
        providers = load_llm_providers()
        return providers if isinstance(providers, list) else []

    def _provider_by_bin(self, provider_bin: str) -> dict[str, Any] | None:
        target = self._normalize_provider_bin(provider_bin)
        if not target:
            return None
        for provider in self._llm_providers():
            bin_name = str(provider.get("bin") or "").strip().lower()
            if bin_name == target:
                return provider
        return None

    def _provider_by_id(self, provider_id: str) -> dict[str, Any] | None:
        target = (provider_id or "").strip()
        if not target:
            return None
        for provider in self._llm_providers():
            if str(provider.get("id") or "").strip() == target:
                return provider
        return None

    @staticmethod
    def _normalize_provider_bin(provider_bin: str) -> str:
        value = (provider_bin or "").strip()
        if not value:
            return ""
        first_token = value.split()[0]
        normalized = os.path.basename(first_token).strip().lower()
        if normalized.endswith(".exe"):
            normalized = normalized[:-4]
        return normalized

    def _known_provider_bins(self) -> set[str]:
        bins: set[str] = set()
        for provider in self._llm_providers():
            bin_name = str(provider.get("bin") or "").strip().lower()
            if bin_name:
                bins.add(bin_name)
        return bins

    def _ps_children_pids(self, parent_pid: int) -> list[int]:
        if parent_pid <= 1:
            return []
        if shutil.which("pgrep") is not None:
            proc = subprocess.run(
                ["pgrep", "-P", str(parent_pid)],
                capture_output=True,
                text=True,
                check=False,
                env=safe_env(),
            )
            if proc.returncode == 0:
                result: list[int] = []
                for line in (proc.stdout or "").splitlines():
                    raw = line.strip()
                    if raw.isdigit():
                        result.append(int(raw))
                return result
        return []

    def _ps_command(self, pid: int) -> str:
        if pid <= 1:
            return ""
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "comm="],
            capture_output=True,
            text=True,
            check=False,
            env=safe_env(),
        )
        if proc.returncode != 0:
            return ""
        return (proc.stdout or "").strip()

    def _detect_agent_bin_for_session(self, session_name: str) -> str:
        pane_proc = self._run_tmux(["display-message", "-p", "-t", session_name, "#{pane_pid}"], check=False)
        if pane_proc.returncode != 0:
            return ""
        pane_pid_raw = (pane_proc.stdout or "").strip()
        if not pane_pid_raw.isdigit():
            return ""
        child_pids = self._ps_children_pids(int(pane_pid_raw))
        if not child_pids:
            return ""
        known_bins = self._known_provider_bins()
        if not known_bins:
            return ""
        for pid in reversed(child_pids):
            command = self._ps_command(pid)
            if not command:
                continue
            bin_name = os.path.basename(command).strip().lower()
            if bin_name in known_bins:
                return bin_name
        return ""

    def _detect_self_agent_bin(self) -> str:
        known_bins = self._known_provider_bins()
        if not known_bins:
            return ""
        # Try process ancestry first.
        current_pid = os.getpid()
        for _ in range(8):
            proc = subprocess.run(
                ["ps", "-p", str(current_pid), "-o", "ppid=,comm="],
                capture_output=True,
                text=True,
                check=False,
                env=safe_env(),
            )
            if proc.returncode != 0:
                break
            row = (proc.stdout or "").strip()
            if not row:
                break
            parts = row.split(None, 1)
            if not parts:
                break
            ppid = int(parts[0]) if parts[0].isdigit() else 0
            command = parts[1] if len(parts) > 1 else ""
            bin_name = os.path.basename(command).strip().lower()
            if bin_name in known_bins:
                return bin_name
            if ppid <= 1 or ppid == current_pid:
                break
            current_pid = ppid
        # Heuristic fallback: this codex agent defaults to codex bin.
        if "codex" in known_bins:
            return "codex"
        return ""

    def _provider_exit_session_shortcut(self, provider: dict[str, Any]) -> str:
        raw = provider.get("exit-session")
        if not isinstance(raw, str) or not raw.strip():
            raw = provider.get("exit_session")
        if isinstance(raw, str):
            return raw.strip()
        return "ctrl+c"

    def _get_session_agent_meta(self, session_name: str) -> dict[str, Any]:
        return get_session_agent_meta(session_name)

    def _send_exit_session_shortcut(self, session_name: str, provider: dict[str, Any]) -> str:
        raw = self._provider_exit_session_shortcut(provider)
        steps = [step.strip().lower() for step in raw.splitlines() if step.strip()]
        if not steps:
            steps = ["ctrl+c"]
        time.sleep(1.5)
        for step in steps:
            if step in {"ctrl+c", "^c", "c-c"}:
                self._run_tmux(["send-keys", "-t", session_name, "C-c"], check=False)
            elif step in {"enter", "return"}:
                self._run_tmux(["send-keys", "-t", session_name, "Enter"], check=False)
            elif step in {"esc", "escape"}:
                self._run_tmux(["send-keys", "-t", session_name, "Escape"], check=False)
                time.sleep(1.0)
                continue
            else:
                self._run_tmux(["send-keys", "-t", session_name, step, "Enter"], check=False)
            time.sleep(0.35)
        return raw

    def _pane_current_command(self, session_name: str) -> str:
        proc = self._run_tmux(["display-message", "-p", "-t", session_name, "#{pane_current_command}"], check=False)
        if proc.returncode != 0:
            return ""
        return self._normalize_provider_bin((proc.stdout or "").strip())

    def _provider_still_active(self, session_name: str, provider_bin: str) -> bool:
        expected = self._normalize_provider_bin(provider_bin)
        if not expected:
            return False
        pane_cmd = self._pane_current_command(session_name)
        if pane_cmd == expected:
            return True
        active_cmd = self._normalize_provider_bin(self._detect_agent_bin_for_session(session_name))
        return active_cmd == expected

    def _list_agent_tmux_sessions(self) -> list[dict[str, Any]]:
        prefixes = ("webui-live-", "native-terminal-")
        proc = self._run_tmux(
            ["ls", "-F", "#{session_name}\t#{session_created}"],
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip().lower()
            if "failed to connect to server" in message or "no server running" in message:
                return []
            raise MCPError((proc.stderr or proc.stdout or "").strip() or "unable to list tmux sessions")

        sessions: list[dict[str, Any]] = []
        for line in proc.stdout.splitlines():
            raw = line.strip()
            if not raw:
                continue
            parts = raw.split("\t")
            session_name = parts[0].strip() if parts else ""
            if not session_name.startswith(prefixes):
                continue
            created_raw = parts[1].strip() if len(parts) > 1 else "0"
            try:
                created_at = int(created_raw)
            except ValueError:
                created_at = 0
            sessions.append({"name": session_name, "created_at": created_at})
        sessions.sort(key=lambda item: (item["created_at"], item["name"]), reverse=True)
        return sessions

    def _latest_agent_tmux_session_name(self) -> str:
        sessions = self._list_agent_tmux_sessions()
        if not sessions:
            raise MCPError("No active web/native tmux session found")
        return str(sessions[0]["name"])

    @staticmethod
    def _validate_session_name_any(session_name: str) -> str:
        value = (session_name or "").strip()
        if not value:
            raise MCPError("session_name is required")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise MCPError("invalid session_name format")
        return value

    def _start_or_replace_agent_session(
        self,
        *,
        prompt: str,
        session_name: str | None = None,
        provider_id: str | None = None,
        sandbox_override: Any = None,
        auto_override: Any = None,
        network_override: Any = None,
    ) -> dict[str, Any]:
        target_session = self._validate_session_name_any(session_name) if session_name else self._latest_agent_tmux_session_name()
        session_meta = self._get_session_agent_meta(target_session)
        provider_source = "explicit"

        resolved_provider_id = (provider_id or "").strip()
        if resolved_provider_id:
            provider = self._provider_by_id(resolved_provider_id)
            if provider is None:
                raise MCPError(f"provider_id '{resolved_provider_id}' is not configured.")
        else:
            provider_id_from_meta = str(session_meta.get("provider_id") or "").strip()
            if not provider_id_from_meta:
                raise MCPError(
                    f"No recorded agent metadata for session '{target_session}'. "
                    "Provide provider_id or start a new session first."
                )
            provider = self._provider_by_id(provider_id_from_meta)
            if provider is None:
                raise MCPError(
                    f"Recorded provider_id '{provider_id_from_meta}' for session '{target_session}' is not configured."
                )
            resolved_provider_id = provider_id_from_meta
            provider_source = "session-meta"

        provider_id_text = str(provider.get("id") or "").strip()
        provider_bin = str(provider.get("bin") or "").strip()
        sandbox = self._coerce_bool(sandbox_override, bool(session_meta.get("sandbox", False)))
        auto = self._coerce_bool(auto_override, bool(session_meta.get("auto", False)))
        network = self._coerce_bool(network_override, bool(session_meta.get("network", True)))
        cmd_list = build_terminal_command(
            provider,
            prompt,
            auto_allow=auto,
            network_allow=network,
            sandbox_mode=sandbox,
        )
        if provider_id_text == "opencode" and auto:
            opencode_config = str(self._repo_root / "config" / "opencode-yolo.json")
            command = f"OPENCODE_CONFIG={shlex.quote(opencode_config)} {shlex.join(cmd_list)}"
        else:
            command = shlex.join(cmd_list)

        current_provider = None
        current_provider_id = str(session_meta.get("provider_id") or "").strip()
        if current_provider_id:
            current_provider = self._provider_by_id(current_provider_id)
        if current_provider is not None:
            current_provider_bin = str(current_provider.get("bin") or "").strip()
            exit_session_shortcut = self._send_exit_session_shortcut(target_session, current_provider)
            time.sleep(1.0)
            if self._provider_still_active(target_session, current_provider_bin):
                self._send_exit_session_shortcut(target_session, current_provider)
                time.sleep(1.0)
            if self._provider_still_active(target_session, current_provider_bin):
                raise MCPError(
                    f"Failed to exit current agent session '{current_provider_bin}' in tmux session '{target_session}'. "
                    "Try Ctrl+C manually in that terminal, then retry."
                )
        else:
            exit_session_shortcut = ""

        self._run_tmux(["send-keys", "-t", target_session, command, "Enter"], check=True)
        set_session_agent_meta(
            target_session,
            {
                "provider_id": provider_id_text,
                "provider_bin": provider_bin,
                "sandbox": sandbox,
                "auto": auto,
                "network": network,
                "updated_at": int(time.time()),
            },
        )
        return {
            "session_name": target_session,
            "provider_id": provider_id_text,
            "provider_bin": provider_bin,
            "provider_source": provider_source,
            "exit_session_shortcut": exit_session_shortcut,
            "command": command,
            "wait_seconds": 1.0,
        }

    def _load(self) -> None:
        servers, missing_env = load_mcp_configs(self._config_path)
        self._enabled.clear()

        for server_id, server_cfg in servers.items():
            if not is_server_enabled(server_cfg):
                continue
            if missing_env.get(server_id):
                continue
            self._enabled.add(server_id)

    def refresh_config(self, restart_clients: bool = False) -> dict[str, Any]:
        previous_enabled = set(self._enabled)
        self._load()

        active_enabled = set(self._enabled)
        stale_server_ids = [server_id for server_id in self._clients if server_id not in active_enabled]
        restarted_server_ids: list[str] = []
        if restart_clients:
            restarted_server_ids = [server_id for server_id in self._clients if server_id in active_enabled]
            stale_server_ids.extend(restarted_server_ids)

        closed_server_ids: set[str] = set()
        for server_id in stale_server_ids:
            if server_id in closed_server_ids:
                continue
            closed_server_ids.add(server_id)
            client = self._clients.pop(server_id, None)
            if client is not None:
                client.close()

        return {
            "enabled_servers": sorted(active_enabled),
            "disabled_servers": sorted(previous_enabled - active_enabled),
            "newly_enabled_servers": sorted(active_enabled - previous_enabled),
            "restarted_servers": sorted(restarted_server_ids),
        }

    def _get_client(self, server_id: str) -> MCPClient:
        if server_id not in self._enabled:
            raise MCPError(f"server_id is not enabled or not available: {server_id}")
        if server_id in self._clients:
            return self._clients[server_id]

        servers, missing_env = load_mcp_configs(self._config_path)
        cfg = servers.get(server_id)
        if cfg is None:
            raise MCPError(f"unknown server_id: {server_id}")
        if missing_env.get(server_id):
            missing = ", ".join(sorted(missing_env[server_id]))
            raise MCPError(f"missing env for server {server_id}: {missing}")

        client = create_client(cfg)
        self._clients[server_id] = client
        return client

    @staticmethod
    def _resolve_engine_control_pid() -> int:
        control_pid_raw = os.environ.get("SKILL_PILOT_ENGINE_CONTROL_PID", "").strip()
        if not control_pid_raw:
            raise MCPError(
                "engine control pid is not set; start engine via core/engine/main.py so restart/reload signals can be routed safely"
            )
        try:
            control_pid = int(control_pid_raw)
        except ValueError as exc:
            raise MCPError(f"invalid SKILL_PILOT_ENGINE_CONTROL_PID: {control_pid_raw!r}") from exc
        if control_pid <= 0:
            raise MCPError(f"invalid SKILL_PILOT_ENGINE_CONTROL_PID: {control_pid!r}")
        return control_pid

    def handle_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = payload.get("operation")
        if operation == "sync_mcp":
            repo_root = Path(__file__).resolve().parents[4]
            from .sync import sync_mcp_tools

            summary = sync_mcp_tools(repo_root=repo_root)
            # Close live MCP clients so the next tool request recreates them from the
            # freshly synced config on disk.
            refresh_summary = self.refresh_config(restart_clients=True)
            if isinstance(summary, dict):
                summary["bridge_refresh"] = refresh_summary
            return {"status": "ok", "result": summary}
        if operation in {"engine_restart", "engine_reload"}:
            control_pid = self._resolve_engine_control_pid()
            target_signal = signal.SIGUSR2 if operation == "engine_restart" else signal.SIGUSR1
            signal_name = "SIGUSR2" if operation == "engine_restart" else "SIGUSR1"
            if control_pid == os.getpid():
                handler = signal.getsignal(target_signal)
                if handler in (signal.SIG_DFL, signal.SIG_IGN):
                    raise MCPError(
                        f"refusing to send {signal_name} to current process {control_pid} without an installed signal handler"
                    )
            try:
                os.kill(control_pid, target_signal)
            except OSError as exc:
                raise MCPError(f"failed to send {signal_name} to pid {control_pid}: {exc}") from exc
            return {
                "status": "ok",
                "result": {
                    "operation": operation,
                    "signal": signal_name,
                    "pid": control_pid,
                },
            }
        if operation == "skill_agent_infer":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                raise MCPError("skill_agent_infer requires a non-empty prompt")
            provider_id_raw = payload.get("provider_id")
            requested_provider_id = str(provider_id_raw).strip() if isinstance(provider_id_raw, str) else None
            provider = get_provider(requested_provider_id)
            provider_id = str(provider.get("id") or "").strip()
            security_flags = self._skill_agent_security(provider_id)
            auto = bool(payload.get("auto")) if "auto" in payload else bool(security_flags["auto"])
            network = bool(payload.get("network")) if "network" in payload else bool(security_flags["network"])
            sandbox = bool(payload.get("sandbox")) if "sandbox" in payload else bool(security_flags["sandbox"])
            text = llm_get_text(
                messages=[{"role": "user", "content": prompt}],
                provider_id=provider_id,
                client_id="skill-agent",
                auto_allow=auto,
                network_allow=network,
                sandbox_mode=sandbox,
            )
            return {
                "status": "ok",
                "result": {
                    "text": text,
                    "provider_id": provider.get("id"),
                    "security": {"sandbox": sandbox, "auto": auto, "network": network},
                },
            }
        if operation == "new_agent_session":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                raise MCPError("new_agent_session requires a non-empty prompt")
            session_name_raw = payload.get("session_name")
            requested_provider_raw = payload.get("provider_id")
            result = self._start_or_replace_agent_session(
                prompt=prompt,
                session_name=str(session_name_raw).strip() if isinstance(session_name_raw, str) else None,
                provider_id=str(requested_provider_raw).strip() if isinstance(requested_provider_raw, str) else None,
                sandbox_override=payload.get("sandbox"),
                auto_override=payload.get("auto"),
                network_override=payload.get("network"),
            )
            return {
                "status": "ok",
                "result": result,
            }
        if operation == "continue_workflow_terminal":
            from routes import request_workflow_continue_signal  # lazy import to avoid module cycle at startup

            source_raw = payload.get("source")
            source = str(source_raw).strip() if isinstance(source_raw, str) else "cli"
            result = request_workflow_continue_signal(source=source or "cli")
            return {"status": "ok", "result": result}
        if operation == "safe_dotenv_key_names":
            return {"status": "ok", "result": {"keys": loaded_env_key_names()}}
        if operation == "safe_dotenv_set_key_values":
            updates_raw = payload.get("updates")
            if not isinstance(updates_raw, dict) or not updates_raw:
                raise MCPError("safe_dotenv_set_key_values requires a non-empty updates object")
            updates: dict[str, str] = {}
            for key, value in updates_raw.items():
                if not isinstance(key, str) or not key:
                    raise MCPError("safe_dotenv_set_key_values update keys must be non-empty strings")
                if not isinstance(value, str):
                    raise MCPError(f"safe_dotenv_set_key_values value for '{key}' must be a string")
                updates[key] = value
            applied = apply_env_key_values(updates)
            return {"status": "ok", "result": {"updated": applied}}

        server_id = payload.get("server_id")
        if not isinstance(server_id, str) or not server_id:
            raise MCPError(
                "request missing server_id, this is a skill to mcp tool bridge, please use the best agent skill with server_id instead of calling mcp tool directly"
            )

        client = self._get_client(server_id)

        if "tool_name" in payload:
            tool_name = payload.get("tool_name")
            if not isinstance(tool_name, str) or not tool_name:
                raise MCPError("request missing tool_name")
            arguments = payload.get("arguments")
            if arguments is not None and not isinstance(arguments, dict):
                raise MCPError("arguments must be an object")
            result = client.request("tools/call", {"name": tool_name, "arguments": arguments or {}})
            return {"status": "ok", "result": result}

        if "method" in payload:
            method = payload.get("method")
            if not isinstance(method, str) or not method:
                raise MCPError("request missing method")
            params = payload.get("params")
            if params is not None and not isinstance(params, dict):
                raise MCPError("params must be an object")
            result = client.request(method, params or {})
            return {"status": "ok", "result": result}

        raise MCPError("request must include tool_name or method")

    def handle_request_json(self, json_str: str) -> str:
        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "detail": "invalid_json"}, ensure_ascii=False)

        if not isinstance(payload, dict):
            return json.dumps({"status": "error", "detail": "payload must be object"}, ensure_ascii=False)

        try:
            response = self.handle_request(payload)
        except Exception as exc:
            return json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False)
        return json.dumps(response, ensure_ascii=False)

    def close(self) -> None:
        for client in self._clients.values():
            client.close()

    def probe_servers(self) -> list[dict[str, Any]]:
        servers, missing_env = load_mcp_configs(self._config_path)
        results: list[dict[str, Any]] = []

        for server_id in sorted(servers.keys()):
            cfg = servers[server_id]
            if not is_server_enabled(cfg):
                results.append({"server_id": server_id, "status": "skipped", "reason": "disabled"})
                continue
            missing = missing_env.get(server_id)
            if missing:
                results.append(
                    {
                        "server_id": server_id,
                        "status": "skipped",
                        "reason": f"missing env: {', '.join(sorted(missing))}",
                    }
                )
                continue

            client: MCPClient | None = None
            try:
                client = create_client(cfg)
                tools = client.list_tools()
                results.append({"server_id": server_id, "status": "ok", "tool_count": len(tools)})
            except Exception as exc:
                results.append({"server_id": server_id, "status": "error", "reason": str(exc)})
            finally:
                if client is not None:
                    client.close()

        return results


class MCPBridgeSocketService:
    _conn_read_timeout_seconds = 5.0

    def __init__(self, config_path: Path, socket_path: Path) -> None:
        self._bridge = Bridge(config_path)
        self._socket_path = socket_path
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._atexit_registered = False

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._prepare_socket_path()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self._socket_path))
        os.chmod(self._socket_path, stat.S_IRUSR | stat.S_IWUSR)
        server.listen(64)
        server.settimeout(1.0)

        self._server = server
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serve_forever, name="mcp-bridge-socket", daemon=True)
        self._thread.start()
        if not self._atexit_registered:
            atexit.register(self._cleanup_socket_file)
            self._atexit_registered = True

    def _prepare_socket_path(self) -> None:
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._socket_path.exists():
            return

        mode = self._socket_path.stat().st_mode
        if not stat.S_ISSOCK(mode):
            raise RuntimeError(f"Path exists and is not a socket: {self._socket_path}")

        owners = self._socket_owner_pids()
        if owners:
            self._terminate_socket_owners(owners)

        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.settimeout(0.2)
            probe.connect(str(self._socket_path))
        except OSError as exc:
            # Only remove sockets that are clearly stale.
            # Permission or transient connect errors should fail fast.
            if exc.errno in (errno.ECONNREFUSED, errno.ENOENT):
                self._socket_path.unlink(missing_ok=True)
            else:
                raise RuntimeError(f"Unable to probe existing socket {self._socket_path}: {exc}") from exc
        else:
            raise RuntimeError(f"Socket already in use: {self._socket_path}")
        finally:
            probe.close()

    def _socket_owner_pids(self) -> list[int]:
        if shutil.which("lsof") is None:
            return []
        proc = subprocess.run(
            ["lsof", "-t", "--", str(self._socket_path)],
            capture_output=True,
            text=True,
            shell=False,
            env=safe_env(),
        )
        if proc.returncode not in (0, 1):
            message = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(message or f"failed to inspect socket owners for {self._socket_path}")

        current_pid = os.getpid()
        owner_pids: list[int] = []
        seen: set[int] = set()
        for line in proc.stdout.splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                pid = int(raw)
            except ValueError:
                continue
            if pid <= 0 or pid == current_pid or pid in seen:
                continue
            seen.add(pid)
            owner_pids.append(pid)
        return owner_pids

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _terminate_socket_owners(self, pids: list[int]) -> None:
        pending = [pid for pid in pids if self._pid_alive(pid)]
        if not pending:
            return

        for sig, grace_seconds in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 0.5)):
            for pid in list(pending):
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    continue
                except PermissionError as exc:
                    raise RuntimeError(f"permission denied killing pid {pid} for socket {self._socket_path}") from exc
                except OSError as exc:
                    raise RuntimeError(f"failed to kill pid {pid} for socket {self._socket_path}: {exc}") from exc

            deadline = time.time() + grace_seconds
            while time.time() < deadline:
                alive = [pid for pid in pending if self._pid_alive(pid)]
                if not alive:
                    return
                pending = alive
                time.sleep(0.05)

            pending = [pid for pid in pending if self._pid_alive(pid)]
            if not pending:
                return

        raise RuntimeError(f"unable to terminate process(es) using socket {self._socket_path}: {pending}")

    def _serve_forever(self) -> None:
        assert self._server is not None
        while not self._stop_event.is_set():
            try:
                conn, _ = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                if self._stop_event.is_set():
                    break
                continue

            with conn:
                conn.settimeout(self._conn_read_timeout_seconds)
                try:
                    raw = self._read_all(conn)
                    response = self._bridge.handle_request_json(raw.strip())
                except Exception as exc:
                    response = json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False)
                try:
                    conn.sendall(response.encode("utf-8") + b"\n")
                except OSError:
                    continue

    @staticmethod
    def _read_all(conn: socket.socket) -> str:
        chunks: list[bytes] = []
        while True:
            try:
                data = conn.recv(65536)
            except socket.timeout as exc:
                raise MCPError("request read timed out") from exc
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode("utf-8", errors="replace")

    def stop(self) -> None:
        self._stop_event.set()
        if self._server is not None:
            try:
                self._server.close()
            finally:
                self._server = None

        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

        self._bridge.close()
        self._cleanup_socket_file()
        if self._atexit_registered:
            try:
                atexit.unregister(self._cleanup_socket_file)
            except Exception:
                pass
            self._atexit_registered = False

    def _cleanup_socket_file(self) -> None:
        self._socket_path.unlink(missing_ok=True)

    def probe_servers(self) -> list[dict[str, Any]]:
        return self._bridge.probe_servers()
