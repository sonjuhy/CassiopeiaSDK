"""RateLimiter 단위 테스트."""
from __future__ import annotations

import asyncio
import time

import pytest

from cassiopeia_sdk.brain import RateLimitExceededError, RateLimiter


class TestNoLimit:

    async def test_no_limit_never_raises(self):
        limiter = RateLimiter(limit=None)
        for _ in range(1000):
            await limiter.check_async()  # 예외 없어야 함


class TestMemoryBackend:

    async def test_under_limit_passes(self):
        limiter = RateLimiter(limit=5, backend="memory")
        for _ in range(5):
            await limiter.check_async()

    async def test_over_limit_raises(self):
        limiter = RateLimiter(limit=3, backend="memory")
        for _ in range(3):
            await limiter.check_async()
        with pytest.raises(RateLimitExceededError):
            await limiter.check_async()

    async def test_error_message_contains_limit(self):
        limiter = RateLimiter(limit=2, backend="memory")
        await limiter.check_async()
        await limiter.check_async()
        with pytest.raises(RateLimitExceededError, match="2"):
            await limiter.check_async()

    async def test_sliding_window_expires_old_entries(self):
        """슬라이딩 윈도우에서 60초 지난 항목은 제거됨."""
        limiter = RateLimiter(limit=2, backend="memory")

        # 60초 이전 타임스탬프를 직접 삽입
        limiter._window.append(time.monotonic() - 61.0)
        limiter._window.append(time.monotonic() - 61.0)

        # 오래된 항목이 제거되므로 2번 더 호출 가능
        await limiter.check_async()
        await limiter.check_async()

    async def test_limit_one_allows_single_call(self):
        limiter = RateLimiter(limit=1, backend="memory")
        await limiter.check_async()
        with pytest.raises(RateLimitExceededError):
            await limiter.check_async()

    async def test_independent_limiters_have_separate_windows(self):
        """서로 다른 RateLimiter 인스턴스는 독립적인 카운터를 가짐."""
        limiter_a = RateLimiter(limit=1, backend="memory")
        limiter_b = RateLimiter(limit=1, backend="memory")

        await limiter_a.check_async()
        with pytest.raises(RateLimitExceededError):
            await limiter_a.check_async()

        # limiter_b는 아직 1회 여유 있음
        await limiter_b.check_async()


class TestRedisBackendUnavailable:

    async def test_redis_backend_raises_value_error_without_url(self):
        """Redis URL 미설정 시 ValueError 발생."""
        import os
        env_backup = os.environ.pop("BRAIN_RATE_LIMIT_REDIS_URL", None)
        try:
            limiter = RateLimiter(limit=10, backend="redis")
            with pytest.raises(ValueError, match="Redis URL"):
                await limiter.check_async()
        finally:
            if env_backup:
                os.environ["BRAIN_RATE_LIMIT_REDIS_URL"] = env_backup
