import base64
import asyncio
import json
import os
import math
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from fastapi import HTTPException

from llm_service import get_image_provider
from settings import logger


GEMINI_ALLOWED_ASPECT_RATIOS = (
    "1:1",
    "1:4",
    "1:8",
    "2:3",
    "3:2",
    "3:4",
    "4:1",
    "4:3",
    "4:5",
    "5:4",
    "8:1",
    "9:16",
    "16:9",
    "21:9",
)

DEFAULT_IMAGE_STYLE_SIZES = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}


def _parse_image_size(size: Optional[str]) -> Optional[tuple[int, int]]:
    if not size:
        return None

    normalized = size.lower().strip().replace(" ", "")
    if "x" not in normalized:
        return None

    width_str, height_str = normalized.split("x", 1)
    try:
        width = int(width_str)
        height = int(height_str)
    except ValueError:
        return None

    if width < 1 or height < 1:
        return None
    return width, height


def _normalize_image_style(style: Optional[str]) -> str:
    normalized = (style or "portrait").strip().lower()
    if normalized in DEFAULT_IMAGE_STYLE_SIZES:
        return normalized
    return "portrait"


def resolve_image_size_for_provider(provider: Dict[str, Any], style: Optional[str]) -> str:
    normalized_style = _normalize_image_style(style)
    provider_size = provider.get("size")

    if isinstance(provider_size, dict):
        configured_size = provider_size.get(normalized_style)
        if isinstance(configured_size, str) and _parse_image_size(configured_size):
            return configured_size
    elif isinstance(provider_size, str) and _parse_image_size(provider_size):
        return provider_size

    return DEFAULT_IMAGE_STYLE_SIZES[normalized_style]


def _closest_gemini_aspect_ratio(size: Optional[str], default: str) -> str:
    parsed = _parse_image_size(size)
    if not parsed:
        return default

    width, height = parsed
    target_ratio = width / height
    best_ratio = default
    best_delta = math.inf
    for candidate in GEMINI_ALLOWED_ASPECT_RATIOS:
        ratio_width, ratio_height = (int(part) for part in candidate.split(":", 1))
        delta = abs((ratio_width / ratio_height) - target_ratio)
        if delta < best_delta:
            best_delta = delta
            best_ratio = candidate
    return best_ratio


def _gemini_image_size_value(size: Optional[str], default: str) -> str:
    parsed = _parse_image_size(size)
    if parsed == (512, 512):
        return "512"
    return default


def _extract_gemini_response_parts(response: Any) -> Iterable[Any]:
    parts = getattr(response, "parts", None)
    if parts:
        return parts

    candidates = getattr(response, "candidates", None) or []
    if candidates:
        content = getattr(candidates[0], "content", None)
        candidate_parts = getattr(content, "parts", None)
        if candidate_parts:
            return candidate_parts
    return []


def _extract_mcp_text_content(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    content = payload.get("content")
    if not isinstance(content, list):
        return None

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _skill_pilot_generate_image(prompt: str, provider: Dict[str, Any], size: Optional[str]) -> Path:
    api_key = (os.getenv("SKILL_PILOT_API_KEY") or "").strip()
    base_url = (os.getenv("SKILL_PILOT_BASE_URL") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="SKILL_PILOT_API_KEY is not configured")
    if not base_url:
        raise HTTPException(status_code=500, detail="SKILL_PILOT_BASE_URL is not configured")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise HTTPException(status_code=500, detail="openai package is not installed") from exc

    model = provider.get("model", "skill-pilot-image")
    chosen_size = size or provider.get("size", "1024x1536")
    quality = provider.get("quality", "low")

    client = OpenAI(api_key=api_key, base_url=base_url)
    request: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    if chosen_size:
        request["size"] = chosen_size
    if quality:
        request["quality"] = quality

    try:
        result = client.images.generate(**request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Skill Pilot image generation failed: {exc}") from exc

    b64 = None
    if getattr(result, "data", None):
        first = result.data[0]
        b64 = getattr(first, "b64_json", None)

    if not b64:
        raise HTTPException(status_code=502, detail="Skill Pilot image generation returned no image")

    out = Path(f"/tmp/webui_image_{uuid.uuid4().hex}.png")
    out.write_bytes(base64.b64decode(b64))
    return out


def _openai_generate_image(prompt: str, provider: Dict[str, Any], size: Optional[str]) -> Path:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise HTTPException(status_code=500, detail="openai package is not installed") from exc

    model = provider.get("model", "gpt-image-1")
    chosen_size = size or provider.get("size", "1024x1536")
    quality = provider.get("quality", "low")

    client = OpenAI(api_key=api_key)
    request: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    if chosen_size:
        request["size"] = chosen_size
    if quality:
        request["quality"] = quality

    try:
        result = client.images.generate(**request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI image generation failed: {exc}") from exc

    b64 = None
    if getattr(result, "data", None):
        first = result.data[0]
        b64 = getattr(first, "b64_json", None)

    if not b64:
        raise HTTPException(status_code=502, detail="OpenAI image generation returned no image")

    out = Path(f"/tmp/webui_image_{uuid.uuid4().hex}.png")
    out.write_bytes(base64.b64decode(b64))
    return out


def _gemini_generate_image(prompt: str, provider: Dict[str, Any], size: Optional[str]) -> Path:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLEAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY/GOOGLEAI_API_KEY/GOOGLE_API_KEY is not configured")

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise HTTPException(status_code=500, detail="google-genai package is not installed") from exc

    model = provider.get("model", "gemini-3.1-flash-image-preview")
    aspect_ratio = _closest_gemini_aspect_ratio(size, provider.get("aspect_ratio", "1:1"))
    image_size = _gemini_image_size_value(size, str(provider.get("resolution", "1K")))

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini image generation failed: {exc}") from exc

    out = Path(f"/tmp/webui_image_{uuid.uuid4().hex}.png")
    for part in _extract_gemini_response_parts(response):
        try:
            image_obj = part.as_image()
        except Exception:
            image_obj = None
        if image_obj is None:
            continue
        try:
            image_obj.save(str(out))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to save Gemini image: {exc}") from exc
        return out

    raise HTTPException(status_code=502, detail="Gemini image generation returned no image")


def _media_mcp_generate_image(prompt: str, provider: Dict[str, Any], size: Optional[str]) -> Path:
    parsed_size = _parse_image_size(size or provider.get("size"))
    width, height = parsed_size or (720, 1280)
    repo_root = Path(__file__).resolve().parents[2]
    request = {
        "server_id": "media",
        "tool_name": "text_to_image",
        "arguments": {
            "prompt": prompt,
            "width": width,
            "height": height,
        },
    }

    try:
        result = subprocess.run(
            [str(repo_root / "core/bin/tool-cli"), "request", json.dumps(request)],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Media MCP image generation failed: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise HTTPException(status_code=502, detail=f"Media MCP image generation failed: {stderr}")

    output = (result.stdout or "").strip()
    if not output:
        raise HTTPException(status_code=502, detail="Media MCP image generation returned no output")

    try:
        response = json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Media MCP image generation returned invalid JSON: {output}") from exc

    if not isinstance(response, dict):
        raise HTTPException(status_code=502, detail="Media MCP image generation returned an unexpected response")
    if response.get("status") != "ok":
        raise HTTPException(status_code=502, detail=str(response.get("detail") or "Media MCP image generation failed"))

    result_payload = response.get("result")
    raw_path = _extract_mcp_text_content(result_payload)
    if not raw_path:
        raise HTTPException(status_code=502, detail=f"Media MCP image generation returned no local image path: {output}")

    path = Path(raw_path).expanduser()
    if not path.is_file():
        raise HTTPException(status_code=502, detail=f"Media MCP image generation returned a missing file path: {raw_path}")
    return path.resolve()


def generate_image_file(prompt: str, provider_id: Optional[str] = None, size: Optional[str] = None) -> str:
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")

    provider = get_image_provider(provider_id)
    provider_name = provider.get("id")
    resolved_size = size if _parse_image_size(size) else resolve_image_size_for_provider(provider, "portrait")

    if provider_name == "skill-pilot":
        path = _skill_pilot_generate_image(prompt, provider, resolved_size)
    elif provider_name == "openai":
        path = _openai_generate_image(prompt, provider, resolved_size)
    elif provider_name == "gemini":
        path = _gemini_generate_image(prompt, provider, resolved_size)
    elif provider_name == "media-mcp":
        path = _media_mcp_generate_image(prompt, provider, resolved_size)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported image provider: {provider_name}")

    logger.info("Created image file: %s", path)
    return str(path)


async def generate_image_from_prompt(
    positivePrompt: str,
    negativePrompt: Optional[str] = None,
    style: str = "portrait",
    provider: Optional[str] = None,
    **_: Any,
) -> str:
    _ = negativePrompt
    provider_config = get_image_provider(provider)
    image_size = resolve_image_size_for_provider(provider_config, style)

    path = await asyncio.to_thread(
        generate_image_file,
        positivePrompt,
        provider_config.get("id"),
        image_size,
    )
    return path
