"""분당 호출 횟수 제한 — memory / redis 백엔드 지원."""
from __future__ import annotations

import time
from collections import deque

from ._exceptions import RateLimitExceededError
from ._models import RateLimitBackend


class RateLimiter:
    """
    에이전트 인스턴스 단위(per-agent-instance) 분당 호출 횟수를 제한합니다.

    Backends:
        "memory": 단일 프로세스 환경. 슬라이딩 윈도우(60초) 방식.
                  ⚠️ scale-out 환경에서는 인스턴스별 독립 카운터로 실제 제한이 n배 증가.
        "redis" : 분산 환경. Redis INCR + TTL 방식. BRAIN_RATE_LIMIT_REDIS_URL 환경변수 필요.
    """

    def __init__(
        self,
        limit: int | None,
        backend: RateLimitBackend = "memory",
        redis_url: str | None = None,
        agent_name: str = "default",
    ) -> None:
        self.limit = limit
        self.backend = backend
        self._redis_url = redis_url
        self._agent_name = agent_name
        # memory 백엔드용 슬라이딩 윈도우 (호출 타임스탬프 저장)
        self._window: deque[float] = deque()

    async def check_async(self) -> None:
        """
        비동기 호출 횟수 확인. 제한 초과 시 RateLimitExceededError 발생.
        limit=None이면 즉시 반환 (제한 없음).
        """
        if self.limit is None:
            return
        if self.backend == "memory":
            self._check_memory()
        elif self.backend == "redis":
            await self._check_redis_async()

    def _check_memory(self) -> None:
        """슬라이딩 윈도우(60초) 방식으로 메모리 기반 Rate Limit 검사."""
        now = time.monotonic()
        window_start = now - 60.0

        # 윈도우 밖의 오래된 타임스탬프 제거
        while self._window and self._window[0] < window_start:
            self._window.popleft()

        if len(self._window) >= self.limit:
            raise RateLimitExceededError(
                f"분당 호출 횟수 제한({self.limit}회/분)을 초과했습니다. "
                f"잠시 후 다시 시도해주세요."
            )
        self._window.append(now)

    async def _check_redis_async(self) -> None:
        """Redis INCR + TTL 방식으로 분산 환경 Rate Limit 검사."""
        import os
        try:
            import redis.asyncio as aioredis
        except ImportError as e:
            raise ImportError(
                "Redis 백엔드를 사용하려면 redis 패키지가 필요합니다: "
                "pip install cassiopeia-sdk[brain]"
            ) from e

        url = self._redis_url or os.environ.get("BRAIN_RATE_LIMIT_REDIS_URL")
        if not url:
            raise ValueError(
                "Redis URL이 필요합니다. "
                "BRAIN_RATE_LIMIT_REDIS_URL 환경변수를 설정하거나 "
                "RateLimiter(redis_url=...) 파라미터를 전달하세요."
            )

        client = aioredis.from_url(url, decode_responses=True)
        # 에이전트 인스턴스별 키 분리 — 같은 Redis를 공유하는 다른 에이전트와 카운터 격리
        key = f"cassiopeia:brain:rate_limit:{self._agent_name}"
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = await pipe.execute()
            current_count: int = results[0]
            current_ttl: int = results[1]

            # 키가 새로 생성된 경우(TTL=-1)에만 60초 만료 설정
            # 매 호출마다 TTL을 리셋하지 않아야 고정 창 의미가 보존됨
            if current_ttl == -1:
                await client.expire(key, 60)

            if current_count > self.limit:
                raise RateLimitExceededError(
                    f"분당 호출 횟수 제한({self.limit}회/분)을 초과했습니다. "
                    f"잠시 후 다시 시도해주세요."
                )
        finally:
            await client.aclose()
