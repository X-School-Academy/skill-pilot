#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

from .run_workflow import resolve_workflow_file, run_workflow
from .sync import load_mcp_configs


class EngineNotStartedError(RuntimeError):
    pass


def normalize_runtime_mode(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"dev", "development"}:
        return "development"
    if normalized in {"prod", "production", "release"}:
        return "production"
    return None


def socket_root() -> Path:
    return Path(__file__).resolve().parents[4] / ".skillpilot/temp"


def runtime_mode_env() -> str | None:
    return normalize_runtime_mode(os.getenv("SKILL_PILOT_RUNTIME_MODE"))


def default_socket_candidates() -> list[Path]:
    root = socket_root()
    runtime_mode = runtime_mode_env()
    if runtime_mode is None:
        return [root / "engine.sock", root / "engine-dev.sock"]
    if runtime_mode in {"dev", "development"}:
        return [root / "engine-dev.sock"]
    return [root / "engine.sock"]


def default_socket_path() -> Path:
    return default_socket_candidates()[0]


def socket_candidates_for_mode(mode: str | None) -> list[Path]:
    root = socket_root()
    if mode == "development":
        return [root / "engine-dev.sock"]
    if mode == "production":
        return [root / "engine.sock"]
    return [root / "engine.sock", root / "engine-dev.sock"]


def default_request_timeout_seconds() -> float:
    return 7200.0


def resolve_request_timeout_seconds(json_str: str | None) -> float:
    if not json_str:
        return default_request_timeout_seconds()
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError:
        return default_request_timeout_seconds()
    if not isinstance(payload, dict):
        return default_request_timeout_seconds()
    server_id = payload.get("server_id")
    if not isinstance(server_id, str) or not server_id.strip():
        return default_request_timeout_seconds()

    config_path = Path(__file__).resolve().parents[4] / "config" / "mcp.json5"
    try:
        servers, _missing = load_mcp_configs(config_path)
    except Exception:
        return default_request_timeout_seconds()
    config = servers.get(server_id.strip())
    if config is None or not config.tool_timeout_ms:
        return default_request_timeout_seconds()
    return max(default_request_timeout_seconds(), (config.tool_timeout_ms / 1000.0) + 5.0)


def send_request(json_str: str, socket_path: Path, timeout: float) -> str:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(str(socket_path))
        client.sendall(json_str.encode("utf-8"))
        client.shutdown(socket.SHUT_WR)

        chunks: list[bytes] = []
        while True:
            data = client.recv(65536)
            if not data:
                break
            chunks.append(data)
    finally:
        client.close()

    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def send_request_with_runtime_fallback(
    json_str: str,
    timeout: float,
    socket_path: Path | None = None,
    *,
    explicit_socket: bool,
    socket_candidates: list[Path] | None = None,
) -> str:
    if explicit_socket:
        if socket_path is None:
            raise ValueError("socket_path is required when explicit_socket is True")
        return send_request(json_str, socket_path, timeout)

    errors: list[str] = []
    for candidate in socket_candidates or default_socket_candidates():
        try:
            return send_request(json_str, candidate, timeout)
        except Exception as exc:
            errors.append(f"{candidate.name}: {exc}")

    runtime_mode = runtime_mode_env()
    if runtime_mode is None:
        raise EngineNotStartedError("your Skill Pilot Engine (Prod or Dev) is not started")
    if runtime_mode in {"dev", "development"}:
        raise EngineNotStartedError("your Skill Pilot Engine (Dev) is not started")
    raise EngineNotStartedError("your Skill Pilot Engine (Prod) is not started")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI bridge mcp tool request to core engine service")
    parser.add_argument(
        "--socket",
        default=None,
        help="Unix socket path (default: mode-aware path under <repo>/.skillpilot/temp/)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Socket timeout in seconds (default: 7200, or request-specific MCP timeout + 5s for tool requests)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    request_parser = subparsers.add_parser("request", help="Send JSON payload to engine socket")
    request_parser.set_defaults(_request_parser=request_parser)
    request_parser.add_argument("json_str", nargs="?", help="JSON string payload")
    request_parser.add_argument(
        "--help-json",
        action="store_true",
        help="Print example request JSON payload and exit",
    )
    subparsers.add_parser("engine-restart", help="Request engine restart from memory via socket signal")
    subparsers.add_parser("engine-reload", help="Request engine reload (.env read) then restart via socket signal")
    get_webui_url_parser = subparsers.add_parser(
        "get_webui_url",
        help="Return the active WebUI HTTP URL with auth token from the running engine environment",
    )
    get_webui_url_parser.add_argument(
        "--dev",
        action="store_true",
        help="Force development mode and use the dev engine socket",
    )
    skill_agent_parser = subparsers.add_parser(
        "skill-agent",
        help="Run prompt inference through core engine default LLM provider and print plain text output",
    )
    skill_agent_parser.add_argument("prompt", nargs="+", help="Prompt text")
    skill_agent_parser.add_argument(
        "--provider",
        default=None,
        help="Optional provider id. Uses engine default provider when omitted.",
    )
    skill_agent_parser.add_argument("--auto", dest="auto", action="store_true", default=None)
    skill_agent_parser.add_argument("--no-auto", dest="auto", action="store_false")
    skill_agent_parser.add_argument("--network", dest="network", action="store_true", default=None)
    skill_agent_parser.add_argument("--no-network", dest="network", action="store_false")
    skill_agent_parser.add_argument("--sandbox", dest="sandbox", action="store_true", default=None)
    skill_agent_parser.add_argument("--no-sandbox", dest="sandbox", action="store_false")
    api_invoke_parser = subparsers.add_parser(
        "api-invoke",
        help="Invoke an internal POST /api/<name> route through the engine socket",
    )
    api_invoke_parser.add_argument("api_name", help="API name without /api/ prefix, for example create_course_plan")
    api_invoke_parser.add_argument(
        "payload",
        nargs="?",
        default="{}",
        help="JSON object payload (default: {})",
    )
    create_image_parser = subparsers.add_parser(
        "create-image",
        help="Create an image through the running engine socket and print the local file path",
    )
    create_image_parser.add_argument(
        "--ratio",
        choices=("square", "landscape", "portrait"),
        default="square",
        help="Output image ratio preset. Defaults to square.",
    )
    create_image_parser.add_argument(
        "--prompt",
        required=True,
        help="Detailed image generation prompt.",
    )
    create_audio_parser = subparsers.add_parser(
        "create-audio",
        help="Create TTS audio through the running engine socket and print the local file path",
    )
    create_audio_parser.add_argument(
        "--text",
        required=True,
        help="Plain text to synthesize.",
    )
    create_audio_parser.add_argument(
        "--format",
        default="mp3",
        help="Output audio format, for example mp3, wav, opus, aac, flac, or pcm. Defaults to mp3.",
    )
    create_audio_parser.add_argument(
        "--voice",
        default=None,
        help="Optional TTS voice id. Uses the configured provider default when omitted.",
    )
    run_workflow_parser = subparsers.add_parser(
        "run-workflow",
        help="Execute a workflow JSON by running each SubAgent via engine socket inference",
    )
    run_workflow_parser.add_argument(
        "workflow",
        nargs="?",
        help="Workflow JSON path (relative to core/workflows or absolute path under it)",
    )
    run_workflow_parser.add_argument("prompt", nargs="*", help="Global workflow instruction")
    run_workflow_parser.add_argument(
        "--workflow",
        dest="workflow_opt",
        default=None,
        help="Workflow JSON path (named form, preserved alongside positional form)",
    )
    run_workflow_parser.add_argument(
        "--prompt",
        dest="prompt_opt",
        default=None,
        help="Global workflow instruction text (named form)",
    )
    run_workflow_parser.add_argument(
        "--tmux-session",
        dest="tmux_session",
        default=None,
        help="Existing tmux session name to use for workflow monitor mode; use 'none' or omit for non-tmux mode",
    )
    run_workflow_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing tmux-session-backed workflow run; valid only with --tmux-session",
    )
    run_workflow_parser.add_argument(
        "--auto-continue",
        dest="auto_continue",
        action="store_true",
        help="Use automatic downstream continuation in tmux mode; valid only with --tmux-session",
    )
    run_workflow_parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Max parallel SubAgent runs (default: 1). Current socket bridge is single-request; values >1 are capped to 1.",
    )
    run_workflow_parser.add_argument(
        "--infer-timeout",
        type=float,
        default=300.0,
        help="Per-SubAgent socket timeout in seconds (default: 300)",
    )
    run_workflow_parser.add_argument("--auto", dest="auto", action="store_true", default=None)
    run_workflow_parser.add_argument("--no-auto", dest="auto", action="store_false")
    run_workflow_parser.add_argument("--network", dest="network", action="store_true", default=None)
    run_workflow_parser.add_argument("--no-network", dest="network", action="store_false")
    run_workflow_parser.add_argument("--sandbox", dest="sandbox", action="store_true", default=None)
    run_workflow_parser.add_argument("--no-sandbox", dest="sandbox", action="store_false")
    run_workflow_parser.add_argument(
        "--continue-terminal-session",
        action="store_true",
        help="Signal active terminal workflow execution to continue to the next node (start-by-prompt mode)",
    )
    run_workflow_parser.add_argument(
        "--continue-source",
        default="cli",
        help="Source label for continue signal logs (default: cli)",
    )
    new_agent_parser = subparsers.add_parser(
        "new_agent_session",
        help="Reuse latest web/native tmux bash session by stopping the current agent process and launching a new prompt",
    )
    new_agent_parser.add_argument("prompt", nargs="+", help="Prompt text")
    new_agent_parser.add_argument("--session-name", default=None, help="Optional explicit tmux session name")
    new_agent_parser.add_argument("--provider", default=None, help="Optional explicit provider id")
    new_agent_parser.add_argument("--auto", dest="auto", action="store_true", default=None)
    new_agent_parser.add_argument("--no-auto", dest="auto", action="store_false")
    new_agent_parser.add_argument("--network", dest="network", action="store_true", default=None)
    new_agent_parser.add_argument("--no-network", dest="network", action="store_false")
    new_agent_parser.add_argument("--sandbox", dest="sandbox", action="store_true", default=None)
    new_agent_parser.add_argument("--no-sandbox", dest="sandbox", action="store_false")

    return parser


def _resolve_run_workflow_inputs(args: argparse.Namespace) -> tuple[str, str, str | None]:
    workflow_positional = str(getattr(args, "workflow", "") or "").strip()
    workflow_named = str(getattr(args, "workflow_opt", "") or "").strip()
    if workflow_named and workflow_positional and workflow_named != workflow_positional:
        raise ValueError("workflow path provided by positional and --workflow must match")
    workflow = workflow_named or workflow_positional

    prompt_parts = getattr(args, "prompt", []) or []
    prompt_positional = " ".join(str(part) for part in prompt_parts).strip()
    prompt_named = str(getattr(args, "prompt_opt", "") or "").strip()
    if prompt_named and prompt_positional and prompt_named != prompt_positional:
        raise ValueError("prompt provided by positional and --prompt must match")
    prompt = prompt_named or prompt_positional

    raw_tmux_session = str(getattr(args, "tmux_session", "") or "").strip()
    normalized_tmux_session = raw_tmux_session or None
    if normalized_tmux_session and normalized_tmux_session.lower() == "none":
        normalized_tmux_session = None

    return workflow, prompt, normalized_tmux_session


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    explicit_socket = args.socket is not None
    socket_path = Path(args.socket).expanduser().resolve() if explicit_socket else default_socket_path()
    timeout = float(args.timeout) if args.timeout is not None else default_request_timeout_seconds()

    if args.command == "request":
        if args.timeout is None:
            timeout = resolve_request_timeout_seconds(args.json_str)
        if args.help_json:
            print('{"server_id":"<server-id>","tool_name":"<tool-name>","arguments":{}}')
            return 0
        if not args.json_str:
            request_parser = getattr(args, "_request_parser", None)
            if isinstance(request_parser, argparse.ArgumentParser):
                request_parser.print_help(sys.stderr)
            else:
                print("request requires json_str. Use --help for usage or --help-json for an example payload.", file=sys.stderr)
            return 2
        try:
            response = send_request_with_runtime_fallback(
                args.json_str,
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"request failed: {exc}", file=sys.stderr)
            return 2
        print(response)
        return 0

    if args.command in {"engine-restart", "engine-reload"}:
        operation = "engine_restart" if args.command == "engine-restart" else "engine_reload"
        payload = {"operation": operation}
        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"{args.command} request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or f"{args.command} failed"
            print(str(detail), file=sys.stderr)
            return 2
        result = response.get("result") or {}
        signal_name = result.get("signal", "")
        pid = result.get("pid", "")
        print(f"{args.command} requested: {signal_name} -> pid {pid}")
        return 0

    if args.command == "get_webui_url":
        payload = {"operation": "get_webui_url"}
        requested_mode = "development" if bool(getattr(args, "dev", False)) else None
        if requested_mode:
            payload["mode"] = requested_mode
        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
                socket_candidates=socket_candidates_for_mode(requested_mode),
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"get_webui_url request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "get_webui_url request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result") or {}
        if isinstance(result, dict):
            url = result.get("url")
            if url is not None:
                print(str(url))
                return 0
        print(response_raw)
        return 0

    if args.command == "skill-agent":
        payload = {
            "operation": "skill_agent_infer",
            "prompt": " ".join(args.prompt).strip(),
        }
        if args.provider:
            payload["provider_id"] = str(args.provider).strip()
        if args.auto is not None:
            payload["auto"] = bool(args.auto)
        if args.network is not None:
            payload["network"] = bool(args.network)
        if args.sandbox is not None:
            payload["sandbox"] = bool(args.sandbox)

        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"skill-agent request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "skill-agent request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result") or {}
        if isinstance(result, dict):
            text = result.get("text")
            if text is not None:
                print(str(text))
                return 0
        print(response_raw)
        return 0

    if args.command == "api-invoke":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            print(f"api-invoke payload must be valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(payload, dict):
            print("api-invoke payload must be a JSON object", file=sys.stderr)
            return 2

        request_payload = {
            "operation": "api_invoke",
            "api_name": str(args.api_name).strip(),
            "payload": payload,
        }
        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(request_payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"api-invoke request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "api-invoke request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "create-image":
        request_payload = {
            "operation": "create_image",
            "prompt": str(args.prompt).strip(),
            "ratio": str(args.ratio).strip(),
        }
        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(request_payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"create-image request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "create-image request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result") or {}
        if isinstance(result, dict):
            path = result.get("path")
            if path is not None:
                print(str(path))
                return 0
        print(response_raw)
        return 0

    if args.command == "create-audio":
        request_payload = {
            "operation": "create_audio",
            "text": str(args.text).strip(),
            "format": str(args.format).strip().lower(),
            "voice": str(args.voice).strip() if args.voice is not None else None,
        }
        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(request_payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"create-audio request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "create-audio request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result") or {}
        if isinstance(result, dict):
            path = result.get("path")
            if path is not None:
                print(str(path))
                return 0
        print(response_raw)
        return 0

    if args.command == "run-workflow":
        if bool(args.continue_terminal_session):
            payload = {
                "operation": "continue_workflow_terminal",
                "source": str(args.continue_source or "cli"),
            }
            try:
                response_raw = send_request_with_runtime_fallback(
                    json.dumps(payload, ensure_ascii=True),
                    timeout,
                    socket_path,
                    explicit_socket=explicit_socket,
                )
            except EngineNotStartedError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            except Exception as exc:
                print(f"run-workflow continue request failed: {exc}", file=sys.stderr)
                return 2
            try:
                response = json.loads(response_raw)
            except json.JSONDecodeError:
                print(response_raw)
                return 0

            if not isinstance(response, dict):
                print(response_raw)
                return 0
            if response.get("status") != "ok":
                detail = response.get("detail") or "run-workflow continue request failed"
                print(str(detail), file=sys.stderr)
                return 2
            result = response.get("result") or {}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if bool(result.get("accepted")) else 2

        try:
            workflow_arg, workflow_prompt, tmux_session = _resolve_run_workflow_inputs(args)
        except ValueError as exc:
            print(f"run-workflow setup failed: {exc}", file=sys.stderr)
            return 2

        if (bool(args.resume) or bool(args.auto_continue)) and not tmux_session:
            print(
                "run-workflow setup failed: --resume and --auto-continue require --tmux-session=<session-name>",
                file=sys.stderr,
            )
            return 2

        if not workflow_arg:
            print("run-workflow setup failed: workflow path is required", file=sys.stderr)
            return 2
        if not workflow_prompt:
            print("run-workflow setup failed: prompt is required", file=sys.stderr)
            return 2

        if tmux_session:
            payload = {
                "operation": "start_workflow_terminal",
                "workflow": workflow_arg,
                "prompt": workflow_prompt,
                "tmux_session": tmux_session,
                "resume": bool(args.resume),
                "next_node_trigger": "auto_continue" if bool(args.auto_continue) else "start_by_prompt",
            }
            if args.auto is not None:
                payload["auto"] = bool(args.auto)
            if args.network is not None:
                payload["network"] = bool(args.network)
            if args.sandbox is not None:
                payload["sandbox"] = bool(args.sandbox)
            try:
                response_raw = send_request_with_runtime_fallback(
                    json.dumps(payload, ensure_ascii=True),
                    timeout,
                    socket_path,
                    explicit_socket=explicit_socket,
                )
            except EngineNotStartedError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            except Exception as exc:
                print(f"run-workflow start request failed: {exc}", file=sys.stderr)
                return 2
            try:
                response = json.loads(response_raw)
            except json.JSONDecodeError:
                print(response_raw)
                return 0

            if not isinstance(response, dict):
                print(response_raw)
                return 0
            if response.get("status") != "ok":
                detail = response.get("detail") or "run-workflow start request failed"
                print(str(detail), file=sys.stderr)
                return 2

            result = response.get("result") or {}
            startup = result.get("startup") if isinstance(result, dict) else {}
            if isinstance(startup, dict):
                prompt_text = startup.get("prompt")
                if isinstance(prompt_text, str) and prompt_text.strip():
                    print(prompt_text.strip())
                    return 0
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        repo_root = Path(__file__).resolve().parents[4]
        workflows_root = repo_root / "core" / "workflows"

        try:
            workflow_file = resolve_workflow_file(workflow_arg, workflows_root)
        except Exception as exc:
            print(f"run-workflow setup failed: {exc}", file=sys.stderr)
            return 2

        def infer_fn(prompt: str, provider_id: str | None) -> str:
            payload = {"operation": "skill_agent_infer", "prompt": prompt}
            if provider_id:
                payload["provider_id"] = provider_id
            if args.auto is not None:
                payload["auto"] = bool(args.auto)
            if args.network is not None:
                payload["network"] = bool(args.network)
            if args.sandbox is not None:
                payload["sandbox"] = bool(args.sandbox)
            debug_parts = [
                "[run-workflow] infer_request",
                f"provider_id={provider_id or ''}",
                f"timeout={args.infer_timeout}",
                f"payload={json.dumps(payload, ensure_ascii=False)}",
            ]
            print(" ".join(debug_parts), file=sys.stderr)
            print(f"[run-workflow] infer_prompt\n{prompt}", file=sys.stderr)
            response_raw = send_request_with_runtime_fallback(
                json.dumps(payload, ensure_ascii=True),
                args.infer_timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
            print(f"[run-workflow] infer_response_raw\n{response_raw}", file=sys.stderr)
            response = json.loads(response_raw)
            if not isinstance(response, dict):
                raise RuntimeError("invalid skill-agent response")
            if response.get("status") != "ok":
                raise RuntimeError(str(response.get("detail") or "skill-agent request failed"))
            result = response.get("result") or {}
            if not isinstance(result, dict):
                raise RuntimeError("invalid skill-agent result payload")
            text = result.get("text")
            if text is None:
                raise RuntimeError("skill-agent response missing `text`")
            return str(text)

        requested_workers = max(1, int(args.max_workers))
        effective_workers = 1
        if requested_workers != 1:
            print(
                "run-workflow: --max-workers is capped to 1 because engine socket bridge handles one request at a time.",
                file=sys.stderr,
            )

        try:
            result = run_workflow(
                workflow_file=workflow_file,
                workflow_prompt=workflow_prompt,
                max_workers=effective_workers,
                infer_fn=infer_fn,
                log_fn=lambda message: print(message, file=sys.stderr),
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"run-workflow failed: {exc}", file=sys.stderr)
            return 2

        print(
            json.dumps(
                {
                    "status": result.status,
                    "workflow": result.workflow,
                    "workflow_name": result.workflow_name,
                    "duration_sec": result.duration_sec,
                    "run_id": result.run_id,
                    "output_root": result.output_root,
                    "node_status": result.node_status,
                    "final_outputs": result.final_outputs,
                    "errors": result.errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if result.status == "ok" else 2

    if args.command == "new_agent_session":
        payload = {
            "operation": "new_agent_session",
            "prompt": " ".join(args.prompt).strip(),
        }
        if args.session_name:
            payload["session_name"] = str(args.session_name).strip()
        if args.provider:
            payload["provider_id"] = str(args.provider).strip()
        if args.auto is not None:
            payload["auto"] = bool(args.auto)
        if args.network is not None:
            payload["network"] = bool(args.network)
        if args.sandbox is not None:
            payload["sandbox"] = bool(args.sandbox)

        try:
            response_raw = send_request_with_runtime_fallback(
                json.dumps(payload, ensure_ascii=True),
                timeout,
                socket_path,
                explicit_socket=explicit_socket,
            )
        except EngineNotStartedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"new_agent_session request failed: {exc}", file=sys.stderr)
            return 2
        try:
            response = json.loads(response_raw)
        except json.JSONDecodeError:
            print(response_raw)
            return 0

        if not isinstance(response, dict):
            print(response_raw)
            return 0
        if response.get("status") != "ok":
            detail = response.get("detail") or "new_agent_session request failed"
            print(str(detail), file=sys.stderr)
            return 2

        result = response.get("result") or {}
        if isinstance(result, dict):
            session_name = str(result.get("session_name") or "").strip()
            provider_id = str(result.get("provider_id") or "").strip()
            provider_bin = str(result.get("provider_bin") or "").strip()
            if session_name:
                provider_suffix_parts = [part for part in (provider_id, provider_bin) if part]
                provider_suffix = f" ({'/'.join(provider_suffix_parts)})" if provider_suffix_parts else ""
                print(f"new_agent_session started in {session_name}{provider_suffix}")
                return 0
        print(response_raw)
        return 0

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
