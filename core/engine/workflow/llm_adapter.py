import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from llm_service import llm_get_json, llm_get_text

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AgentCliLLMAdapter:
    def __init__(self, provider_id: Optional[str] = None, cli_session_id: Optional[str] = None):
        self.provider_id = provider_id
        self.cli_session_id = cli_session_id or str(uuid.uuid4())
        self._conversation_payload: List[Dict[str, str]] = []

    def _message_payload(self, messages: List[Any]) -> List[Dict[str, str]]:
        message_payload: List[Dict[str, str]] = []
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
        return message_payload

    def _payload_to_send(self, message_payload: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not self._conversation_payload:
            return message_payload
        prefix_len = len(self._conversation_payload)
        if message_payload[:prefix_len] == self._conversation_payload:
            return message_payload[prefix_len:]
        return message_payload

    async def ainvoke(self, messages: List[Any], config: Optional[Dict[str, Any]] = None) -> AIMessage:
        message_payload = self._message_payload(messages)
        invoke_payload = self._payload_to_send(message_payload)

        model_kwargs = (((config or {}).get("configurable") or {}).get("model_kwargs") or {})
        response_format = model_kwargs.get("response_format")
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0}

        if isinstance(response_format, dict) and response_format.get("type") == "json_object":
            data = llm_get_json(
                invoke_payload,
                provider_id=self.provider_id,
                client_id="workflow",
                cli_session_id=self.cli_session_id,
                cwd=PROJECT_ROOT,
            )
            response = AIMessage(
                content=json.dumps(data, ensure_ascii=False),
                response_metadata={"token_usage": token_usage},
            )
            self._conversation_payload = [*message_payload, {"role": "assistant", "content": response.content}]
            return response

        text = llm_get_text(
            invoke_payload,
            provider_id=self.provider_id,
            client_id="workflow",
            cli_session_id=self.cli_session_id,
            cwd=PROJECT_ROOT,
        )
        response = AIMessage(content=text, response_metadata={"token_usage": token_usage})
        self._conversation_payload = [*message_payload, {"role": "assistant", "content": response.content}]
        return response
