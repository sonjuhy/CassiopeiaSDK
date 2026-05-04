"""agent.py — AgentBase 단위 테스트"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cassiopeia_sdk.agent import AgentBase
from cassiopeia_sdk.client import AgentMessage


def _make_msg(action: str, payload: dict) -> AgentMessage:
    return AgentMessage(sender="orchestra", receiver="my_agent", action=action, payload=payload)


class ConcreteAgent(AgentBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received: list[AgentMessage] = []

    async def handle(self, msg: AgentMessage) -> None:
        self.received.append(msg)


@pytest.fixture
def agent():
    a = ConcreteAgent("my_agent", redis_url="redis://localhost:6379")
    a.client.send_message = AsyncMock(return_value=True)
    return a


class TestSendResult:
    async def test_sends_to_orchestra(self, agent):
        await agent.send_result("task-1", {"answer": "ok"})
        agent.client.send_message.assert_awaited_once()
        kwargs = agent.client.send_message.call_args.kwargs
        assert kwargs["receiver"] == "orchestra"
        assert kwargs["action"] == "agent_result"

    async def test_completed_status_when_no_error(self, agent):
        await agent.send_result("task-1", {})
        payload = agent.client.send_message.call_args.kwargs["payload"]
        assert payload["status"] == "COMPLETED"
        assert payload["error"] is None

    async def test_failed_status_when_error(self, agent):
        await agent.send_result("task-1", {}, error="뭔가 잘못됨")
        payload = agent.client.send_message.call_args.kwargs["payload"]
        assert payload["status"] == "FAILED"
        assert payload["error"] == "뭔가 잘못됨"

    async def test_task_id_in_payload(self, agent):
        await agent.send_result("task-xyz", {"data": 1})
        payload = agent.client.send_message.call_args.kwargs["payload"]
        assert payload["task_id"] == "task-xyz"


class TestRequestLLM:
    async def test_sends_llm_call_to_orchestra(self, agent):
        async def _resolve():
            await asyncio.sleep(0)
            task_id = list(agent._pending_llm.keys())[0]
            agent._resolve_llm({"task_id": task_id, "status": "completed", "content": "응답"})

        asyncio.create_task(_resolve())
        result = await agent.request_llm([{"role": "user", "content": "안녕"}])

        agent.client.send_message.assert_awaited()
        kwargs = agent.client.send_message.call_args.kwargs
        assert kwargs["action"] == "llm_call"
        assert kwargs["receiver"] == "orchestra"

    async def test_returns_llm_response(self, agent):
        async def _resolve():
            await asyncio.sleep(0)
            task_id = list(agent._pending_llm.keys())[0]
            agent._resolve_llm({
                "task_id": task_id,
                "status": "completed",
                "content": "테스트 응답",
                "usage": {"total_tokens": 50},
            })

        asyncio.create_task(_resolve())
        result = await agent.request_llm([{"role": "user", "content": "질문"}])
        assert result["content"] == "테스트 응답"

    async def test_timeout_raises(self, agent):
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await agent.request_llm([{"role": "user", "content": "질문"}], timeout=0.01)


class TestLLMResultRouting:
    async def test_llm_result_resolves_future(self, agent):
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        agent._pending_llm["task-abc"] = fut

        agent._resolve_llm({"task_id": "task-abc", "status": "completed", "content": "ok"})
        assert fut.done()
        assert fut.result()["content"] == "ok"

    async def test_unknown_task_id_ignored(self, agent):
        agent._resolve_llm({"task_id": "unknown-id", "content": "orphan"})
        # 예외 없이 통과하면 OK


class TestRegister:
    async def test_register_posts_to_orchestra(self, agent):
        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            result = await agent.register(
                orchestra_url="http://localhost:8000",
                capabilities=["my_action"],
                api_key="test-key",
            )

        assert result is True
        mock_http.post.assert_awaited_once()
        call_kwargs = mock_http.post.call_args
        assert "my_agent" in str(call_kwargs)

    async def test_register_returns_false_on_failure(self, agent):
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            result = await agent.register("http://localhost:8000", capabilities=[])

        assert result is False
