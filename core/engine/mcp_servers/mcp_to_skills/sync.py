#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
import json
import json5
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
from safe_dotenv import load_env_with_safeguard, safe_env

logger = logging.getLogger(__name__)

class MCPError(RuntimeError):
    pass


@dataclass
class ServerConfig:
    id: str
    command: str | None
    args: list[str]
    env: dict[str, str]
    url: str | None
    type: str | None
    transport: str | None
    headers: dict[str, str]
    disabled: bool
    enabled: bool | None
    system: bool
    workdir: str | None
    tool_timeout_ms: int | None


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPClient:
    def list_tools(self) -> list[ToolDef]:
        raise NotImplementedError

    def close(self) -> None:
        return None


class StdioClient(MCPClient):
    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str],
        workdir: str | None = None,
        server_id: str = "unknown",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._next_id = 1
        self._lock = threading.Lock()
        self._stdout_queue: queue.Queue[str] = queue.Queue()
        self._stdout_closed = threading.Event()
        self._stderr_tail: deque[str] = deque(maxlen=20)
        self._server_id = server_id
        self._response_timeout_seconds = timeout_seconds
        merged_env = safe_env(extra=env)
        self._process = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=merged_env,
            cwd=workdir or None,
        )
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()
        self._stdout_thread = threading.Thread(target=self._drain_stdout, daemon=True)
        self._stdout_thread.start()
        self._initialize()

    def _drain_stderr(self) -> None:
        if self._process.stderr is None:
            return
        for line in self._process.stderr:
            stripped = line.strip()
            if stripped:
                self._stderr_tail.append(stripped)
                logger.info("[mcp.stdio.%s] %s", self._server_id, stripped)

    def _stderr_context(self) -> str:
        if not self._stderr_tail:
            return ""
        return f" | stderr tail: {' || '.join(self._stderr_tail)}"

    def _drain_stdout(self) -> None:
        if self._process.stdout is None:
            self._stdout_closed.set()
            return
        for line in self._process.stdout:
            self._stdout_queue.put(line)
        self._stdout_closed.set()

    def _initialize(self) -> None:
        try:
            self.request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "skill-pilot-sync", "version": "0.1"},
                },
            )
            # MCP notification method must include full notifications path.
            self._send_notification("notifications/initialized", {})
        except Exception:
            pass

    def _send_notification(self, method: str, params: dict[str, Any] | None) -> None:
        self._write_payload({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _write_payload(self, payload: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise MCPError("stdio process stdin unavailable")
        try:
            self._process.stdin.write(json.dumps(payload) + "\n")
            self._process.stdin.flush()
        except BrokenPipeError as exc:
            raise MCPError(f"stdio write failed: broken pipe{self._stderr_context()}") from exc

    def _read_response(self, request_id: int) -> Any:
        deadline = time.monotonic() + self._response_timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError("stdio response timed out")
            try:
                line = self._stdout_queue.get(timeout=remaining)
            except queue.Empty as exc:
                if self._stdout_closed.is_set():
                    raise MCPError(f"stdio process closed while awaiting response{self._stderr_context()}") from exc
                raise MCPError("stdio response timed out") from exc
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise MCPError(str(message["error"]))
            return message.get("result")

    def request(self, method: str, params: dict[str, Any] | None) -> Any:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            self._write_payload(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
            return self._read_response(request_id)

    def list_tools(self) -> list[ToolDef]:
        result = self.request("tools/list", {}) or {}
        return parse_tools(result)

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()


class HttpClient(MCPClient):
    def __init__(self, url: str, headers: dict[str, str], sse: bool, timeout_seconds: float = 30.0) -> None:
        self._url = url
        self._headers = headers
        self._sse = sse
        self._next_id = 1
        self._lock = threading.Lock()
        self._timeout_seconds = timeout_seconds
        self._initialize()

    def _initialize(self) -> None:
        try:
            self.request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "skill-pilot-sync", "version": "0.1"},
                },
            )
        except Exception:
            pass

    def request(self, method: str, params: dict[str, Any] | None) -> Any:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        response = (
            _post_sse(self._url, payload, self._headers, timeout_seconds=self._timeout_seconds)
            if self._sse
            else _post_json(self._url, payload, self._headers, timeout_seconds=self._timeout_seconds)
        )
        if response.get("id") != request_id:
            raise MCPError("mismatched response id")
        if "error" in response:
            raise MCPError(str(response["error"]))
        return response.get("result")

    def list_tools(self) -> list[ToolDef]:
        result = self.request("tools/list", {}) or {}
        return parse_tools(result)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/event-stream")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise MCPError(f"HTTP error {exc.code}: {error_body}") from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise MCPError("Invalid JSON response from MCP server") from exc


def _post_sse(url: str, payload: dict[str, Any], headers: dict[str, str], *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/event-stream")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            return _parse_sse_payload(raw)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise MCPError(f"HTTP error {exc.code}: {error_body}") from exc


def _parse_sse_payload(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line.replace("data:", "", 1).strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPError("No JSON response received from SSE stream") from exc


def parse_tools(result: dict[str, Any]) -> list[ToolDef]:
    tools = result.get("tools") or []
    parsed: list[ToolDef] = []
    for tool in tools:
        name = tool.get("name") if isinstance(tool, dict) else None
        if not isinstance(name, str) or not name:
            continue
        parsed.append(
            ToolDef(
                name=name,
                description=(tool.get("description") or "") if isinstance(tool, dict) else "",
                input_schema=(tool.get("inputSchema") or {}) if isinstance(tool, dict) else {},
            )
        )
    return parsed


def is_server_enabled(config: ServerConfig) -> bool:
    if config.enabled is not None:
        return config.enabled
    return not config.disabled


def expand_env_placeholders(value: Any, env: dict[str, str], missing: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: expand_env_placeholders(child, env, missing) for key, child in value.items()}
    if isinstance(value, list):
        return [expand_env_placeholders(item, env, missing) for item in value]
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([A-Za-z0-9_]+)\}")

        def replace(match: re.Match[str]) -> str:
            var = match.group(1)
            if var not in env:
                missing.add(var)
                return match.group(0)
            return env[var]

        return pattern.sub(replace, value)
    return value


def _coerce_to_bool(value: Any) -> bool:
    """Convert env-expanded field values (possibly strings) to bool.

    String values are parsed case-insensitively: "1", "true", "yes" → True;
    everything else (including "false", "0", "") → False.
    """
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def load_expansion_env(config_path: Path) -> dict[str, str]:
    return dict(os.environ)


def _coerce_timeout_ms(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        timeout_ms = int(str(value).strip())
    except (TypeError, ValueError):
        raise MCPError(f"invalid MCP tool timeout value: {value!r}")
    if timeout_ms <= 0:
        raise MCPError(f"MCP tool timeout must be > 0, got {timeout_ms}")
    return timeout_ms


def load_mcp_configs(path: Path) -> tuple[dict[str, ServerConfig], dict[str, set[str]]]:
    raw = json5.loads(path.read_text())
    raw_servers = raw.get("mcpServers")
    if not isinstance(raw_servers, dict):
        raise MCPError("mcpServers missing or invalid in config file")

    # Use repo root as subprocess cwd so relative paths in mcp.json5 stay stable.
    default_workdir = str(path.resolve().parent.parent)
    expansion_env = load_expansion_env(path)
    servers: dict[str, ServerConfig] = {}
    missing_env: dict[str, set[str]] = {}
    for server_id, value in raw_servers.items():
        if not isinstance(server_id, str) or not isinstance(value, dict):
            continue
        missing: set[str] = set()
        expanded = expand_env_placeholders(value, expansion_env, missing)

        command = expanded.get("command")
        args = expanded.get("args") or []
        if isinstance(command, list):
            cmd_list = [str(x) for x in command]
            command = cmd_list[0] if cmd_list else None
            args = cmd_list[1:] + [str(x) for x in args]
        else:
            command = str(command) if command is not None else None
            args = [str(x) for x in args]

        env_val = expanded.get("env") or {}
        headers_val = expanded.get("headers") or {}
        tool_timeout_ms = None
        if isinstance(env_val, dict):
            tool_timeout_ms = _coerce_timeout_ms(env_val.get("MCP_TOOL_TIMEOUT"))
        if tool_timeout_ms is None:
            tool_timeout_ms = _coerce_timeout_ms(expanded.get("toolTimeoutMs"))
        server = ServerConfig(
            id=server_id,
            command=command,
            args=args,
            env={str(k): str(v) for k, v in env_val.items()} if isinstance(env_val, dict) else {},
            url=str(expanded.get("url")) if expanded.get("url") is not None else None,
            type=str(expanded.get("type")) if expanded.get("type") is not None else None,
            transport=str(expanded.get("transport")) if expanded.get("transport") is not None else None,
            headers={str(k): str(v) for k, v in headers_val.items()} if isinstance(headers_val, dict) else {},
            disabled=_coerce_to_bool(expanded.get("disabled", False)),
            enabled=_coerce_to_bool(expanded["enabled"]) if "enabled" in expanded and expanded["enabled"] is not None else None,
            system=bool(expanded.get("system", False)),
            workdir=default_workdir,
            tool_timeout_ms=tool_timeout_ms,
        )
        servers[server_id] = server
        if missing:
            missing_env[server_id] = missing
    return servers, missing_env


def resolve_transport(config: ServerConfig) -> str:
    if config.transport:
        normalized = config.transport.replace("_", "-").lower()
        return normalized
    if config.type:
        normalized = config.type.replace("_", "-").lower()
        if normalized in {"http", "streamable-http"}:
            return "streamable-http"
        return normalized
    if config.command:
        return "stdio"
    if config.url:
        return "sse" if "sse" in config.url.lower() else "http"
    raise MCPError(f"Server {config.id} missing transport information")


def create_client(config: ServerConfig) -> MCPClient:
    transport = resolve_transport(config)
    timeout_seconds = (config.tool_timeout_ms / 1000.0) if config.tool_timeout_ms else 30.0
    if transport == "stdio":
        if not config.command:
            raise MCPError(f"Missing command for stdio server {config.id}")
        return StdioClient(
            config.command,
            config.args,
            config.env,
            config.workdir,
            server_id=config.id,
            timeout_seconds=timeout_seconds,
        )
    if transport in {"http", "streamable-http"}:
        if not config.url:
            raise MCPError(f"Missing url for server {config.id}")
        return HttpClient(config.url, config.headers, sse=(transport == "streamable-http"), timeout_seconds=timeout_seconds)
    if transport == "sse":
        if not config.url:
            raise MCPError(f"Missing url for server {config.id}")
        return HttpClient(config.url, config.headers, sse=True, timeout_seconds=timeout_seconds)
    raise MCPError(f"Unsupported transport '{transport}' for server {config.id}")


def camel_to_kebab(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", value)
    return value.lower()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        raise MCPError("skill name resolved to empty string")
    return value


def skill_name(server_id: str, tool_name: str) -> str:
    return slugify(f"{camel_to_kebab(server_id)}-{tool_name}")


def skill_dir(base_dir: Path, server_id: str, tool_name: str) -> Path:
    return base_dir / skill_name(server_id, tool_name)


def normalize_description(value: str) -> str:
    text = textwrap.dedent(value).strip()
    if not text:
        return text
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def split_docstring(description: str) -> tuple[str, str]:
    """Split a normalized docstring into (first_line, remaining_content).

    For system MCP tools the first line becomes the skill description and
    the remaining content is prepended to the skill body.
    """
    lines = description.splitlines()
    if not lines:
        return "", ""
    first_line = lines[0].strip()
    remaining = "\n".join(lines[1:]).strip()
    return first_line, remaining


def build_short_description(full_description: str, max_chars: int = 220) -> str:
    first_line = full_description.splitlines()[0].strip()
    candidate = re.sub(r"\s+", " ", first_line).strip()
    if not candidate:
        candidate = re.sub(r"\s+", " ", full_description).strip()
    if len(candidate) <= max_chars:
        return candidate
    return candidate[: max_chars - 1].rstrip() + "…"


def load_description_overrides(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise MCPError(f"Invalid YAML in description overrides file: {path}") from exc
    if not isinstance(raw, dict):
        raise MCPError(f"Description overrides file must be a mapping of skill-id to description: {path}")

    overrides: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if not isinstance(value, str):
            continue
        normalized = normalize_description(value)
        if normalized:
            overrides[key.strip().lower()] = normalized
    return overrides


def render_skill(tool: ToolDef, server_id: str, description_overrides: dict[str, str], is_system: bool = False) -> str:
    sid = skill_name(server_id, tool.name)
    fallback = f"Invoke MCP tool {tool.name} on server {server_id}."
    normalized = normalize_description(tool.description or fallback) or fallback

    if sid in description_overrides:
        full_description = description_overrides[sid]
        skill_description = build_short_description(full_description).replace('"', '\\"')
        tool_extra = ""
    elif is_system:
        first_line, remaining = split_docstring(normalized)
        skill_description = (first_line or normalized)[:1024].rstrip().replace('"', '\\"')
        full_description = normalized
        tool_extra = remaining
    else:
        full_description = normalized
        skill_description = build_short_description(full_description).replace('"', '\\"')
        tool_extra = ""

    schema_json = json.dumps(tool.input_schema or {}, indent=2, ensure_ascii=True)
    request_json = json.dumps({"server_id": server_id, "tool_name": tool.name, "arguments": {}}, ensure_ascii=True)

    extra_block = f"{tool_extra}\n\n" if tool_extra else ""
    tool_description_section = "" if is_system and not (sid in description_overrides) else f"\n## Tool Description\n{full_description}\n"

    return f"""---
name: {sid}
description: "{skill_description}"
---

{extra_block}## Usage
Call the local MCP bridge shell wrapper:
Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.

```bash
core/bin/tool-cli request '{request_json}'
```
{tool_description_section}
## Arguments Schema
```json
{schema_json}
```
"""


def write_skill_files(
    output_dir: Path, tools_by_server: dict[str, list[ToolDef]], description_overrides: dict[str, str], is_system: bool = False
) -> set[str]:
    expected: set[str] = set()
    for server_id in sorted(tools_by_server.keys()):
        for tool in sorted(tools_by_server[server_id], key=lambda t: t.name):
            path = skill_dir(output_dir, server_id, tool.name)
            expected.add(path.name)
            path.mkdir(parents=True, exist_ok=True)
            (path / "SKILL.md").write_text(render_skill(tool, server_id, description_overrides, is_system=is_system))
    return expected


def get_server_skill_dirs(output_dir: Path, server_id: str) -> list[Path]:
    if not output_dir.exists():
        return []
    pattern = f"{slugify(camel_to_kebab(server_id))}-*"
    return sorted(path for path in output_dir.glob(pattern) if path.is_dir())


def prune_server_skills(output_dir: Path, server_id: str, expected_skill_names: set[str]) -> None:
    for existing in get_server_skill_dirs(output_dir, server_id):
        if existing.name in expected_skill_names:
            continue
        shutil.rmtree(existing)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync MCP tools to local agent skills.")
    parser.add_argument(
        "servers",
        nargs="*",
        help="Optional MCP server ids from config/mcp.json5. If omitted, sync all enabled servers.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to MCP config JSON (default: <repo>/config/mcp.json5).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Directory for generated skill folders (default: <repo>/core/skills/mcp).",
    )
    parser.add_argument(
        "--system-output",
        default=None,
        help="Directory for generated system skill folders (default: <repo>/core/skills/system).",
    )
    parser.add_argument(
        "--descriptions",
        default=None,
        help="YAML file mapping skill-id to description override (default: <repo>/config/mcp_descriptions.yaml).",
    )
    return parser.parse_args()


def sync_mcp_tools(
    *,
    repo_root: Path,
    servers: list[str] | None = None,
    config_path: Path | None = None,
    output_dir: Path | None = None,
    system_output_dir: Path | None = None,
    descriptions_path: Path | None = None,
) -> dict[str, Any]:
    """
    In-process sync entrypoint.

    Assumes environment variables are already loaded into os.environ (engine main),
    so it does not attempt to read any .env files or invoke sudo.
    """
    default_config = repo_root / "config" / "mcp.json5"
    default_descriptions = repo_root / "config" / "mcp_descriptions.yaml"
    default_output = repo_root / "core" / "skills" / "mcp"
    default_system_output = repo_root / "core" / "skills" / "system"

    config_path = config_path or default_config
    descriptions_path = descriptions_path or default_descriptions
    output_dir = output_dir or default_output
    system_output_dir = system_output_dir or default_system_output

    output_dir.mkdir(parents=True, exist_ok=True)
    system_output_dir.mkdir(parents=True, exist_ok=True)

    description_overrides = load_description_overrides(descriptions_path)
    servers_by_id, missing_env = load_mcp_configs(config_path)
    requested = servers if servers else sorted(servers_by_id.keys())

    unknown = [server_id for server_id in requested if server_id not in servers_by_id]
    if unknown:
        raise MCPError(f"Unknown server id(s): {', '.join(sorted(unknown))}")

    total_tools = 0
    synced_servers: list[str] = []
    skipped_servers: list[str] = []
    all_output_dirs = [output_dir] if output_dir == system_output_dir else [output_dir, system_output_dir]
    for server_id in requested:
        config = servers_by_id[server_id]
        target_output_dir = system_output_dir if config.system else output_dir
        alternate_output_dirs = [path for path in all_output_dirs if path != target_output_dir]
        if not is_server_enabled(config):
            for path in all_output_dirs:
                prune_server_skills(path, server_id, set())
            skipped_servers.append(f"{server_id} (disabled)")
            continue

        missing = missing_env.get(server_id, set())
        if missing:
            skipped_servers.append(f"{server_id} (missing env: {', '.join(sorted(missing))})")
            continue

        client: MCPClient | None = None
        try:
            client = create_client(config)
            tools = client.list_tools()
            expected = write_skill_files(target_output_dir, {server_id: tools}, description_overrides, is_system=config.system)
            prune_server_skills(target_output_dir, server_id, expected)
            for path in alternate_output_dirs:
                prune_server_skills(path, server_id, set())
            total_tools += len(tools)
            synced_servers.append(f"{server_id} ({len(tools)} tools)")
        except Exception as exc:
            skipped_servers.append(f"{server_id} ({exc})")
        finally:
            if client is not None:
                client.close()

    return {
        "total_tools": total_tools,
        "synced_servers": synced_servers,
        "skipped_servers": skipped_servers,
        "requested": requested,
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "system_output_dir": str(system_output_dir),
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[4]
    # CLI entrypoint: load config/.env once so later config expansion only uses os.environ.
    load_env_with_safeguard(repo_root / "config" / ".env", override=False)
    default_config = repo_root / "config" / "mcp.json5"
    default_descriptions = repo_root / "config" / "mcp_descriptions.yaml"
    default_output = repo_root / "core" / "skills" / "mcp"
    default_system_output = repo_root / "core" / "skills" / "system"

    config_path = Path(args.config).expanduser().resolve() if args.config else default_config
    descriptions_path = Path(args.descriptions).expanduser().resolve() if args.descriptions else default_descriptions
    output_dir = Path(args.output).expanduser().resolve() if args.output else default_output
    system_output_dir = (
        Path(args.system_output).expanduser().resolve() if args.system_output else default_system_output
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    system_output_dir.mkdir(parents=True, exist_ok=True)

    description_overrides = load_description_overrides(descriptions_path)
    servers_by_id, missing_env = load_mcp_configs(config_path)
    requested = args.servers if args.servers else sorted(servers_by_id.keys())

    unknown = [server_id for server_id in requested if server_id not in servers_by_id]
    if unknown:
        print(f"Unknown server id(s): {', '.join(sorted(unknown))}")
        return 2

    total_tools = 0
    synced_servers: list[str] = []
    skipped_servers: list[str] = []
    all_output_dirs = [output_dir] if output_dir == system_output_dir else [output_dir, system_output_dir]
    for server_id in requested:
        config = servers_by_id[server_id]
        target_output_dir = system_output_dir if config.system else output_dir
        alternate_output_dirs = [path for path in all_output_dirs if path != target_output_dir]
        if not is_server_enabled(config):
            for path in all_output_dirs:
                prune_server_skills(path, server_id, set())
            skipped_servers.append(f"{server_id} (disabled)")
            continue

        missing = missing_env.get(server_id, set())
        if missing:
            skipped_servers.append(f"{server_id} (missing env: {', '.join(sorted(missing))})")
            continue

        client: MCPClient | None = None
        try:
            client = create_client(config)
            tools = client.list_tools()
            expected = write_skill_files(target_output_dir, {server_id: tools}, description_overrides, is_system=config.system)
            prune_server_skills(target_output_dir, server_id, expected)
            for path in alternate_output_dirs:
                prune_server_skills(path, server_id, set())
            total_tools += len(tools)
            synced_servers.append(f"{server_id} ({len(tools)} tools)")
        except Exception as exc:
            skipped_servers.append(f"{server_id} ({exc})")
        finally:
            if client is not None:
                client.close()

    if synced_servers:
        print(f"Synced {total_tools} tools from {len(synced_servers)} server(s).")
        for line in synced_servers:
            print(f"  - {line}")
    else:
        print("No servers were synced.")

    if skipped_servers:
        print("Skipped:")
        for line in skipped_servers:
            print(f"  - {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
