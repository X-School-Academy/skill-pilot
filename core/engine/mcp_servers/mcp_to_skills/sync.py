#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ENGINE_ROOT = str(Path(__file__).resolve().parents[2])
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

import json5_io as json5
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
    description: str | None
    instructions: str | None


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
        pattern = re.compile(r"\$\{([A-Za-z0-9_]+)(?:(:-|-)([^}]*))?\}")

        def replace(match: re.Match[str]) -> str:
            var = match.group(1)
            operator = match.group(2)
            default = match.group(3)
            if var in env:
                resolved = env[var]
                if operator == ":-" and resolved == "":
                    return default or ""
                return resolved
            if operator is not None:
                return default or ""
            missing.add(var)
            return match.group(0)

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
    # Use absolute() (not resolve()) so a symlinked config/ dir doesn't redirect
    # the workdir into the symlink target (e.g. workspace/).
    default_workdir = str(path.absolute().parent.parent)
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
        raw_desc = expanded.get("description")
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
            description=str(raw_desc).strip() if raw_desc else None,
            instructions=str(expanded["instructions"]).strip() if expanded.get("instructions") else None,
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


def normalize_description(value: str) -> str:
    text = textwrap.dedent(value).strip()
    if not text:
        return text
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def split_docstring(description: str) -> tuple[str, str]:
    lines = description.splitlines()
    if not lines:
        return "", ""
    first_line = lines[0].strip()
    remaining = "\n".join(lines[1:]).strip()
    return first_line, remaining


def get_server_skill_name(config: ServerConfig) -> str:
    return slugify(camel_to_kebab(config.id))


def render_tool_reference(tool: ToolDef, server_id: str) -> str:
    normalized = normalize_description(tool.description or f"Invoke MCP tool {tool.name} on server {server_id}.")
    request_json = json.dumps({"server_id": server_id, "tool_name": tool.name, "arguments": {}}, ensure_ascii=True)
    schema_json = json.dumps(tool.input_schema or {}, indent=2, ensure_ascii=True)
    return f"""# {tool.name}

{normalized}

## Usage
```bash
core/bin/tool-cli request '{request_json}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{schema_json}
```
"""


def render_server_skill(server_id: str, config: ServerConfig, tools: list[ToolDef]) -> str:
    sname = get_server_skill_name(config)
    fallback_desc = f"Invoke MCP tools on server {server_id}."
    description = (config.description or fallback_desc).strip()
    desc_escaped = description[:1024].replace('"', '\\"')

    tool_entries: list[str] = []
    for tool in sorted(tools, key=lambda t: t.name):
        normalized = normalize_description(tool.description or "")
        first_line, _ = split_docstring(normalized)
        short_desc = first_line or f"Invoke {tool.name} on server {server_id}."
        tool_entries.append(f"- **{tool.name}** — {short_desc} ([details](references/{tool.name}.md))")

    tools_section = "\n".join(tool_entries)
    instructions_block = ""
    if config.instructions:
        instructions_block = f"\n{normalize_description(config.instructions)}\n"
    return f"""---
name: {sname}
description: "{desc_escaped}"
---
{instructions_block}
## Tools

Select the tool that matches the task. Read its reference file only when you are ready to invoke it.

{tools_section}
"""


def write_server_skill(output_dir: Path, server_id: str, config: ServerConfig, tools: list[ToolDef]) -> str:
    """Write one skill directory for the server: SKILL.md + references/{tool}.md files.

    Returns the skill directory name.
    """
    sname = get_server_skill_name(config)
    skill_path = output_dir / sname
    refs_path = skill_path / "references"
    skill_path.mkdir(parents=True, exist_ok=True)
    refs_path.mkdir(exist_ok=True)
    (skill_path / "SKILL.md").write_text(render_server_skill(server_id, config, tools))
    for tool in tools:
        (refs_path / f"{tool.name}.md").write_text(render_tool_reference(tool, server_id))
    expected_refs = {f"{tool.name}.md" for tool in tools}
    for existing in list(refs_path.iterdir()):
        if existing.name not in expected_refs:
            existing.unlink()
    for existing in list(skill_path.iterdir()):
        if existing.name not in {"SKILL.md", "references"}:
            existing.unlink() if existing.is_file() else shutil.rmtree(existing)
    return sname


def prune_old_tool_skills(output_dir: Path, server_id: str) -> None:
    """Remove legacy per-tool skill directories matching {server_id}-* pattern."""
    if not output_dir.exists():
        return
    pattern = f"{slugify(camel_to_kebab(server_id))}-*"
    for existing in sorted(output_dir.glob(pattern)):
        if existing.is_dir():
            shutil.rmtree(existing)


def prune_server_skill(output_dir: Path, config: ServerConfig) -> None:
    """Remove the server-level skill directory (used when a server is disabled or moved)."""
    sname = get_server_skill_name(config)
    skill_path = output_dir / sname
    if skill_path.exists() and skill_path.is_dir():
        shutil.rmtree(skill_path)


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
    return parser.parse_args()


def sync_mcp_tools(
    *,
    repo_root: Path,
    servers: list[str] | None = None,
    config_path: Path | None = None,
    output_dir: Path | None = None,
    system_output_dir: Path | None = None,
) -> dict[str, Any]:
    """
    In-process sync entrypoint.

    Assumes environment variables are already loaded into os.environ (engine main),
    so it does not attempt to read any .env files or invoke sudo.
    """
    default_config = repo_root / "config" / "mcp.json5"
    default_output = repo_root / "core" / "skills" / "mcp"
    default_system_output = repo_root / "core" / "skills" / "system"

    config_path = config_path or default_config
    output_dir = output_dir or default_output
    system_output_dir = system_output_dir or default_system_output

    output_dir.mkdir(parents=True, exist_ok=True)
    system_output_dir.mkdir(parents=True, exist_ok=True)

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
                prune_old_tool_skills(path, server_id)
                prune_server_skill(path, config)
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
            write_server_skill(target_output_dir, server_id, config, tools)
            prune_old_tool_skills(target_output_dir, server_id)
            for path in alternate_output_dirs:
                prune_old_tool_skills(path, server_id)
                prune_server_skill(path, config)
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
    default_output = repo_root / "core" / "skills" / "mcp"
    default_system_output = repo_root / "core" / "skills" / "system"

    config_path = Path(args.config).expanduser().resolve() if args.config else default_config
    output_dir = Path(args.output).expanduser().resolve() if args.output else default_output
    system_output_dir = (
        Path(args.system_output).expanduser().resolve() if args.system_output else default_system_output
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    system_output_dir.mkdir(parents=True, exist_ok=True)

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
                prune_old_tool_skills(path, server_id)
                prune_server_skill(path, config)
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
            write_server_skill(target_output_dir, server_id, config, tools)
            prune_old_tool_skills(target_output_dir, server_id)
            for path in alternate_output_dirs:
                prune_old_tool_skills(path, server_id)
                prune_server_skill(path, config)
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
