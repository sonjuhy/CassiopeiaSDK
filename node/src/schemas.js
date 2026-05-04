/**
 * 오케스트라 프로토콜 타입 정의
 *
 * JSDoc 타입으로만 정의됩니다 — 런타임 영향 없음.
 * IDE 자동완성 및 타입 힌트 용도로 사용하세요.
 */
'use strict';

/**
 * 오케스트라로 결과 반환 시 payload 구조
 * @typedef {Object} AgentResult
 * @property {string} task_id
 * @property {string} agent
 * @property {'COMPLETED'|'FAILED'|'PROCESSING'} status
 * @property {Object} result_data
 * @property {string|null} error
 * @property {Object} usage_stats
 */

/**
 * 오케스트라에서 수신하는 태스크 payload 구조
 * @typedef {Object} OrchestraTask
 * @property {string} task_id
 * @property {string} session_id
 * @property {{user_id: string, channel_id: string}} requester
 * @property {string} content    - 사용자 원문
 * @property {string} action     - 이 에이전트에 요청된 액션
 * @property {Object} params
 * @property {string} source     - "slack" | "api" | ...
 */

/**
 * LLM 게이트웨이 요청 payload 구조
 * @typedef {Object} LLMRequest
 * @property {string} task_id
 * @property {string} agent_id
 * @property {Array<{role: 'user'|'assistant', content: string}>} messages
 * @property {number} max_tokens   - 1 ~ 2000
 * @property {number} temperature  - 0.0 ~ 1.0
 */

/**
 * LLM 게이트웨이 응답 payload 구조
 * @typedef {Object} LLMResponse
 * @property {string} task_id
 * @property {'completed'|'rate_limited'|'unauthorized'|'error'} status
 * @property {string} content
 * @property {{prompt_tokens: number, completion_tokens: number, total_tokens: number}} usage
 * @property {string|null} error
 * @property {number|null} retry_after  - rate_limited일 때만
 */

module.exports = {};
