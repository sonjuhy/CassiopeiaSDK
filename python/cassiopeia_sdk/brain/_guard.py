"""프롬프트 인젝션 방어 — 정규식 블랙리스트 기반 1차 방어."""
from __future__ import annotations

import re
from typing import Literal

from ._exceptions import PromptInjectionError

# ---------------------------------------------------------------------------
# 인젝션 탐지 패턴 목록
# ---------------------------------------------------------------------------
# 각 패턴은 독립적으로 탐지; 하나라도 매치되면 인젝션으로 판단.

_PATTERNS: list[re.Pattern[str]] = [
    # 시스템 프롬프트 구조 탈출
    re.compile(r"</?(?:system|prompt|instruction)\b", re.IGNORECASE),
    re.compile(r"<\|im_(?:start|end)\|>", re.IGNORECASE),
    re.compile(r"\[(?:현재|이전|지금).*?(?:요청|지시|명령).*?(?:종료|무시|끝)\]", re.IGNORECASE | re.DOTALL),

    # 역할 전환 시도
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\b", re.IGNORECASE),
    re.compile(r"새로운\s*(?:역할|지시|명령|시스템\s*프롬프트)"),

    # 이전 지시 무력화
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"(?:forget|disregard)\s+(?:all\s+)?(?:previous|prior|your)(?:\s+previous)?\s+(?:instructions?|prompt)", re.IGNORECASE),
    re.compile(r"(?:이전|모든)\s*(?:지시|명령|프롬프트)\s*(?:무시|잊어|ignore)", re.IGNORECASE),

    # 마크다운 헤더 인젝션
    re.compile(r"^#{1,6}\s+(?:new\s+instruction|system\s+prompt|override|jailbreak)", re.IGNORECASE | re.MULTILINE),

    # 알려진 탈옥 키워드
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bDAN\s*(?:mode|prompt)\b", re.IGNORECASE),
]


def _detect(text: str) -> re.Pattern[str] | None:
    """탐지된 패턴을 반환. 탐지 없으면 None."""
    for pattern in _PATTERNS:
        if pattern.search(text):
            return pattern
    return None


# ---------------------------------------------------------------------------
# PromptInjectionGuard
# ---------------------------------------------------------------------------

class PromptInjectionGuard:
    """
    1차 방어: 정규식 블랙리스트 기반 프롬프트 인젝션 탐지.

    검사 대상:
    - user_request (현재 사용자 입력)
    - history 내 role="user" 메시지의 content만
      ※ role="assistant" 메시지는 SDK 자신이 생성한 텍스트이므로 제외.
        (포함 시 이전 응답에 인젝션 패턴이 포함된 경우 false positive 발생)
    - capabilities 문자열 (에이전트 초기화 시 check_static으로 1회 검사)

    ⚠️ 블랙리스트 방식의 한계:
    인코딩 변형(유니코드·Base64·공백 삽입 등)으로 우회될 수 있습니다.
    고위험 에이전트에는 AgentBrainConfig.enable_llm_secondary_guard=True 설정 권장.
    """

    def __init__(
        self,
        enabled: bool = True,
        policy: Literal["raise", "fallback"] = "fallback",
    ) -> None:
        self.enabled = enabled
        self.policy = policy

    def check(
        self,
        user_request: str,
        history: list[dict[str, str]] | None = None,
    ) -> None:
        """
        user_request와 history 내 role="user" 메시지를 검사합니다.

        enabled=False이면 즉시 반환 (검사 생략).
        탐지 시 PromptInjectionError 발생.
        (policy 분기는 AgentBrain.analyze_task에서 처리)
        """
        if not self.enabled:
            return

        matched = _detect(user_request)
        if matched:
            raise PromptInjectionError(
                f"[user_request] 프롬프트 인젝션이 탐지되었습니다: {matched.pattern!r}"
            )

        if history:
            for i, msg in enumerate(history):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    matched = _detect(content)
                    if matched:
                        raise PromptInjectionError(
                            f"[history[{i}]] 프롬프트 인젝션이 탐지되었습니다: {matched.pattern!r}"
                        )

    def check_static(self, text: str, label: str = "input") -> None:
        """
        초기화 시점 정적 검사용 (capabilities 등 개발자 입력 검증).

        AgentBrainConfig.enable_injection_guard 값과 무관하게 항상 실행됩니다.
        탐지 시 항상 ValueError 발생 (injection_guard_policy 무관).
        목적: 개발자 실수로 인한 capabilities 오염 방지.
        """
        matched = _detect(text)
        if matched:
            raise ValueError(
                f"[{label}] 인젝션 패턴이 감지되었습니다: {matched.pattern!r}\n"
                f"capabilities에 시스템 지시 패턴이 포함되어 있는지 확인해주세요."
            )
