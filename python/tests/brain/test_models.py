"""BrainDecision / AgentBrainConfig Pydantic 모델 단위 테스트."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from cassiopeia_sdk.brain import AgentBrainConfig, BrainDecision


class TestBrainDecision:

    def test_confidence_default_is_zero(self):
        """최소 신뢰 원칙: confidence 기본값은 0.0."""
        d = BrainDecision(action="do_thing", params={})
        assert d.confidence == 0.0

    def test_confidence_accepted_in_range(self):
        d = BrainDecision(action="x", params={}, confidence=0.85)
        assert d.confidence == 0.85

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            BrainDecision(action="x", params={}, confidence=-0.1)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            BrainDecision(action="x", params={}, confidence=1.1)

    def test_optional_fields_default_none(self):
        d = BrainDecision(action="x", params={})
        assert d.reasoning is None
        assert d.suggested_reply is None

    def test_model_copy_with_update(self):
        """model_copy(update=...) 로 새 인스턴스가 올바르게 생성됨."""
        d = BrainDecision(action="x", params={}, reasoning="original")
        d2 = d.model_copy(update={"reasoning": "updated"})
        assert d2.reasoning == "updated"
        assert d.reasoning == "original"  # 원본 불변


class TestAgentBrainConfig:

    def test_defaults(self):
        cfg = AgentBrainConfig()
        assert cfg.max_retries == 2
        assert cfg.confidence_threshold == 0.7
        assert cfg.enable_injection_guard is True
        assert cfg.injection_guard_policy == "fallback"
        assert cfg.enable_llm_secondary_guard is False
        assert cfg.rate_limit_per_minute is None
        assert cfg.rate_limit_backend == "memory"
        assert cfg.output_escape_policy == "markdown"

    def test_custom_values(self):
        cfg = AgentBrainConfig(
            max_retries=0,
            confidence_threshold=0.9,
            enable_injection_guard=False,
            injection_guard_policy="raise",
            enable_llm_secondary_guard=True,
            rate_limit_per_minute=30,
            rate_limit_backend="redis",
            output_escape_policy="html",
        )
        assert cfg.max_retries == 0
        assert cfg.confidence_threshold == 0.9
        assert cfg.enable_injection_guard is False
        assert cfg.injection_guard_policy == "raise"
        assert cfg.enable_llm_secondary_guard is True
        assert cfg.rate_limit_per_minute == 30
        assert cfg.rate_limit_backend == "redis"
        assert cfg.output_escape_policy == "html"

    def test_invalid_injection_guard_policy_raises(self):
        with pytest.raises(ValidationError):
            AgentBrainConfig(injection_guard_policy="unknown")  # type: ignore

    def test_invalid_output_escape_policy_raises(self):
        with pytest.raises(ValidationError):
            AgentBrainConfig(output_escape_policy="xml")  # type: ignore
