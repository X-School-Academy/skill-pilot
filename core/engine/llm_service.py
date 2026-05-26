import json
import os
import re
import shlex
import subprocess
import threading
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import HTTPException
from json5_io import loads as json5_loads
from json_repair import repair_json

from safe_dotenv import loaded_env_key_names
from settings import LLM_PROVIDERS_FILE, PROJECT_DIR, logger

RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}
RUNNING_LOCK = threading.Lock()
WEBUI_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")
_WARNED_CONFIG_PLACEHOLDERS: set[tuple[str, str]] = set()


def _resolve_config_placeholders(raw: str, config_path: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in os.environ:
            return os.environ[key]
        return match.group(0)

    return _ENV_VAR_PATTERN.sub(replace, raw)


def _unresolved_config_placeholders(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                keys.update(match.group(1) for match in _ENV_VAR_PATTERN.finditer(key))
            keys.update(_unresolved_config_placeholders(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_unresolved_config_placeholders(item))
    elif isinstance(value, str):
        keys.update(match.group(1) for match in _ENV_VAR_PATTERN.finditer(value))
    return keys


def _warn_unresolved_config_placeholders(data: Dict[str, Any], config_path: Path) -> None:
    for key in sorted(_unresolved_config_placeholders(data)):
        warning_key = (str(config_path), key)
        if warning_key in _WARNED_CONFIG_PLACEHOLDERS:
            continue
        _WARNED_CONFIG_PLACEHOLDERS.add(warning_key)
        logger.warning(
            "AI provider config placeholder ${%s} was not resolved because the env var is not set: %s",
            key,
            config_path,
        )


def load_provider_config() -> Dict[str, Any]:
    config_path = LLM_PROVIDERS_FILE
    if not config_path.exists():
        raise SystemExit(f"FATAL: required AI provider config is missing: {config_path}")

    try:
        raw = config_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise SystemExit(f"FATAL: failed to read AI provider config {config_path}: {exc}") from exc

    raw = _resolve_config_placeholders(raw, config_path)

    try:
        try:
            data = json.loads(raw)
        except JSONDecodeError:
            data = json5_loads(raw)
    except Exception as exc:
        raise SystemExit(f"FATAL: failed to parse AI provider config {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"FATAL: AI provider config root must be an object: {config_path}")

    _warn_unresolved_config_placeholders(data, config_path)
    return data


_ = load_provider_config()


def _is_background_only(provider: Dict[str, Any]) -> bool:
    return bool(provider.get("background_only", False) or provider.get("background-only", False))


def _load_llm_provider_entries(*, include_background_only: bool = False) -> List[Dict[str, Any]]:
    data = load_provider_config().get("llm", [])
    providers = data if isinstance(data, list) else []
    visible: List[Dict[str, Any]] = []
    for provider in providers:
        if provider.get("disabled", False):
            continue
        if _is_background_only(provider) and not include_background_only:
            continue
        visible.append(provider)
    return visible


def load_llm_providers() -> List[Dict[str, Any]]:
    return _load_llm_provider_entries()


def load_tts_providers() -> List[Dict[str, Any]]:
    data = load_provider_config().get("tts", [])
    providers = data if isinstance(data, list) else []
    return [p for p in providers if not p.get("disabled", False)]


def load_image_providers() -> List[Dict[str, Any]]:
    data = load_provider_config().get("image", [])
    providers = data if isinstance(data, list) else []
    return [p for p in providers if not p.get("disabled", False)]


def _default_id(kind: str, providers: List[Dict[str, Any]]) -> Optional[str]:
    cfg = load_provider_config().get("default", {})
    preferred = cfg.get(kind)
    if preferred:
        for provider in providers:
            if provider.get("id") == preferred:
                return preferred
    if providers:
        return providers[0].get("id")
    return None


def get_default_llm_provider_id() -> Optional[str]:
    return _default_id("llm", load_llm_providers())


def get_default_doctor_provider_id() -> Optional[str]:
    return _default_id("doctor", load_llm_providers())


def get_default_background_llm_provider_id() -> Optional[str]:
    cfg = load_provider_config().get("default", {})
    preferred = cfg.get("background_llm")
    if preferred != "skill-pilot":
        return get_default_llm_provider_id()
    providers = _load_llm_provider_entries(include_background_only=True)
    for provider in providers:
        if provider.get("id") == preferred:
            return preferred
    return get_default_llm_provider_id()


def get_provider(provider_id: Optional[str]) -> Dict[str, Any]:
    providers = load_llm_providers()
    if not providers:
        raise HTTPException(status_code=500, detail="No LLM providers configured")
    selected = provider_id or _default_id("llm", providers)
    for provider in providers:
        if provider.get("id") == selected:
            return provider
    return providers[0]


def get_background_provider(provider_id: Optional[str]) -> Dict[str, Any]:
    if provider_id:
        return get_provider(provider_id)
    providers = _load_llm_provider_entries(include_background_only=True)
    if not providers:
        raise HTTPException(status_code=500, detail="No LLM providers configured")
    selected = get_default_background_llm_provider_id()
    for provider in providers:
        if provider.get("id") == selected:
            return provider
    return get_provider(None)


def get_tts_provider(provider_id: Optional[str]) -> Dict[str, Any]:
    providers = load_tts_providers()
    if not providers:
        raise HTTPException(status_code=500, detail="No TTS providers configured")
    selected = provider_id or load_provider_config().get("default", {}).get("tts")
    for provider in providers:
        if provider.get("id") == selected:
            return provider
    return providers[0]


def get_image_provider(provider_id: Optional[str]) -> Dict[str, Any]:
    providers = load_image_providers()
    if not providers:
        raise HTTPException(status_code=500, detail="No image providers configured")
    selected = provider_id or load_provider_config().get("default", {}).get("image")
    for provider in providers:
        if provider.get("id") == selected:
            return provider
    return providers[0]


def _popen_kwargs() -> Dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": 0x08000000}
    return {}


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


def _string_list(provider: Dict[str, Any], key: str) -> List[str]:
    value = provider.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


_CONFIG_DIR = str(PROJECT_DIR / "config")


def _resolve_arg(arg: str) -> str:
    """Resolve placeholders and bare filenames in provider args.

    - ``{{config_dir}}`` is replaced with the absolute path to the config/ dir.
    - ``${ENV_VAR}`` placeholders are expanded from the current environment.
    - Bare filenames (no path separator, .json/.json5 extension) are resolved
      relative to config/ by default (e.g. ``claude-sandbox-settings.json``).
    """
    arg = _ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), arg)
    if "{{config_dir}}" in arg:
        return arg.replace("{{config_dir}}", _CONFIG_DIR)
    if (
        os.sep not in arg
        and "/" not in arg
        and (arg.endswith(".json") or arg.endswith(".json5"))
    ):
        return os.path.join(_CONFIG_DIR, arg)
    return arg


def _build_codex_terminal_args(provider: Dict[str, Any], prompt: str, model: str | None = None, effort: str | None = None) -> List[str]:
    """Reuse Codex provider config for terminal mode without non-interactive flags."""
    derived_args: List[str] = []
    for raw_arg in _string_list(provider, "args"):
        arg = _resolve_arg(raw_arg)
        if arg in {"exec", "--json"}:
            continue
        if "{{prompt}}" in arg:
            continue
        derived_args.append(arg)
    if model:
        derived_args.extend(["--model", model])
    if effort:
        derived_args.extend(["--effort", effort])
    derived_args.append(prompt)
    return derived_args


def build_llm_command(
    provider: Dict[str, Any],
    prompt: str,
    auto_allow: Optional[bool] = None,
    network_allow: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> List[str]:
    args: List[str] = []
    provider_args = _string_list(provider, "args")
    auto_args = _string_list(provider, "auto-args")
    network_args = _string_list(provider, "network-args")
    sandbox_args = _string_list(provider, "sandbox-args")
    use_auto_allow = _coerce_bool(auto_allow, False)
    use_network_allow = _coerce_bool(network_allow, False)
    use_sandbox_mode = _coerce_bool(sandbox_mode, True)

    if use_sandbox_mode:
        args.extend(_resolve_arg(arg) for arg in sandbox_args)
    if use_auto_allow:
        args.extend(_resolve_arg(arg) for arg in auto_args)
    if use_network_allow:
        args.extend(_resolve_arg(arg) for arg in network_args)

    # Resolve model: CLI override > provider config > None
    resolved_model = model or provider.get("model")

    # Only prepend --model / --effort when the provider's arg template
    # doesn't already contain the placeholder.  Otherwise we double-emit
    # the flag, and for uv-based providers it lands before 'run' (fatal).
    template_has_model = any("{{model}}" in str(a) for a in provider_args)
    template_has_effort = any("{{effort}}" in str(a) for a in provider_args)

    if resolved_model and not template_has_model:
        if isinstance(resolved_model, list):
            args.extend(str(m) for m in resolved_model)
        else:
            args.extend(["--model", str(resolved_model)])

    if effort and not template_has_effort:
        args.extend(["--effort", effort])

    if provider.get("bin") == "gemini":
        if os.name == "nt":
            prompt = prompt.replace("\r\n", "\\n").replace("\n", "\\n")

    for arg in provider_args:
        arg = _resolve_arg(arg)
        if "{{model}}" in arg:
            if resolved_model:
                arg = arg.replace("{{model}}", str(resolved_model))
            else:
                continue  # skip arg if no model available
        if "{{effort}}" in arg:
            if effort:
                arg = arg.replace("{{effort}}", str(effort))
            else:
                continue  # skip arg if no effort specified
        if "{{prompt}}" in arg:
            args.append(arg.replace("{{prompt}}", prompt))
        else:
            args.append(arg)
    return [provider.get("bin", ""), *args]


def build_terminal_command(
    provider: Dict[str, Any],
    prompt: str,
    auto_allow: Optional[bool] = None,
    network_allow: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> List[str]:
    """Build a command for interactive terminal use (tmux sessions).

    Unlike build_llm_command(), this skips the provider's 'args' (which contain
    non-interactive flags like --print, --output-format=stream-json).
    Uses 'terminal-args' if defined, otherwise just passes the prompt as a
    plain positional argument.
    """
    args: List[str] = []
    auto_args = _string_list(provider, "auto-args")
    network_args = _string_list(provider, "network-args")
    sandbox_args = _string_list(provider, "sandbox-args")
    use_auto_allow = _coerce_bool(auto_allow, False)
    use_network_allow = _coerce_bool(network_allow, False)
    use_sandbox_mode = _coerce_bool(sandbox_mode, True)

    if use_sandbox_mode:
        args.extend(_resolve_arg(arg) for arg in sandbox_args)
    if use_auto_allow:
        args.extend(_resolve_arg(arg) for arg in auto_args)
    if use_network_allow:
        args.extend(_resolve_arg(arg) for arg in network_args)

    # Resolve model: CLI override > provider config > None
    resolved_model = model or provider.get("model")

    terminal_args = _string_list(provider, "terminal-args")
    template_has_model = any("{{model}}" in str(a) for a in terminal_args)
    template_has_effort = any("{{effort}}" in str(a) for a in terminal_args)

    if resolved_model and not template_has_model:
        if isinstance(resolved_model, list):
            args.extend(str(m) for m in resolved_model)
        else:
            args.extend(["--model", str(resolved_model)])

    if effort and not template_has_effort:
        args.extend(["--effort", effort])

    if provider.get("bin") == "gemini" and os.name == "nt":
        prompt = prompt.replace("\r\n", "\\n").replace("\n", "\\n")

    if terminal_args:
        for arg in terminal_args:
            arg = _resolve_arg(arg)
            if "{{model}}" in arg:
                if resolved_model:
                    arg = arg.replace("{{model}}", str(resolved_model))
                else:
                    continue
            if "{{effort}}" in arg:
                if effort:
                    arg = arg.replace("{{effort}}", str(effort))
                else:
                    continue
            if "{{prompt}}" in arg:
                args.append(arg.replace("{{prompt}}", prompt))
            else:
                args.append(arg)
    elif str(provider.get("bin") or "").strip().lower() == "codex":
        args.extend(_build_codex_terminal_args(provider, prompt, model=model, effort=effort))
    else:
        args.append(prompt)
    return [provider.get("bin", ""), *args]


def _resolve_provider_env(provider: Dict[str, Any]) -> Dict[str, str]:
    """Expand ${VAR} placeholders in provider env dict using os.environ.

    Values from the provider's 'env' field overwrite any existing env vars
    when passed to the subprocess.
    """
    raw_env = provider.get("env") or {}
    if not isinstance(raw_env, dict):
        return {}
    resolved: Dict[str, str] = {}
    for key, val in raw_env.items():
        if isinstance(val, str):
            resolved[key] = _ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), val)
        else:
            resolved[key] = str(val)
    return resolved


def _llm_subprocess_env(provider_env: Dict[str, str]) -> Dict[str, str]:
    """Build the exact environment for LLM CLI subprocesses.

    LLM CLIs receive the regular process environment except keys loaded from
    config/.env. A provider can opt into a loaded key by declaring it in its
    env block in ai_providers.json5.
    """
    env: Dict[str, str] = dict(os.environ)
    for key in loaded_env_key_names():
        if key not in provider_env:
            env.pop(key, None)
    env.update(provider_env)
    return env


def _provider_uses_codex_json(provider: Dict[str, Any]) -> bool:
    return str(provider.get("bin") or "").strip().lower() == "codex" and "--json" in _string_list(provider, "args")


def _provider_uses_gemini_json(provider: Dict[str, Any]) -> bool:
    return str(provider.get("bin") or "").strip().lower() == "gemini" and "stream-json" in _string_list(provider, "args")


def _provider_uses_claude_json(provider: Dict[str, Any]) -> bool:
    return str(provider.get("bin") or "").strip().lower() == "claude" and any(
        arg.startswith("--output-format=stream-json") for arg in _string_list(provider, "args")
    )


def _provider_uses_opencode_json(provider: Dict[str, Any]) -> bool:
    return str(provider.get("bin") or "").strip().lower() == "opencode" and any(
        arg == "json" or arg.startswith("--format=json") for arg in _string_list(provider, "args")
    )


def _extract_claude_stream_text(payload: Dict[str, Any]) -> List[str]:
    chunks: List[str] = []

    if payload.get("type") == "stream_event":
        event = payload.get("event") or {}
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta" and delta.get("text"):
                chunks.append(str(delta["text"]))

    if payload.get("type") == "assistant":
        message = payload.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "text":
                    continue
                text = part.get("text")
                if text:
                    chunks.append(str(text))

    return chunks


def format_command_for_log(cmd: List[str], env: Optional[Dict[str, str]] = None) -> str:
    ordered_env_parts: List[str] = []
    if env:
        filtered_env = {
            key: value
            for key, value in env.items()
            if value and not re.fullmatch(r"\$\{[A-Za-z0-9_]+\}", value)
        }
        priority_keys = ["OPENAI_BASE_URL", "OPENAI_API_KEY"]
        seen_keys = set()
        for key in priority_keys:
            value = filtered_env.get(key)
            if value is None:
                continue
            ordered_env_parts.append(f"{key}={shlex.quote(value)}")
            seen_keys.add(key)
        for key in sorted(filtered_env):
            if key in seen_keys:
                continue
            ordered_env_parts.append(f"{key}={shlex.quote(filtered_env[key])}")

    rendered_cmd: List[str] = []
    index = 0
    while index < len(cmd):
        current = cmd[index]
        if current in ("--model", "--effort") and index + 1 < len(cmd):
            rendered_cmd.append(f"{current}={shlex.quote(cmd[index + 1])}")
            index += 2
            continue
        rendered_cmd.append(shlex.quote(current))
        index += 1

    parts = ordered_env_parts + rendered_cmd
    return " ".join(part for part in parts if part)


def build_code_system_message(message: str, lang: str) -> str:
    if "TODO" in message:
        return (
            "You are a coding instructor, please think step by step as below then answer the question or edit the coding.\n"
            f"Step 1: Please follow the user's TODO comment instructions to edit or fix the code in {lang} language.\n"
            "Step 2: Please only output the code you edited, and not explain why the request is coding or computer science related.\n"
            "Step 3: Please don't explain the code you have edited.\n"
            "Step 4: If you want to explain the code, please using the code comment format.\n"
            "Step 5: The output needs to be markdown code block, start with ``` follow by coding language name and end with ```.\n"
            "Step 6: Do not output anything before or after the markdown code block."
        )
    return (
        "You are a coding instructor, please think step by step as below then answer the question or finish the completion.\n"
        f"Step 1: Please follow the user's coding comment block to complete the coding in {lang} language.\n"
        "Step 2: Do not update or modify any existing code, only add new code as the user's request in the comment block.\n"
        "Step 3: Please only output the code completion, and not explain why the request is coding or computer science related.\n"
        "Step 4: Please don't explain the code you have completed.\n"
        "Step 5: If you to explain the code, please using the code comment format.\n"
        "Step 6: The output needs to be markdown code block, start with ``` follow by coding language name and end with ```.\n"
        "Step 7: Do not output anything before or after the markdown code block."
    )


def build_chat_system_message() -> str:
    return (
        "I want you to act as a coding instructor in a school, teaching programming to beginners, please think step by step as below then answer the question or help the user.\n"
        "Step 1: The user's input will be coding or computer science related content, please first check the content if it is coding or computer science related.\n"
        "Step 2: If the user's input is not coding or computer science related, please just say one word: \"NOOP\" (Do not need to explain why say \"NOOP\"), and don't need to think the next steps.\n"
        "Step 3: DO NOT need to say it is coding or computer science related, just follow the user's instruction to help the user.\n"
        "Step 4: If the output including code, please make it as markdown code block, start with ``` follow by coding language name and end with ```.\n"
        "Step 5: If the output including code, please add some output message in the code for easy understand\n"
        "Step 6: If the output including code, please add main function if it is necessary to make the code can be run directly with any modification\n"
        "Step 7: You can explain your code, before or after the markdown cod block."
    )


def build_translate_system_message(lang: str, to_lang: str) -> str:
    message = (
        "I want you to act as a coding instructor in a school, teaching programming to beginners, please think step by step below then help the user.\n"
        f"Step 1: Check the language the user provided, then translate the language from {lang} language to {to_lang} language.\n"
        "Step 2: To output the translated code, please make it as markdown code block, start with ``` follow by coding language name and end with ```.\n"
        "Step 3: Please do not explain the code, just provide the translated code only."
    )
    if to_lang in {"python", "javascript", "typescript", "swift"}:
        message += f"\nStep 4: Please do not include the main function for {to_lang} language as it is not necessary!"
    elif to_lang == "objective-c":
        message += "\nStep 4: Please include code \"NSAutoreleasePool* pool = init...\" in the main function and header Foundation.h for objective-c language as it is necessary!"
    return message


def _parse_stream_json_text(provider: Dict[str, Any], output: str) -> str:
    is_codex_json = _provider_uses_codex_json(provider)
    is_gemini_json = _provider_uses_gemini_json(provider)
    is_claude_json = _provider_uses_claude_json(provider)

    if not (is_codex_json or is_gemini_json or is_claude_json):
        return output.strip()

    chunks: List[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue

        if is_codex_json:
            if payload.get("type") == "item.completed":
                item = payload.get("item") or {}
                if item.get("type") == "agent_message" and item.get("text"):
                    chunks.append(str(item["text"]))
        elif is_gemini_json:
            if payload.get("type") == "message" and payload.get("role") == "assistant":
                text = payload.get("content")
                if text:
                    chunks.append(str(text))
        elif is_claude_json:
            chunks.extend(_extract_claude_stream_text(payload))

    if chunks:
        return "".join(chunks).strip()
    return output.strip()


def _messages_to_prompt(messages: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for msg in messages:
        role = str(msg.get("role", "user")).upper()
        content = msg.get("content", "")
        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            text = "\n".join(p for p in parts if p)
        else:
            text = str(content)
        lines.append(f"{role}:\n{text}")
    return "\n\n".join(lines).strip()


def _extract_json_payload(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Empty LLM response")

    def _strip_code_fence(value: str) -> str:
        stripped = value.strip()
        if not stripped.startswith("```"):
            return stripped

        lines = stripped.splitlines()
        if not lines:
            return stripped
        if lines[0].startswith("```"):
            lines = lines[1:]
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _decode_first_object(value: str) -> Optional[Dict[str, Any]]:
        candidate = value.strip()
        if not candidate:
            return None

        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except JSONDecodeError:
            pass

        try:
            repaired = repair_json(candidate)
        except Exception:
            repaired = ""
        if repaired and repaired != candidate:
            try:
                payload = json.loads(repaired)
                if isinstance(payload, dict):
                    return payload
            except JSONDecodeError:
                pass

        decoder = json.JSONDecoder()
        for source in (candidate, repaired):
            if not source:
                continue
            for idx, ch in enumerate(source):
                if ch not in "[{":
                    continue
                try:
                    obj, _ = decoder.raw_decode(source[idx:])
                except JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    return obj
        return None

    candidates: List[str] = [text]
    stripped = _strip_code_fence(text)
    if stripped and stripped != text:
        candidates.append(stripped)

    for candidate in candidates:
        payload = _decode_first_object(candidate)
        if payload is None:
            continue

        # Some providers wrap the real assistant JSON inside a transport object.
        nested_result = payload.get("result")
        if isinstance(nested_result, dict):
            return nested_result
        if isinstance(nested_result, str):
            nested_payload = _decode_first_object(_strip_code_fence(nested_result))
            if nested_payload is not None:
                return nested_payload

        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") != "text":
                        continue
                    nested_text = str(part.get("text", "")).strip()
                    if not nested_text:
                        continue
                    nested_payload = _decode_first_object(_strip_code_fence(nested_text))
                    if nested_payload is not None:
                        return nested_payload

        return payload

    raise ValueError("LLM response does not contain a valid JSON object")


def llm_get_text(
    messages: List[Dict[str, Any]],
    provider_id: Optional[str] = None,
    client_id: str = "workflow",
    auto_allow: Optional[bool] = None,
    network_allow: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
) -> str:
    _ = client_id
    provider = get_background_provider(provider_id)
    prompt = _messages_to_prompt(messages)
    cmd = build_llm_command(
        provider,
        prompt,
        auto_allow=auto_allow,
        network_allow=network_allow,
        sandbox_mode=sandbox_mode,
    )
    if not cmd[0]:
        raise RuntimeError("No LLM binary configured")

    logger.info(
        "[llm] invoke client_id=%s provider_id=%s command=%s",
        client_id,
        provider.get("id"),
        format_command_for_log(cmd, _resolve_provider_env(provider)),
    )
    logger.info("[llm] prompt client_id=%s provider_id=%s\n%s", client_id, provider.get("id"), prompt)

    provider_env = _resolve_provider_env(provider)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            env=_llm_subprocess_env(provider_env),
            **_popen_kwargs(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"LLM command not found: {cmd[0]}") from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    output = "\n".join(part for part in (stdout, stderr) if part).strip()
    logger.info(
        "[llm] output client_id=%s provider_id=%s returncode=%s\n%s",
        client_id,
        provider.get("id"),
        proc.returncode,
        output,
    )
    if proc.returncode not in (0, None):
        raise RuntimeError(f"LLM command failed (provider={provider.get('id')}): {output}")

    output_source = stdout or stderr
    parsed = _parse_stream_json_text(provider, output_source)
    return parsed or output


def llm_get_json(
    messages: List[Dict[str, Any]],
    provider_id: Optional[str] = None,
    client_id: str = "workflow",
    auto_allow: Optional[bool] = None,
    network_allow: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
) -> Dict[str, Any]:
    text = llm_get_text(
        messages,
        provider_id=provider_id,
        client_id=client_id,
        auto_allow=auto_allow,
        network_allow=network_allow,
        sandbox_mode=sandbox_mode,
    )
    return _extract_json_payload(text)


def llm_stream(
    prompt: str,
    provider_id: Optional[str] = None,
    client_id: str = "workflow",
    auto_allow: Optional[bool] = None,
    network_allow: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
) -> Iterable[bytes]:
    provider = get_background_provider(provider_id)
    cmd = build_llm_command(
        provider,
        prompt,
        auto_allow=auto_allow,
        network_allow=network_allow,
        sandbox_mode=sandbox_mode,
    )
    if not cmd[0]:
        yield b"[-ERROR-]"
        return

    collected_output = bytearray()
    provider_env = _resolve_provider_env(provider)
    logger.info(
        "[llm] stream_invoke client_id=%s provider_id=%s command=%s",
        client_id,
        provider.get("id"),
        format_command_for_log(cmd, provider_env),
    )
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            env=_llm_subprocess_env(provider_env),
            **_popen_kwargs(),
        )
    except FileNotFoundError:
        logger.error("llm command not found: %s (provider=%s)", cmd[0], provider.get("id"))
        yield b"[-ERROR-]"
        return

    with RUNNING_LOCK:
        RUNNING_PROCESSES[client_id] = proc

    try:
        assert proc.stdout is not None
        is_codex_json = _provider_uses_codex_json(provider)
        is_gemini_json = _provider_uses_gemini_json(provider)
        is_claude_json = _provider_uses_claude_json(provider)
        is_opencode_json = _provider_uses_opencode_json(provider)
        if not is_codex_json and not is_gemini_json and not is_claude_json and not is_opencode_json:
            while True:
                chunk = proc.stdout.read(1024)
                if not chunk:
                    break
                collected_output.extend(chunk)
                yield chunk
        else:
            buffer = b""
            while True:
                chunk = proc.stdout.read(1024)
                if not chunk:
                    break
                collected_output.extend(chunk)
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line.startswith(b"{"):
                        continue
                    try:
                        payload = json.loads(line.decode("utf-8", errors="replace"))
                    except Exception:
                        continue
                    if is_codex_json:
                        if payload.get("type") == "item.completed":
                            item = payload.get("item") or {}
                            if item.get("type") == "agent_message":
                                text = item.get("text")
                                if text:
                                    yield text.encode("utf-8")
                    elif is_gemini_json:
                        if payload.get("type") == "message" and payload.get("role") == "assistant":
                            text = payload.get("content")
                            if text:
                                yield text.encode("utf-8")
                    elif is_claude_json:
                        for text in _extract_claude_stream_text(payload):
                            if text:
                                yield text.encode("utf-8")
                    elif is_opencode_json:
                        if payload.get("type") == "text":
                            part = payload.get("part") or {}
                            if part.get("type") == "text":
                                text = part.get("text")
                                if text:
                                    yield text.encode("utf-8")
            tail = buffer.strip()
            if tail.startswith(b"{"):
                try:
                    payload = json.loads(tail.decode("utf-8", errors="replace"))
                    if is_codex_json:
                        if payload.get("type") == "item.completed":
                            item = payload.get("item") or {}
                            if item.get("type") == "agent_message":
                                text = item.get("text")
                                if text:
                                    yield text.encode("utf-8")
                    elif is_gemini_json:
                        if payload.get("type") == "message" and payload.get("role") == "assistant":
                            text = payload.get("content")
                            if text:
                                yield text.encode("utf-8")
                    elif is_claude_json:
                        for text in _extract_claude_stream_text(payload):
                            if text:
                                yield text.encode("utf-8")
                    elif is_opencode_json:
                        if payload.get("type") == "text":
                            part = payload.get("part") or {}
                            if part.get("type") == "text":
                                text = part.get("text")
                                if text:
                                    yield text.encode("utf-8")
                except Exception:
                    pass
    finally:
        with RUNNING_LOCK:
            RUNNING_PROCESSES.pop(client_id, None)
        if proc.poll() is None:
            proc.terminate()

    if proc.returncode not in (0, None):
        output_text = collected_output.decode("utf-8", errors="replace")
        logger.error("llm error provider=%s returncode=%s", provider.get("id"), proc.returncode)
        if output_text:
            logger.error("llm cli output:\n%s", output_text)
        yield b"[-ERROR-]"
    yield b"[-DONE-]"


def stop_client(client_id: str) -> str:
    if not client_id:
        return "missing"
    with RUNNING_LOCK:
        proc = RUNNING_PROCESSES.get(client_id)
    if proc and proc.poll() is None:
        proc.terminate()
        return "stopped"
    return "idle"
