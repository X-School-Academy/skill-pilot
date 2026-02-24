import base64
import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from llm_service import get_image_provider
from settings import DEFAULT_IMAGE_PROVIDER, logger


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


def _gemini_generate_image(prompt: str, provider: Dict[str, Any]) -> Path:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLEAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY/GOOGLEAI_API_KEY/GOOGLE_API_KEY is not configured")

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise HTTPException(status_code=500, detail="google-genai package is not installed") from exc

    model = provider.get("model", "imagen-4.0-generate-001")
    number_of_images = int(provider.get("number_of_images", 1) or 1)
    if number_of_images < 1:
        number_of_images = 1

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=number_of_images),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini image generation failed: {exc}") from exc

    generated_images = getattr(response, "generated_images", None) or []
    if not generated_images:
        raise HTTPException(status_code=502, detail="Gemini image generation returned no image")

    first = generated_images[0]
    image_obj = getattr(first, "image", None)
    if image_obj is None:
        raise HTTPException(status_code=502, detail="Gemini image response did not include image data")

    out = Path(f"/tmp/webui_image_{uuid.uuid4().hex}.png")
    try:
        image_obj.save(str(out))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to save Gemini image: {exc}") from exc
    return out


def generate_image_file(prompt: str, provider_id: Optional[str] = None, size: Optional[str] = None) -> str:
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")

    provider = get_image_provider(provider_id or DEFAULT_IMAGE_PROVIDER)
    provider_name = provider.get("id")

    if provider_name == "openai":
        path = _openai_generate_image(prompt, provider, size)
    elif provider_name == "gemini":
        path = _gemini_generate_image(prompt, provider)
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
) -> tuple[str, float]:
    _ = negativePrompt
    image_size = None
    if style in {"icon", "square"}:
        image_size = "1024x1024"
    elif style == "landscape":
        image_size = "1536x1024"
    elif style == "portrait":
        image_size = "1024x1536"

    path = await asyncio.to_thread(
        generate_image_file,
        positivePrompt,
        provider,
        image_size,
    )
    return path, 0.0
