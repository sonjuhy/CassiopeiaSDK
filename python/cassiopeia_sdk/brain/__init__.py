"""
cassiopeia_sdk.brain — NLU 의도 분석 모듈

AgentBrain을 통해 자연어 요청을 분석하고, 적절한 Tool과 파라미터를 결정합니다.

Usage:
    from cassiopeia_sdk.brain import AgentBrain, AgentBrainConfig, BrainDecision

    class MyAgent(AgentBase):
        def __init__(self, ...):
            super().__init__(...)
            self.brain = AgentBrain(
                agent_name="my_agent",
                capabilities="노션 및 옵시디언 데이터 관리",
                backend="gateway",
                llm_caller=self.request_llm,
                config=AgentBrainConfig(
                    rate_limit_per_minute=60,
                    output_escape_policy="markdown",
                ),
            )

        async def handle(self, msg):
            decision: BrainDecision = await self.brain.analyze_task(
                user_request=msg.payload["content"],
                tools=self.executor.get_registered_tools(),
                history=msg.payload.get("context"),
            )
            if decision.action == "ask_clarification":
                return self.reply(decision.suggested_reply or "좀 더 구체적으로 말씀해주세요.")
            return await self.executor.execute(decision.action, decision.params)
"""
from ._exceptions import (
    PromptInjectionError,
    UnknownActionError,
    ParamsValidationError,
    RateLimitExceededError,
)
from ._models import (
    BackendType,
    OutputEscapePolicy,
    RateLimitBackend,
    LLMCallerType,
    BrainDecision,
    AgentBrainConfig,
)
from ._guard import PromptInjectionGuard
from ._validator import ActionAndParamsValidator
from ._sanitizer import OutputSanitizer
from ._rate_limiter import RateLimiter
from ._providers import GatewayProvider, DirectProvider, LLMProviderFactory
from ._brain import AgentBrain

__all__ = [
    # 예외
    "PromptInjectionError",
    "UnknownActionError",
    "ParamsValidationError",
    "RateLimitExceededError",
    # 모델 / 타입
    "BackendType",
    "OutputEscapePolicy",
    "RateLimitBackend",
    "LLMCallerType",
    "BrainDecision",
    "AgentBrainConfig",
    # 보안 컴포넌트
    "PromptInjectionGuard",
    "ActionAndParamsValidator",
    "OutputSanitizer",
    "RateLimiter",
    # Provider
    "GatewayProvider",
    "DirectProvider",
    "LLMProviderFactory",
    # 메인
    "AgentBrain",
]
