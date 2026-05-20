"""brain 모듈 전용 예외 클래스."""
from __future__ import annotations


class PromptInjectionError(Exception):
    """프롬프트 인젝션 패턴이 탐지되었을 때 발생합니다."""


class UnknownActionError(Exception):
    """LLM이 tools에 등록되지 않은 action을 반환했을 때 발생합니다."""


class ParamsValidationError(Exception):
    """LLM이 반환한 params가 Tool 스키마와 일치하지 않을 때 발생합니다."""


class RateLimitExceededError(Exception):
    """분당 analyze_task 호출 횟수가 설정 제한을 초과했을 때 발생합니다."""
