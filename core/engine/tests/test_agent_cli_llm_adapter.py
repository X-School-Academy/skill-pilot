import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow.llm_adapter import AgentCliLLMAdapter
from workflow.llm_adapter import PROJECT_ROOT


def test_agent_cli_llm_adapter_sends_only_appended_messages_after_first_invoke():
    adapter = AgentCliLLMAdapter(cli_session_id="workflow-abc")
    calls = []

    def fake_llm_get_text(messages, **kwargs):
        calls.append((messages, kwargs))
        return "first response" if len(calls) == 1 else "second response"

    async def run_invokes():
        first_messages = [
            SystemMessage(content="system"),
            HumanMessage(content="first"),
        ]
        first_response = await adapter.ainvoke(first_messages)
        assert isinstance(first_response, AIMessage)

        second_messages = [
            *first_messages,
            first_response,
            HumanMessage(content="second"),
        ]
        return await adapter.ainvoke(second_messages)

    with patch("workflow.llm_adapter.llm_get_text", side_effect=fake_llm_get_text):
        second_response = asyncio.run(run_invokes())

    assert second_response.content == "second response"
    assert calls[0][0] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "first"},
    ]
    assert calls[1][0] == [{"role": "user", "content": "second"}]
    assert calls[0][1]["cli_session_id"] == "workflow-abc"
    assert calls[1][1]["cli_session_id"] == "workflow-abc"
    assert calls[0][1]["cwd"] == PROJECT_ROOT
    assert calls[1][1]["cwd"] == PROJECT_ROOT
