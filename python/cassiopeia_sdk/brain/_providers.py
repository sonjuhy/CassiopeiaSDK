"""LLM Provider 추상화 — GatewayProvider / DirectProvider / LLMProviderFactory."""
from __future__ import annotations

import os
from typing import Any

from cassiopeia_sdk.schemas import LLMResponse

from ._models import BackendType, LLMCallerType


# ---------------------------------------------------------------------------
# GatewayProvider
# ---------------------------------------------------------------------------

class GatewayProvider:
    """
    AgentBase.request_llm을 주입받아 카시오페아 LLM 게이트웨이를 통해 호출합니다.

    Future 대기(펜딩 LLM 응답 매핑) 메커니즘은 AgentBase에 구현되어 있습니다.
    CassiopeiaClient만으로는 이 메커니즘을 재현할 수 없으므로,
    AgentBase.request_llm 메서드를 callable로 직접 주입받아 위임합니다.

    Usage:
        brain = AgentBrain(
            backend="gateway",
            llm_caller=self.request_llm,  # AgentBase 메서드 직접 주입
            ...
        )
    """

    def __init__(self, caller: LLMCallerType) -> None:
        self.caller = caller

    async def call(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """AgentBase.request_llm으로 LLM을 호출하고 LLMResponse를 반환합니다."""
        return await self.caller(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# ---------------------------------------------------------------------------
# DirectProvider
# ---------------------------------------------------------------------------

class DirectProvider:
    """
    외부 LLM API를 직접 호출합니다. (3rd-party 독립 에이전트용)

    API 키는 에이전트 범위 환경변수를 통해 격리 로드합니다.
    환경변수 명명 규칙: {AGENT_NAME}_{PROVIDER}_API_KEY
    예: ARCHIVE_AGENT_GEMINI_API_KEY, RESEARCH_AGENT_ANTHROPIC_API_KEY

    ⚠️ v0.3.0에서는 GatewayProvider가 최우선 지원됩니다.
       DirectProvider는 인터페이스만 정의되어 있으며,
       실제 API 호출 구현은 각 provider별 확장 패키지에서 추가됩니다.
    """

    _PROVIDER_ENV_MAP: dict[str, str] = {
        "gemini": "GEMINI",
        "claude": "ANTHROPIC",
        "local": "LOCAL",
    }

    def __init__(self, backend: BackendType, agent_name: str) -> None:
        if backend == "gateway":
            raise ValueError(
                "DirectProvider는 gateway 백엔드를 지원하지 않습니다. "
                "GatewayProvider를 사용하세요."
            )
        self.backend = backend
        self.agent_name = agent_name.upper()
        self._api_key: str | None = self._load_api_key()

    def _load_api_key(self) -> str | None:
        """에이전트 범위 환경변수에서 API 키를 로드합니다."""
        provider_key = self._PROVIDER_ENV_MAP.get(self.backend, self.backend.upper())
        env_var = f"{self.agent_name}_{provider_key}_API_KEY"
        return os.environ.get(env_var)

    async def call(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        외부 LLM API를 직접 호출합니다.

        Raises:
            NotImplementedError: v0.3.0에서는 아직 구현되지 않음.
        """
        raise NotImplementedError(
            f"DirectProvider({self.backend!r})는 v0.3.0에서 아직 구현되지 않았습니다. "
            f"GatewayProvider를 사용하거나 해당 provider 구현체를 추가하세요."
        )


# ---------------------------------------------------------------------------
# LLMProviderFactory
# ---------------------------------------------------------------------------

class LLMProviderFactory:
    """BackendType에 따라 적절한 Provider 인스턴스를 생성합니다."""

    @staticmethod
    def create(backend: BackendType, agent_name: str) -> DirectProvider:
        """
        gateway 외의 백엔드에 대한 DirectProvider를 생성합니다.

        Args:
            backend:    "gemini" | "claude" | "local"
            agent_name: 에이전트 식별 이름 (환경변수 키 생성에 사용)
        """
        return DirectProvider(backend=backend, agent_name=agent_name)
