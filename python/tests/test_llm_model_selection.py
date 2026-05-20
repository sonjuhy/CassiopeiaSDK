"""
LLM Gateway 모델 선택 기능 + Pydantic 검증 — TDD 테스트

대상:
  - cassiopeia_sdk.schemas.LLMRequest  (Pydantic BaseModel, 검증 포함)
  - cassiopeia_sdk.schemas.LLMResponse (Pydantic BaseModel)
  - cassiopeia_sdk.agent.AgentBase.request_llm (model 파라미터, 전송 전 검증)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from cassiopeia_sdk.agent import AgentBase
from cassiopeia_sdk.schemas import LLMRequest, LLMResponse


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_agent() -> AgentBase:
    class ConcreteAgent(AgentBase):
        async def handle(self, msg):  # type: ignore[override]
            pass

    agent = ConcreteAgent("test_agent", redis_url="redis://localhost:6379")
    agent.client.send_message = AsyncMock(return_value=True)
    return agent


def _resolve_llm(agent: AgentBase, extra: dict | None = None) -> asyncio.Task:
    """백그라운드에서 LLM 응답을 즉시 resolve하는 태스크."""
    async def _inner() -> None:
        await asyncio.sleep(0)
        task_id = next(iter(agent._pending_llm))
        payload: dict = {
            "task_id": task_id,
            "status": "completed",
            "content": "테스트 응답",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "error": None,
            "model": None,
        }
        if extra:
            payload.update(extra)
        agent._resolve_llm(payload)

    return asyncio.create_task(_inner())


# ===========================================================================
# 1. LLMRequest — 필드 기본값 및 설정
# ===========================================================================

class TestLLMRequestModelField:

    def test_model_defaults_to_none_when_not_specified(self) -> None:
        """TC-01: model 미지정 시 LLMRequest.model은 None"""
        req = LLMRequest(
            task_id="task-001",
            agent_id="agent-001",
            messages=[{"role": "user", "content": "안녕"}],
        )
        assert req.model is None  # Pydantic 속성 접근

    def test_model_is_set_when_specified(self) -> None:
        """TC-02: model 지정 시 LLMRequest에 해당 값이 설정됨"""
        req = LLMRequest(
            task_id="task-002",
            agent_id="agent-002",
            messages=[{"role": "user", "content": "질문"}],
            max_tokens=800,
            temperature=0.3,
            model="gemini-1.5-pro",
        )
        assert req.model == "gemini-1.5-pro"

    def test_max_tokens_default_is_500(self) -> None:
        """TC-06: max_tokens 기본값 500"""
        req = LLMRequest(
            task_id="task-003",
            agent_id="agent-003",
            messages=[{"role": "user", "content": "질문"}],
        )
        assert req.max_tokens == 500

    def test_temperature_default_is_0_7(self) -> None:
        """TC-07: temperature 기본값 0.7"""
        req = LLMRequest(
            task_id="task-004",
            agent_id="agent-004",
            messages=[{"role": "user", "content": "질문"}],
        )
        assert req.temperature == 0.7

    def test_system_role_allowed_in_messages(self) -> None:
        """TC-05: messages에 system role 포함 가능 (신규 허용)"""
        messages: list[dict] = [
            {"role": "system", "content": "너는 문서 요약 전문가야"},
            {"role": "user", "content": "이 내용을 요약해줘"},
        ]
        req = LLMRequest(
            task_id="task-005",
            agent_id="agent-005",
            messages=messages,
            model="gemini-1.5-pro",
        )
        roles: list[str] = [m["role"] for m in req.messages]
        assert "system" in roles
        assert req.messages[0]["content"] == "너는 문서 요약 전문가야"


# ===========================================================================
# 2. LLMRequest — 검증 (Pydantic ValidationError)
# ===========================================================================

class TestLLMRequestValidation:

    def test_invalid_model_format_raises_validation_error(self) -> None:
        """TC-V01: model에 허용되지 않는 문자(공백·특수문자) 포함 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                model="invalid model!",  # 공백·느낌표 포함
            )

    def test_model_exceeds_max_length_raises_validation_error(self) -> None:
        """TC-V02: model 101자 초과 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                model="a" * 101,
            )

    def test_model_min_length_one_char_is_valid(self) -> None:
        """TC-V02 경계: model 1자는 유효"""
        req = LLMRequest(
            task_id="t", agent_id="a",
            messages=[{"role": "user", "content": "hi"}],
            model="a",
        )
        assert req.model == "a"

    def test_model_max_length_100_chars_is_valid(self) -> None:
        """TC-V02 경계: model 100자는 유효"""
        req = LLMRequest(
            task_id="t", agent_id="a",
            messages=[{"role": "user", "content": "hi"}],
            model="a" * 100,
        )
        assert len(req.model) == 100

    def test_max_tokens_exceeds_2000_raises_validation_error(self) -> None:
        """TC-V03: max_tokens 2001 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=2001,
            )

    def test_max_tokens_zero_raises_validation_error(self) -> None:
        """TC-V03 경계: max_tokens 0 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=0,
            )

    def test_temperature_above_1_raises_validation_error(self) -> None:
        """TC-V04: temperature 1.1 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                temperature=1.1,
            )

    def test_temperature_below_0_raises_validation_error(self) -> None:
        """TC-V04 경계: temperature -0.1 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                temperature=-0.1,
            )

    def test_invalid_role_in_messages_raises_validation_error(self) -> None:
        """TC-V05: 허용되지 않는 role 시 ValidationError"""
        with pytest.raises(ValidationError):
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "function", "content": "hi"}],
            )

    def test_error_message_contains_korean_description(self) -> None:
        """TC-V01 보조: model 형식 오류 메시지가 명세 문구를 포함함"""
        with pytest.raises(ValidationError) as exc_info:
            LLMRequest(
                task_id="t", agent_id="a",
                messages=[{"role": "user", "content": "hi"}],
                model="invalid model!",
            )
        assert "model은 영문자" in str(exc_info.value)


# ===========================================================================
# 3. LLMResponse — 필드 기본값 및 설정
# ===========================================================================

class TestLLMResponseModelField:

    def test_model_field_can_be_none(self) -> None:
        """TC-03: LLMResponse.model이 None일 수 있음"""
        resp = LLMResponse(
            task_id="task-006",
            status="completed",
            content="요약 결과",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            error=None,
            model=None,
        )
        assert resp.model is None

    def test_model_field_can_hold_model_name(self) -> None:
        """TC-04: LLMResponse.model에 모델명 설정 가능"""
        resp = LLMResponse(
            task_id="task-007",
            status="completed",
            content="요약 결과",
            usage={},
            error=None,
            model="gemini-1.5-pro",
        )
        assert resp.model == "gemini-1.5-pro"

    def test_model_attribute_always_exists(self) -> None:
        """TC-04 보조: LLMResponse 인스턴스에 항상 model 속성이 존재"""
        resp = LLMResponse(
            task_id="task-008",
            status="completed",
            content="ok",
            usage={},
            error=None,
            model="gemini-1.5-pro",
        )
        assert hasattr(resp, "model")


# ===========================================================================
# 4. AgentBase.request_llm — 페이로드 및 검증
# ===========================================================================

class TestRequestLLMModelParameter:

    async def test_model_not_in_payload_when_not_specified(self) -> None:
        """TC-08: model 미지정 시 payload에 model 키 없음 (exclude_none)"""
        agent = _make_agent()
        _resolve_llm(agent)

        await agent.request_llm([{"role": "user", "content": "질문"}])

        sent_payload: dict = agent.client.send_message.call_args.kwargs["payload"]
        assert "model" not in sent_payload  # exclude_none=True 효과

    async def test_model_included_in_payload_when_specified(self) -> None:
        """TC-09: model 지정 시 llm_call payload에 model 필드 포함"""
        agent = _make_agent()
        _resolve_llm(agent, extra={"model": "gemini-1.5-pro"})

        await agent.request_llm(
            messages=[{"role": "user", "content": "질문"}],
            model="gemini-1.5-pro",
        )

        sent_payload: dict = agent.client.send_message.call_args.kwargs["payload"]
        assert sent_payload["model"] == "gemini-1.5-pro"

    async def test_system_role_message_sent_in_payload(self) -> None:
        """TC-10: system role 포함 메시지로 request_llm 정상 호출"""
        agent = _make_agent()
        messages: list[dict] = [
            {"role": "system", "content": "너는 전문가야"},
            {"role": "user", "content": "요약해줘"},
        ]
        _resolve_llm(agent)

        await agent.request_llm(messages=messages)

        sent_payload: dict = agent.client.send_message.call_args.kwargs["payload"]
        roles: list[str] = [m["role"] for m in sent_payload["messages"]]
        assert "system" in roles

    async def test_backward_compatible_without_model_param(self) -> None:
        """TC-11: model 파라미터 없이 호출 시 기존 동작과 동일 (하위 호환)"""
        agent = _make_agent()
        _resolve_llm(agent)

        result = await agent.request_llm(
            messages=[{"role": "user", "content": "안녕"}],
            max_tokens=500,
            temperature=0.7,
        )

        assert result.status == "completed"  # Pydantic 속성 접근
        agent.client.send_message.assert_awaited_once()

    async def test_model_in_response_when_specified(self) -> None:
        """TC-09 보조: model 지정 요청의 응답에 model 속성 반환"""
        agent = _make_agent()
        _resolve_llm(agent, extra={"model": "gemini-1.5-pro"})

        result = await agent.request_llm(
            messages=[{"role": "user", "content": "질문"}],
            model="gemini-1.5-pro",
        )

        assert result.model == "gemini-1.5-pro"  # Pydantic 속성 접근

    async def test_model_none_in_response_when_not_specified(self) -> None:
        """TC-08 보조: model 미지정 요청의 응답에 model=None"""
        agent = _make_agent()
        _resolve_llm(agent, extra={"model": None})

        result = await agent.request_llm(
            messages=[{"role": "user", "content": "질문"}],
        )

        assert result.model is None

    async def test_invalid_model_raises_before_sending(self) -> None:
        """TC-V06: 유효하지 않은 model로 request_llm 호출 시 ValidationError — 서버 전송 전 차단"""
        agent = _make_agent()

        with pytest.raises(ValidationError):
            await agent.request_llm(
                messages=[{"role": "user", "content": "질문"}],
                model="invalid model!",
            )

        # 검증 실패 → 서버로 전송되지 않아야 함
        agent.client.send_message.assert_not_awaited()

    async def test_invalid_max_tokens_raises_before_sending(self) -> None:
        """TC-V07: max_tokens 범위 초과 시 ValidationError — 서버 전송 전 차단"""
        agent = _make_agent()

        with pytest.raises(ValidationError):
            await agent.request_llm(
                messages=[{"role": "user", "content": "질문"}],
                max_tokens=9999,
            )

        agent.client.send_message.assert_not_awaited()

    async def test_invalid_role_in_request_raises_before_sending(self) -> None:
        """TC-V08: 잘못된 role 포함 시 ValidationError — 서버 전송 전 차단"""
        agent = _make_agent()

        with pytest.raises(ValidationError):
            await agent.request_llm(
                messages=[{"role": "bad_role", "content": "질문"}],
            )

        agent.client.send_message.assert_not_awaited()
