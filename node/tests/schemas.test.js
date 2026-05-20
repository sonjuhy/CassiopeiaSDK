'use strict';

const { LLMRequestSchema, LLMResponseSchema } = require('../src/schemas');
const { ZodError } = require('zod');

// ---------------------------------------------------------------------------
// LLMRequestSchema
// ---------------------------------------------------------------------------

describe('LLMRequestSchema', () => {

  const BASE = {
    task_id: 't1',
    agent_id: 'a1',
    messages: [{ role: 'user', content: '안녕' }],
  };

  it('model 미지정 시 undefined (페이로드 제외)', () => {
    const r = LLMRequestSchema.parse(BASE);
    expect(r.model).toBeUndefined();
  });

  it('model 지정 시 설정됨', () => {
    const r = LLMRequestSchema.parse({ ...BASE, model: 'gemini-1.5-pro' });
    expect(r.model).toBe('gemini-1.5-pro');
  });

  it('max_tokens 기본값 500', () => {
    expect(LLMRequestSchema.parse(BASE).max_tokens).toBe(500);
  });

  it('temperature 기본값 0.7', () => {
    expect(LLMRequestSchema.parse(BASE).temperature).toBe(0.7);
  });

  it('system role 허용', () => {
    const r = LLMRequestSchema.parse({
      ...BASE,
      messages: [
        { role: 'system', content: '너는 전문가야' },
        { role: 'user', content: '요약해줘' },
      ],
    });
    expect(r.messages[0].role).toBe('system');
  });

  // --- 검증 실패 케이스 ---

  it('model에 공백 포함 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, model: 'invalid model' })).toThrow(ZodError);
  });

  it('model 101자 초과 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, model: 'a'.repeat(101) })).toThrow(ZodError);
  });

  it('model 1자는 유효', () => {
    expect(LLMRequestSchema.parse({ ...BASE, model: 'a' }).model).toBe('a');
  });

  it('model 100자는 유효', () => {
    expect(LLMRequestSchema.parse({ ...BASE, model: 'a'.repeat(100) }).model).toHaveLength(100);
  });

  it('max_tokens 2001 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, max_tokens: 2001 })).toThrow(ZodError);
  });

  it('max_tokens 0 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, max_tokens: 0 })).toThrow(ZodError);
  });

  it('temperature 1.1 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, temperature: 1.1 })).toThrow(ZodError);
  });

  it('temperature -0.1 시 ZodError', () => {
    expect(() => LLMRequestSchema.parse({ ...BASE, temperature: -0.1 })).toThrow(ZodError);
  });

  it('허용되지 않은 role 시 ZodError', () => {
    expect(() =>
      LLMRequestSchema.parse({ ...BASE, messages: [{ role: 'function', content: 'hi' }] })
    ).toThrow(ZodError);
  });

  it('에러 메시지에 한국어 설명 포함', () => {
    try {
      LLMRequestSchema.parse({ ...BASE, model: 'invalid model!' });
    } catch (e) {
      expect(e.message).toMatch(/영문자/);
    }
  });
});

// ---------------------------------------------------------------------------
// LLMResponseSchema
// ---------------------------------------------------------------------------

describe('LLMResponseSchema', () => {

  const BASE_RESP = {
    task_id: 't1',
    status: 'completed',
    content: '응답',
    usage: {},
  };

  it('model 필드가 null일 수 있음', () => {
    const r = LLMResponseSchema.parse({ ...BASE_RESP, model: null });
    expect(r.model).toBeNull();
  });

  it('model 필드에 모델명 설정 가능', () => {
    const r = LLMResponseSchema.parse({ ...BASE_RESP, model: 'gemini-1.5-pro' });
    expect(r.model).toBe('gemini-1.5-pro');
  });

  it('content 기본값 빈 문자열', () => {
    const r = LLMResponseSchema.parse({ task_id: 't', status: 'error' });
    expect(r.content).toBe('');
  });

  it('서버 추가 필드 허용 (passthrough)', () => {
    const r = LLMResponseSchema.parse({ ...BASE_RESP, extra_field: 'value' });
    expect(r.extra_field).toBe('value');
  });
});
