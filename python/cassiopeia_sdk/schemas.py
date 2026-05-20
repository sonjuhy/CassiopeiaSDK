import re
from typing import TypedDict, Literal, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ---------------------------------------------------------------------------
# 오케스트라로 결과 반환 시 (TypedDict 유지)
# ---------------------------------------------------------------------------

class AgentResult(TypedDict):
    task_id: str
    agent: str
    status: Literal["COMPLETED", "FAILED", "PROCESSING"]
    result_data: dict[str, Any]
    error: str | None
    usage_stats: dict[str, Any]


# 카시오페아에서 수신하는 태스크 (TypedDict 유지)
class CassiopeiaTask(TypedDict):
    task_id: str
    session_id: str
    requester: dict  # {user_id, channel_id}
    content: str
    source: str  # "slack" | "api" | ...
    action: str
    params: dict[str, Any]


# ---------------------------------------------------------------------------
# LLM 게이트웨이 — Pydantic BaseModel (런타임 검증 포함)
# ---------------------------------------------------------------------------

# model 필드 허용 패턴: 영문자·숫자·점·하이픈, 1~100자
_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9.\-]+$")

# 허용 role 집합
_ALLOWED_ROLES: frozenset[str] = frozenset({"user", "assistant", "system"})


class LLMRequest(BaseModel):
    """
    LLM 게이트웨이 요청 모델.

    Fields:
        task_id:     요청 추적용 ID
        agent_id:    등록된 에이전트 ID
        messages:    role/content 메시지 배열 (role: user | assistant | system)
        max_tokens:  생성 최대 토큰 수 (1~2000, 기본 500)
        temperature: 샘플링 온도 (0.0~1.0, 기본 0.7)
        model:       모델 오버라이드 (None이면 서버 기본 모델 사용)
    """

    task_id: str
    agent_id: str
    messages: list[dict]
    max_tokens: int = Field(default=500, ge=1, le=2000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    model: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        """model은 영문자·숫자·점·하이픈으로 구성된 1~100자 문자열이어야 합니다."""
        if v is not None and not _MODEL_PATTERN.match(v):
            raise ValueError(
                "model은 영문자·숫자·점·하이픈으로 구성된 1~100자 문자열이어야 합니다"
            )
        return v

    @field_validator("messages")
    @classmethod
    def validate_message_roles(cls, v: list[dict]) -> list[dict]:
        """messages의 각 role은 user | assistant | system 중 하나여야 합니다."""
        for msg in v:
            role = msg.get("role")
            if role not in _ALLOWED_ROLES:
                raise ValueError(
                    f"messages의 role은 {sorted(_ALLOWED_ROLES)} 중 하나여야 합니다. "
                    f"받은 값: {role!r}"
                )
        return v


class LLMResponse(BaseModel):
    """
    LLM 게이트웨이 응답 모델.

    Fields:
        task_id:     요청 추적용 ID
        status:      처리 상태
        content:     생성된 텍스트
        usage:       토큰 사용량 {prompt_tokens, completion_tokens, total_tokens}
        error:       에러 메시지 (정상 응답 시 None)
        retry_after: rate_limited 시 재시도 대기 시간(초)
        model:       실제 사용된 모델명 (미지정 요청이면 None)
    """

    model_config = ConfigDict(extra="allow")  # 서버 추가 필드 허용

    task_id: str
    status: Literal["completed", "rate_limited", "unauthorized", "error"]
    content: str = ""
    usage: dict = Field(default_factory=dict)
    error: str | None = None
    retry_after: int | None = None
    model: str | None = None
