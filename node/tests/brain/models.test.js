'use strict';

const { BrainDecision, AgentBrainConfig } = require('../../src/brain/models');

describe('BrainDecision', () => {

  it('confidence 기본값 0.0 (최소 신뢰 원칙)', () => {
    const d = new BrainDecision({ action: 'x', params: {} });
    expect(d.confidence).toBe(0.0);
  });

  it('confidence 0.0~1.0 범위 내 허용', () => {
    const d = new BrainDecision({ action: 'x', params: {}, confidence: 0.85 });
    expect(d.confidence).toBe(0.85);
  });

  it('confidence < 0 시 ZodError', () => {
    expect(() => new BrainDecision({ action: 'x', params: {}, confidence: -0.1 })).toThrow();
  });

  it('confidence > 1 시 ZodError', () => {
    expect(() => new BrainDecision({ action: 'x', params: {}, confidence: 1.1 })).toThrow();
  });

  it('optional 필드 기본값 null', () => {
    const d = new BrainDecision({ action: 'x', params: {} });
    expect(d.reasoning).toBeNull();
    expect(d.suggested_reply).toBeNull();
  });

  it('copyWith로 새 인스턴스 생성 — 원본 불변', () => {
    const d = new BrainDecision({ action: 'x', params: {}, reasoning: 'original' });
    const d2 = d.copyWith({ reasoning: 'updated' });
    expect(d2.reasoning).toBe('updated');
    expect(d.reasoning).toBe('original');
  });
});

describe('AgentBrainConfig', () => {

  it('기본값 확인', () => {
    const cfg = new AgentBrainConfig();
    expect(cfg.maxRetries).toBe(2);
    expect(cfg.confidenceThreshold).toBe(0.7);
    expect(cfg.enableInjectionGuard).toBe(true);
    expect(cfg.injectionGuardPolicy).toBe('fallback');
    expect(cfg.enableLlmSecondaryGuard).toBe(false);
    expect(cfg.rateLimitPerMinute).toBeNull();
    expect(cfg.rateLimitBackend).toBe('memory');
    expect(cfg.outputEscapePolicy).toBe('markdown');
  });

  it('커스텀 값 설정', () => {
    const cfg = new AgentBrainConfig({
      maxRetries: 0,
      confidenceThreshold: 0.9,
      enableInjectionGuard: false,
      injectionGuardPolicy: 'raise',
      rateLimitPerMinute: 30,
      rateLimitBackend: 'redis',
      outputEscapePolicy: 'html',
    });
    expect(cfg.maxRetries).toBe(0);
    expect(cfg.injectionGuardPolicy).toBe('raise');
    expect(cfg.rateLimitPerMinute).toBe(30);
  });

  it('잘못된 injectionGuardPolicy 시 오류', () => {
    expect(() => new AgentBrainConfig({ injectionGuardPolicy: 'unknown' })).toThrow();
  });

  it('잘못된 outputEscapePolicy 시 오류', () => {
    expect(() => new AgentBrainConfig({ outputEscapePolicy: 'xml' })).toThrow();
  });
});
