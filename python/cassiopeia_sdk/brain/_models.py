"""brain 모듈 Pydantic 모델 및 타입 별칭 정의."""
from __future__ import annotations

from collections.abc import Callable, Awaitable
from typing import Any, Literal

from pydantic import BaseModel, Field

from cassiopeia_sdk.schemas import LLMResponse

# ---------------------------------------------------------------------------
# 타입 별칭
# ---------------------------------------------------------------------------

BackendType = Literal["gateway", "gemini", "claude", "local"]
OutputEscapePolicy = Literal["none", "markdown", "html"]
RateLimitBackend = Literal["memory", "redis"]

# GatewayProvider에 주입되는 llm_caller의 타입 별칭
LLMCallerType = Callable[..., Awaitable[LLMResponse]]


# ---------------------------------------------------------------------------
# BrainDecision — analyze_task 반환 타입
# ---------------------------------------------------------------------------

class BrainDecision(BaseModel):
    """
    AgentBrain.analyze_task()의 반환 모델.

    Fields:
        action:         실행할 도구 이름.
                        신뢰도 미달·인젝션 탐지 시 'ask_clarification'.
        params:         Tool 스키마 검증 완료된 파라미터 (ActionAndParamsValidator 통과).
        reasoning:      LLM이 해당 결정을 내린 이유.
                        OutputSanitizer에 의해 output_escape_policy 기준 이스케이핑 적용됨.
        confidence:     LLM의 결정 신뢰도 (0.0~1.0).
                        기본값 0.0 (최소 신뢰 원칙) — LLM 미반환 시 자동으로
                        confidence_threshold 미달로 처리되어 ask_clarification 유도.
        suggested_reply: ask_clarification 시 사용자에게 전달할 텍스트.
                         SDK가 confidence 미달 탐지 시 LLM reasoning 기반으로 자동 생성.
                         OutputSanitizer 이스케이핑 적용됨. None이면 에이전트 폴백 문구 처리.
    """

    action: str
    params: dict[str, Any]
    reasoning: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggested_reply: str | None = None


# ---------------------------------------------------------------------------
# AgentBrainConfig — 정책 설정
# ---------------------------------------------------------------------------

class AgentBrainConfig(BaseModel):
    """
    AgentBrain 동작 정책 설정 모델.

    모든 필드에 안전한 기본값이 설정되어 있으므로,
    필요한 필드만 선택적으로 오버라이드할 수 있습니다.
    """

    max_retries: int = 2
    """
    JSON 파싱 실패, UnknownActionError, ParamsValidationError 발생 시 최대 재시도 횟수.
    각 재시도는 지수 백오프(1s → 2s → 4s ...) 적용.
    재시도 시 이전 오류 내용을 프롬프트에 포함하여 LLM 자기 수정 유도.
    ※ 재시도 LLM 호출은 rate_limit_per_minute 카운트에 포함되지 않음.
    """

    confidence_threshold: float = 0.7
    """
    이 수치 미만이면 SDK가 action="ask_clarification" 결정을 반환.
    BrainDecision.confidence 기본값이 0.0이므로,
    LLM이 confidence를 반환하지 않으면 항상 이 조건에 걸림.
    """

    enable_injection_guard: bool = True
    """
    False로 설정 시 PromptInjectionGuard.check() 호출을 비활성화.
    ⚠️ check_static()은 이 값과 무관하게 항상 실행됨.
    프로덕션 환경에서는 반드시 True 유지.
    """

    injection_guard_policy: Literal["raise", "fallback"] = "fallback"
    """
    "raise"   : 인젝션 탐지 시 PromptInjectionError 예외 발생.
    "fallback": 인젝션 탐지 시 confidence=0 + action="ask_clarification" 으로 강제 라우팅.
    """

    enable_llm_secondary_guard: bool = False
    """
    True 설정 시 Step 1 정규식 검사 통과 후, 메인 LLM 호출 전에
    검증 전용 LLM 호출로 인젝션 2차 검증 수행 (입력 단계에서 실행).
    블랙리스트 우회(인코딩·유니코드 변형) 방어에 효과적.
    고위험 에이전트(금융, 개인정보 처리 등) 또는 외부 사용자 입력을 받는 에이전트에 권장.
    활성화 시 LLM 호출 1회 추가 발생 (이 호출은 rate_limit 카운트에 포함됨).
    """

    rate_limit_per_minute: int | None = None
    """
    에이전트 인스턴스 단위 분당 analyze_task 최대 호출 횟수 (per-agent-instance).
    None이면 제한 없음. 외부 사용자 입력을 받는 에이전트는 반드시 설정 권장. (예: 60)
    초과 시 RateLimitExceededError 발생.
    ※ 사용자별(per-user) 제한이 필요한 경우 호출자 레벨에서 별도 처리 필요.
    """

    rate_limit_backend: RateLimitBackend = "memory"
    """
    "memory": 단일 프로세스 환경. 프로세스 재시작 시 카운터 초기화.
              ⚠️ scale-out 환경에서는 인스턴스마다 독립 카운터로 실제 제한이 n배 증가.
    "redis" : 분산 환경. Redis 연결 필요 (BRAIN_RATE_LIMIT_REDIS_URL 환경변수).
              scale-out 시에도 전체 인스턴스 합산 정확한 제한 유지. 권장.
    """

    output_escape_policy: OutputEscapePolicy = "markdown"
    """
    suggested_reply, reasoning 등 LLM 생성 텍스트의 출력 이스케이핑 정책.
    "none"    : 이스케이핑 없음. 신뢰된 내부 채널 전용.
    "markdown": Slack·노션 등 마크다운 채널용 특수문자 이스케이핑.
    "html"    : 웹 UI 출력용 HTML 엔티티 이스케이핑.
    """
