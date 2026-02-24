from typing import Any, Dict, List, Optional, Tuple

from llm_service import llm_get_json, llm_get_text
from tts_service import text_to_speech_file


class LLM:
    def __init__(self, model: Optional[str] = None, use_pro: bool = False):
        _ = model
        _ = use_pro

    async def chat(self, member_id: Optional[int], messages: List[Dict[str, Any]], **_: Any):
        _ = member_id
        text = llm_get_text(messages)
        return text, None, None, None, None

    async def get_json(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **_: Any):
        _ = model
        return llm_get_json(messages), None

    async def text_to_audio_file(
        self,
        text: str,
        voice: str = "alloy",
        emotion: Optional[str] = None,
        format: str = "mp3",
        speed: float = 1.0,
        **_: Any,
    ) -> Tuple[str, float]:
        _ = emotion
        _ = speed
        return text_to_speech_file(text, provider_id="openai", voice=voice, output_format=format), 0.0
