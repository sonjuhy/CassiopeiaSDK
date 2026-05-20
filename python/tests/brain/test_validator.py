"""ActionAndParamsValidator 단위 테스트."""
from __future__ import annotations

import pytest

from cassiopeia_sdk.brain import (
    ActionAndParamsValidator,
    ParamsValidationError,
    UnknownActionError,
)
from cassiopeia_sdk.tools import Tool

# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

SEARCH_TOOL = Tool(
    name="search_file",
    description="파일 검색",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "검색어"},
            "limit": {"type": "integer", "description": "최대 결과 수"},
        },
        "required": ["query"],
    },
)

SEND_TOOL = Tool(
    name="send_message",
    description="메시지 전송",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "body": {"type": "string"},
            "urgent": {"type": "boolean"},
        },
        "required": ["to", "body"],
    },
)

ALL_TOOLS = [SEARCH_TOOL, SEND_TOOL]


# ---------------------------------------------------------------------------
# action 유효성 검사
# ---------------------------------------------------------------------------

class TestActionValidation:

    def test_valid_action_returns_tool(self):
        tool, _ = ActionAndParamsValidator.validate(
            "search_file", {"query": "보고서"}, ALL_TOOLS
        )
        assert tool.name == "search_file"

    def test_unknown_action_raises(self):
        with pytest.raises(UnknownActionError, match="do_magic"):
            ActionAndParamsValidator.validate("do_magic", {}, ALL_TOOLS)

    def test_error_message_lists_available_actions(self):
        with pytest.raises(UnknownActionError) as exc:
            ActionAndParamsValidator.validate("unknown", {}, ALL_TOOLS)
        assert "search_file" in str(exc.value)
        assert "send_message" in str(exc.value)

    def test_accepts_dict_tools(self):
        """Tool 객체 대신 dict 형태도 허용."""
        dict_tools = [t.model_dump() for t in ALL_TOOLS]
        tool, _ = ActionAndParamsValidator.validate(
            "send_message", {"to": "bob", "body": "hi"}, dict_tools
        )
        assert tool.name == "send_message"

    def test_empty_tools_raises_unknown_action(self):
        with pytest.raises(UnknownActionError):
            ActionAndParamsValidator.validate("any", {}, [])


# ---------------------------------------------------------------------------
# 파라미터 검증
# ---------------------------------------------------------------------------

class TestParamsValidation:

    def test_valid_params_returns_normalized(self):
        _, params = ActionAndParamsValidator.validate(
            "search_file", {"query": "test"}, ALL_TOOLS
        )
        assert params["query"] == "test"

    def test_missing_required_param_raises(self):
        with pytest.raises(ParamsValidationError, match="query"):
            ActionAndParamsValidator.validate("search_file", {}, ALL_TOOLS)

    def test_extra_key_raises(self):
        with pytest.raises(ParamsValidationError, match="허용되지 않은"):
            ActionAndParamsValidator.validate(
                "search_file",
                {"query": "test", "evil_param": "hack"},
                ALL_TOOLS,
            )

    def test_wrong_type_raises(self):
        with pytest.raises(ParamsValidationError, match="타입 불일치"):
            ActionAndParamsValidator.validate(
                "search_file",
                {"query": 12345},  # string이어야 하는데 int
                ALL_TOOLS,
            )

    def test_integer_from_float_is_normalized(self):
        """1.0 같은 float 정수는 integer 타입으로 정규화."""
        _, params = ActionAndParamsValidator.validate(
            "search_file",
            {"query": "test", "limit": 5.0},
            ALL_TOOLS,
        )
        assert params["limit"] == 5
        assert isinstance(params["limit"], int)

    def test_optional_param_can_be_omitted(self):
        """required에 없는 파라미터는 생략 가능."""
        _, params = ActionAndParamsValidator.validate(
            "search_file",
            {"query": "test"},  # limit 생략
            ALL_TOOLS,
        )
        assert "query" in params
        assert "limit" not in params

    def test_all_required_params_present_passes(self):
        _, params = ActionAndParamsValidator.validate(
            "send_message",
            {"to": "alice", "body": "hello"},
            ALL_TOOLS,
        )
        assert params["to"] == "alice"
        assert params["body"] == "hello"

    def test_boolean_type_accepted(self):
        _, params = ActionAndParamsValidator.validate(
            "send_message",
            {"to": "alice", "body": "hi", "urgent": True},
            ALL_TOOLS,
        )
        assert params["urgent"] is True

    def test_error_message_contains_action_name(self):
        with pytest.raises(ParamsValidationError, match="search_file"):
            ActionAndParamsValidator.validate("search_file", {}, ALL_TOOLS)

    def test_tool_with_no_properties_accepts_empty_params(self):
        """parameters에 properties가 없는 Tool은 빈 params 허용."""
        empty_tool = Tool(
            name="ping",
            description="연결 확인",
            parameters={"type": "object"},
        )
        _, params = ActionAndParamsValidator.validate("ping", {}, [empty_tool])
        assert params == {}
