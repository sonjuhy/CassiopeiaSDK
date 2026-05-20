/**
 * LLM 게이트웨이 Zod 스키마 — 런타임 검증 포함
 *
 * Python cassiopeia_sdk.schemas와 동일한 검증 규칙을 적용합니다.
 */
'use strict';

const { z } = require('zod');

// model 필드 허용 패턴: 영문자·숫자·점·하이픈, 1~100자
const MODEL_PATTERN = /^[a-zA-Z0-9.\-]+$/;

// 허용 role 집합
const ALLOWED_ROLES = new Set(['user', 'assistant', 'system']);

// ---------------------------------------------------------------------------
// LLMRequest — LLM 게이트웨이 요청 스키마
// ---------------------------------------------------------------------------

const LLMRequestSchema = z.object({
  task_id: z.string(),
  agent_id: z.string(),
  messages: z
    .array(z.object({ role: z.string(), content: z.string() }))
    .refine(
      (msgs) => msgs.every((m) => ALLOWED_ROLES.has(m.role)),
      { message: 'messages의 role은 user | assistant | system 중 하나여야 합니다' }
    ),
  max_tokens: z.number().int().min(1).max(2000).default(500),
  temperature: z.number().min(0.0).max(1.0).default(0.7),
  model: z
    .string()
    .min(1)
    .max(100)
    .regex(MODEL_PATTERN, {
      message: 'model은 영문자·숫자·점·하이픈으로 구성된 1~100자 문자열이어야 합니다',
    })
    .nullable()
    .optional(),
});

// ---------------------------------------------------------------------------
// LLMResponse — LLM 게이트웨이 응답 스키마
// ---------------------------------------------------------------------------

const LLMResponseSchema = z
  .object({
    task_id: z.string(),
    status: z.enum(['completed', 'rate_limited', 'unauthorized', 'error']),
    content: z.string().default(''),
    usage: z.record(z.any()).default({}),
    error: z.string().nullable().optional(),
    retry_after: z.number().nullable().optional(),
    model: z.string().nullable().optional(),
  })
  .passthrough(); // 서버 추가 필드 허용

module.exports = { LLMRequestSchema, LLMResponseSchema };
