"""action 유효성 검증 + Tool 스키마 기반 파라미터 검증."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from cassiopeia_sdk.tools import Tool

from ._exceptions import UnknownActionError, ParamsValidationError

# JSON Schema type → Python type 매핑
_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


class ActionAndParamsValidator:
    """
    LLM이 생성한 BrainDecision.action과 params를 tools 목록 기준으로 검증합니다.
    executor.execute() 호출 전 반드시 수행하여 미등록 action 실행 및 2차 공격을 차단합니다.

    검증 순서:
    1. action이 tools 목록에 존재하는 이름인지 확인 (UnknownActionError)
    2. 해당 Tool의 parameters 스키마로 params 검증:
       - 필수 파라미터 존재 여부
       - 각 파라미터의 타입 일치 여부
       - 허용된 키 외의 추가 키 포함 여부 (extra 필드 차단)
    """

    @staticmethod
    def validate(
        action: str,
        params: dict[str, Any],
        tools: Sequence[Tool | dict[str, Any]],
    ) -> tuple[Tool, dict[str, Any]]:
        """
        검증된 (Tool 객체, params)를 반환합니다.

        tools 목록에서 action과 일치하는 Tool을 탐색한 후 params를 검증합니다.

        Raises:
            UnknownActionError:    action이 tools 목록에 없을 때
            ParamsValidationError: 파라미터 누락·타입 불일치·허용되지 않은 키
        """
        tool = _find_tool(action, tools)
        validated_params = _validate_params(action, params, tool.parameters)
        return tool, validated_params


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _find_tool(action: str, tools: Sequence[Tool | dict[str, Any]]) -> Tool:
    """tools 목록에서 action 이름과 일치하는 Tool을 반환. 없으면 UnknownActionError."""
    tool_names: list[str] = []
    for t in tools:
        if isinstance(t, dict):
            t = Tool(**t)
        tool_names.append(t.name)
        if t.name == action:
            return t
    raise UnknownActionError(
        f"등록되지 않은 action: {action!r}. "
        f"사용 가능한 action 목록: {tool_names}"
    )


def _validate_params(
    action: str,
    params: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    JSON Schema(tool.parameters) 기준으로 params를 검증합니다.
    검증 통과 시 (필요하다면 타입 정규화된) params를 반환합니다.
    """
    properties: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    # 1. 필수 파라미터 누락 검사
    missing = [k for k in required if k not in params]
    if missing:
        raise ParamsValidationError(
            f"[{action}] 필수 파라미터 누락: {missing}"
        )

    # 2. 허용되지 않은 추가 키 검사 (properties가 정의된 경우)
    if properties:
        extra_keys = [k for k in params if k not in properties]
        if extra_keys:
            raise ParamsValidationError(
                f"[{action}] 허용되지 않은 파라미터 키: {extra_keys}"
            )

    # 3. 타입 검사 및 정규화
    normalized = dict(params)
    for key, value in params.items():
        if key not in properties:
            continue
        prop_schema = properties[key]
        expected_type_str: str | None = prop_schema.get("type")
        if not expected_type_str or expected_type_str not in _TYPE_MAP:
            continue

        expected_type = _TYPE_MAP[expected_type_str]
        if isinstance(value, expected_type):
            continue

        # 특수 케이스: integer 스키마에 float 정수값 허용 (예: 1.0 → 1)
        if expected_type_str == "integer" and isinstance(value, float) and value.is_integer():
            normalized[key] = int(value)
            continue

        raise ParamsValidationError(
            f"[{action}] 파라미터 타입 불일치: {key!r} "
            f"(기대: {expected_type_str}, 실제: {type(value).__name__!r})"
        )

    return normalized
