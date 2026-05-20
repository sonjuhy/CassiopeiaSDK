'use strict';

const { RateLimitExceededError } = require('./exceptions');

/**
 * 에이전트 인스턴스 단위(per-agent-instance) 분당 호출 횟수를 제한합니다.
 *
 * Backends:
 *   "memory": 단일 프로세스 환경. 슬라이딩 윈도우(60초) 방식.
 *             ⚠️ scale-out 환경에서는 인스턴스별 독립 카운터로 실제 제한이 n배 증가.
 *   "redis" : 분산 환경. BRAIN_RATE_LIMIT_REDIS_URL 환경변수 필요.
 */
class RateLimiter {
  /**
   * @param {number|null} limit          - 분당 최대 호출 횟수. null이면 제한 없음
   * @param {'memory'|'redis'} [backend]
   * @param {string|null} [redisUrl]
   */
  constructor(limit, backend = 'memory', redisUrl = null) {
    this.limit = limit;
    this.backend = backend;
    this._redisUrl = redisUrl;
    /** @type {number[]} memory 백엔드용 슬라이딩 윈도우 (타임스탬프 ms) */
    this._window = [];
  }

  /** 호출 횟수 확인. 제한 초과 시 RateLimitExceededError 발생. */
  async check() {
    if (this.limit === null || this.limit === undefined) return;
    if (this.backend === 'memory') {
      this._checkMemory();
    } else if (this.backend === 'redis') {
      await this._checkRedis();
    }
  }

  _checkMemory() {
    const now = Date.now();
    const windowStart = now - 60_000; // 60초

    // 만료된 타임스탬프 제거
    this._window = this._window.filter((t) => t >= windowStart);

    if (this._window.length >= this.limit) {
      throw new RateLimitExceededError(
        `분당 호출 횟수 제한(${this.limit}회/분)을 초과했습니다. 잠시 후 다시 시도해주세요.`
      );
    }
    this._window.push(now);
  }

  async _checkRedis() {
    const url = this._redisUrl || process.env.BRAIN_RATE_LIMIT_REDIS_URL;
    if (!url) {
      throw new Error(
        'Redis URL이 필요합니다. ' +
        'BRAIN_RATE_LIMIT_REDIS_URL 환경변수를 설정하거나 ' +
        'RateLimiter({ redisUrl: ... }) 파라미터를 전달하세요.'
      );
    }

    let Redis;
    try {
      Redis = require('ioredis');
    } catch {
      throw new Error('Redis 백엔드를 사용하려면 ioredis 패키지가 필요합니다: npm install ioredis');
    }

    const client = new Redis(url);
    const key = 'cassiopeia:brain:rate_limit';
    try {
      const pipeline = client.pipeline();
      pipeline.incr(key);
      pipeline.expire(key, 60);
      const results = await pipeline.exec();
      const count = results[0][1]; // [error, value]
      if (count > this.limit) {
        throw new RateLimitExceededError(
          `분당 호출 횟수 제한(${this.limit}회/분)을 초과했습니다. 잠시 후 다시 시도해주세요.`
        );
      }
    } finally {
      await client.quit();
    }
  }
}

module.exports = { RateLimiter };
