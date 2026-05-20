"""LLM 생성 텍스트 출력 이스케이핑 — OutputSanitizer."""
from __future__ import annotations

import html as _html_module

from ._models import OutputEscapePolicy

# 마크다운 이스케이핑 대상 문자 집합
# Slack·노션 등 마크다운 렌더러에서 특수 의미를 갖는 문자들
_MARKDOWN_SPECIAL_CHARS = set(r'\`*_{}[]()#+-.!|~>')


def _escape_markdown(text: str) -> str:
    """마크다운 특수문자 앞에 백슬래시를 삽입합니다."""
    result: list[str] = []
    for char in text:
        if char in _MARKDOWN_SPECIAL_CHARS:
            result.append('\\')
        result.append(char)
    return ''.join(result)


class OutputSanitizer:
    """
    LLM이 생성한 텍스트를 출력 채널에 맞게 이스케이핑합니다.

    적용 대상:
    - BrainDecision.suggested_reply  : 사용자에게 직접 전달되는 텍스트
    - BrainDecision.reasoning        : 에이전트가 사용자에게 노출할 수 있는 추론 텍스트
    ※ BrainDecision.params 내부 문자열은 Tool executor가 직접 처리하므로
      OutputSanitizer 적용 범위에서 제외. (ActionAndParamsValidator로 구조 검증 완료)
    """

    @staticmethod
    def sanitize(text: str, policy: OutputEscapePolicy) -> str:
        """
        policy에 따라 이스케이핑된 텍스트를 반환합니다.

        Args:
            text:   이스케이핑할 텍스트
            policy: 이스케이핑 정책
                    - "none"    : 원본 반환 (내부 채널 전용)
                    - "markdown": *, _, `, [, ] 등 마크다운 특수문자 이스케이핑
                    - "html"    : <, >, &, ", ' HTML 엔티티 변환
        """
        if policy == "none":
            return text
        if policy == "markdown":
            return _escape_markdown(text)
        if policy == "html":
            return _html_module.escape(text, quote=True)
        # 알 수 없는 policy는 원본 반환 (방어적 처리)
        return text
