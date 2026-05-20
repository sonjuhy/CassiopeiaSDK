'use strict';

const { RateLimiter } = require('../../src/brain/rateLimiter');
const { RateLimitExceededError } = require('../../src/brain/exceptions');

describe('RateLimiter — no limit', () => {
  it('limit=null이면 항상 통과', async () => {
    const limiter = new RateLimiter(null);
    for (let i = 0; i < 100; i++) await limiter.check();
  });
});

describe('RateLimiter — memory backend', () => {

  it('제한 이하 통과', async () => {
    const limiter = new RateLimiter(5, 'memory');
    for (let i = 0; i < 5; i++) await limiter.check();
  });

  it('제한 초과 시 RateLimitExceededError', async () => {
    const limiter = new RateLimiter(3, 'memory');
    await limiter.check();
    await limiter.check();
    await limiter.check();
    await expect(limiter.check()).rejects.toThrow(RateLimitExceededError);
  });

  it('에러 메시지에 제한 횟수 포함', async () => {
    const limiter = new RateLimiter(2, 'memory');
    await limiter.check();
    await limiter.check();
    await expect(limiter.check()).rejects.toThrow(/2/);
  });

  it('슬라이딩 윈도우 — 만료된 항목 제거', async () => {
    const limiter = new RateLimiter(2, 'memory');
    // 61초 이전 타임스탬프 직접 삽입
    limiter._window.push(Date.now() - 61_000);
    limiter._window.push(Date.now() - 61_000);
    // 만료된 항목이 제거되므로 2번 더 호출 가능
    await limiter.check();
    await limiter.check();
  });

  it('limit=1이면 첫 호출만 허용', async () => {
    const limiter = new RateLimiter(1, 'memory');
    await limiter.check();
    await expect(limiter.check()).rejects.toThrow(RateLimitExceededError);
  });

  it('독립 인스턴스는 각자의 카운터 보유', async () => {
    const a = new RateLimiter(1, 'memory');
    const b = new RateLimiter(1, 'memory');
    await a.check();
    await expect(a.check()).rejects.toThrow(RateLimitExceededError);
    // b는 아직 여유
    await expect(b.check()).resolves.not.toThrow();
  });
});

describe('RateLimiter — redis backend (URL 미설정)', () => {
  it('BRAIN_RATE_LIMIT_REDIS_URL 미설정 시 오류', async () => {
    const backup = process.env.BRAIN_RATE_LIMIT_REDIS_URL;
    delete process.env.BRAIN_RATE_LIMIT_REDIS_URL;
    const limiter = new RateLimiter(10, 'redis');
    await expect(limiter.check()).rejects.toThrow(/Redis URL/);
    if (backup) process.env.BRAIN_RATE_LIMIT_REDIS_URL = backup;
  });
});
