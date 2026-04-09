#!/usr/bin/env python3
import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

DEFAULT_CHAT_COMPLETIONS_URL = "http://192.168.1.222:12434/v1/chat/completions"
DEFAULT_MODEL = "local-model"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a non-streaming OpenAI-compatible chat completion against a local endpoint."
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=("text", "image"),
        help="Inference input type.",
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Prompt text to send to the model.",
    )
    parser.add_argument(
        "--file_path",
        help="Image file path. Required when --type image.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LOCAL_OPENAI_INFER_MODEL"),
        help=(
            "Optional model name. Defaults to LOCAL_OPENAI_INFER_MODEL. "
            f"If unset, sends {DEFAULT_MODEL}."
        ),
    )
    parser.add_argument(
        "--base_url",
        default=os.getenv("LOCAL_OPENAI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_CHAT_COMPLETIONS_URL,
        help=(
            "OpenAI-compatible base URL or full chat completions URL. "
            "Defaults to LOCAL_OPENAI_BASE_URL, OPENAI_BASE_URL, "
            f"or {DEFAULT_CHAT_COMPLETIONS_URL}."
        ),
    )
    parser.add_argument(
        "--api_key",
        default=os.getenv("LOCAL_OPENAI_INFER_API_KEY") or "local-openai",
        help="API key. Defaults to LOCAL_OPENAI_INFER_API_KEY or local-openai.",
    )
    args = parser.parse_args()

    if args.type == "image" and not args.file_path:
        parser.error("--file_path is required when --type image")
    if args.type == "text" and args.file_path:
        parser.error("--file_path is only valid when --type image")
    return args


def normalize_base_url(value: str) -> str:
    base_url = value.rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    return base_url


def image_file_to_data_url(file_path: str) -> str:
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_messages(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.type == "text":
        return [{"role": "user", "content": args.prompt}]

    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": args.prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_file_to_data_url(args.file_path)},
                },
            ],
        }
    ]


def extract_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise RuntimeError("No choices returned from chat completion")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(item["text"])
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    raise RuntimeError("No text content returned from chat completion")


def main() -> int:
    args = parse_args()
    client_kwargs: dict[str, Any] = {"api_key": args.api_key}
    if args.base_url:
        client_kwargs["base_url"] = normalize_base_url(args.base_url)

    client = OpenAI(**client_kwargs)
    request_kwargs: dict[str, Any] = {
        "model": args.model or DEFAULT_MODEL,
        "messages": build_messages(args),
        "stream": False,
    }

    response = client.chat.completions.create(**request_kwargs)
    print(extract_text(response))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
