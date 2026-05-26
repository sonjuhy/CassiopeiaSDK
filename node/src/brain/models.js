'use strict';

const { z } = require('zod');

// ---------------------------------------------------------------------------
// BrainDecision — analyze 반환 모델
// ---------------------------------------------------------------------------

const BrainDecisionSchema = z.object({
  action: z.string(),
  params: z.record(z.any()),
  reasoning: z.string().nullable().optional().default(null),
  /** 기본값 0.0 — 최소 신뢰 원칙. LLM 미반환 시 ask_clarification 자동 유도 */
  confidence: z.number().min(0.0).max(1.0).default(0.0),
  suggested_reply: z.string().nullable().optional().default(null),
});

class BrainDecision {
  /** @param {object} data */
  constructor(data) {
    const validated = BrainDecisionSchema.parse(data);
    this.action = validated.action;
    this.params = validated.params;
    this.reasoning = validated.reasoning ?? null;
    this.confidence = validated.confidence;
    this.suggested_reply = validated.suggested_reply ?? null;
  }

  /** 필드를 업데이트한 새 인스턴스를 반환합니다. */
  copyWith(updates) {
    return new BrainDecision({ ...this, ...updates });
  }
}

// ---------------------------------------------------------------------------
// AgentBrainConfig — 정책 설정
// ---------------------------------------------------------------------------

const AgentBrainConfigSchema = z.object({
  /** JSON 파싱 실패·UnknownActionError·ParamsValidationError 발생 시 최대 재시도 횟수 */
  maxRetries: z.number().int().min(0).default(2),
  /** 이 수치 미만이면 SDK가 ask_clarification 결정을 반환 */
  confidenceThreshold: z.number().min(0).max(1).default(0.7),
  /** false 시 check() 비활성화. check_static()은 항상 실행됨 */
  enableInjectionGuard: z.boolean().default(true),
  /** "raise": PromptInjectionError 발생 / "fallback": ask_clarification 라우팅 */
  injectionGuardPolicy: z.enum(['raise', 'fallback']).default('fallback'),
  /** true 시, 툴 없이 대화만으로 응답할 수 있도록 direct_response 툴 자동 주입 */
  enableDirectResponse: z.boolean().default(false),
  /** true 시 메인 LLM 호출 전 LLM 기반 2차 인젝션 검증 수행 (rate_limit 카운트 포함) */
  enableLlmSecondaryGuard: z.boolean().default(false),
  /** per-agent-instance 분당 최대 호출 횟수. null이면 제한 없음 */
  rateLimitPerMinute: z.number().int().positive().nullable().default(null),
  /** "memory": 단일 프로세스 / "redis": 분산 환경 권장 */
  rateLimitBackend: z.enum(['memory', 'redis']).default('memory'),
  /** LLM 생성 텍스트 이스케이핑 정책 */
  outputEscapePolicy: z.enum(['none', 'markdown', 'html']).default('markdown'),
});

class AgentBrainConfig {
  /** @param {object} [data={}] */
  constructor(data = {}) {
    const validated = AgentBrainConfigSchema.parse(data);
    Object.assign(this, validated);
  }
}

module.exports = { BrainDecision, BrainDecisionSchema, AgentBrainConfig, AgentBrainConfigSchema };
