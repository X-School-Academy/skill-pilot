import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from llm_service import llm_get_json, llm_get_text


@dataclass
class LLMResponse:
    content: str
    response_metadata: Dict[str, Any]


class WorkflowLLMAdapter:
    def __init__(self, provider_id: Optional[str] = None):
        self.provider_id = provider_id

    async def ainvoke(self, messages: List[Any], config: Optional[Dict[str, Any]] = None) -> LLMResponse:
        message_payload: List[Dict[str, Any]] = []
        for message in messages:
            role = getattr(message, "type", None) or getattr(message, "role", None) or "user"
            content = getattr(message, "content", message)
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            elif role == "system":
                role = "system"
            else:
                role = "user"
            message_payload.append({"role": role, "content": str(content)})

        model_kwargs = (((config or {}).get("configurable") or {}).get("model_kwargs") or {})
        response_format = model_kwargs.get("response_format")
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0}

        if isinstance(response_format, dict) and response_format.get("type") == "json_object":
            data = llm_get_json(message_payload, provider_id=self.provider_id, client_id="workflow")
            return LLMResponse(content=json.dumps(data, ensure_ascii=False), response_metadata={"token_usage": token_usage})

        text = llm_get_text(message_payload, provider_id=self.provider_id, client_id="workflow")
        return LLMResponse(content=text, response_metadata={"token_usage": token_usage})
