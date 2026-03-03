#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

from .run_workflow import resolve_workflow_file, run_workflow


def default_socket_path() -> Path:
    return Path(__file__).resolve().parents[4] / ".skillpilot/temp" / "engine.sock"


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI bridge mcp tool request to core engine service")
    parser.add_argument(
        "--socket",
        default=str(default_socket_path()),
        help="Unix socket path (default: <repo>/.skillpilot/temp/engine.sock)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Socket timeout in seconds (default: 20)",
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
    run_workflow_parser = subparsers.add_parser(
        "run-workflow",
        help="Execute a workflow JSON by running each SubAgent via engine socket inference",
    )
    run_workflow_parser.add_argument(
        "workflow",
        help="Workflow JSON path (relative to core/workflows or absolute path under it)",
    )
    run_workflow_parser.add_argument("prompt", nargs="+", help="Global workflow instruction")
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    socket_path = Path(args.socket).expanduser().resolve()

    if args.command == "request":
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
            response = send_request(args.json_str, socket_path, args.timeout)
        except Exception as exc:
            print(f"request failed: {exc}", file=sys.stderr)
            return 2
        print(response)
        return 0

    if args.command in {"engine-restart", "engine-reload"}:
        operation = "engine_restart" if args.command == "engine-restart" else "engine_reload"
        payload = {"operation": operation}
        try:
            response_raw = send_request(json.dumps(payload, ensure_ascii=True), socket_path, args.timeout)
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
            response_raw = send_request(json.dumps(payload, ensure_ascii=True), socket_path, args.timeout)
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

    if args.command == "run-workflow":
        repo_root = Path(__file__).resolve().parents[4]
        workflows_root = repo_root / "core" / "workflows"

        try:
            workflow_file = resolve_workflow_file(args.workflow, workflows_root)
        except Exception as exc:
            print(f"run-workflow setup failed: {exc}", file=sys.stderr)
            return 2

        def infer_fn(prompt: str, provider_id: str | None) -> str:
            payload = {"operation": "skill_agent_infer", "prompt": prompt}
            if provider_id:
                payload["provider_id"] = provider_id
            response_raw = send_request(json.dumps(payload, ensure_ascii=True), socket_path, args.infer_timeout)
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
                workflow_prompt=" ".join(args.prompt).strip(),
                max_workers=effective_workers,
                infer_fn=infer_fn,
                log_fn=lambda message: print(message, file=sys.stderr),
            )
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
            response_raw = send_request(json.dumps(payload, ensure_ascii=True), socket_path, args.timeout)
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
