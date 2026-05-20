/**
 * AgentBase — 외부 에이전트 기본 클래스
 *
 * Usage:
 *   class MyAgent extends AgentBase {
 *     async handle(msg) {
 *       const result = await this.requestLlm(
 *         [{ role: 'user', content: msg.payload.content }],
 *         { model: 'gemini-1.5-pro', maxTokens: 800 }
 *       );
 *       await this.sendResult(msg.payload.task_id, { answer: result.content });
 *     }
 *   }
 *
 *   const agent = new MyAgent('my_agent', process.env.REDIS_URL);
 *   await agent.register(process.env.CASSIOPEIA_URL, { capabilities: ['my_action'] });
 *   await agent.start();
 */
'use strict';

const crypto = require('crypto');
const { CassiopeiaClient } = require('./client');
const { verifyMessage, DispatchAuthError } = require('./auth');
const { LLMRequestSchema } = require('./schemas');

class AgentBase {
  /**
   * @param {string} agentId  - 이 에이전트의 고유 식별자
   * @param {string} redisUrl - Redis 서버 주소
   */
  constructor(agentId, redisUrl) {
    this.agentId = agentId;
    this.client = new CassiopeiaClient(agentId, redisUrl);
    /** @type {Map<string, {resolve: Function, reject: Function, timer: NodeJS.Timeout}>} */
    this._pendingLlm = new Map();
  }

  /** 연결 후 메시지 수신 루프를 시작합니다. */
  async start() {
    await this.client.connect();
    await this.client.listen(async (msg) => {
      if (msg.action === 'llm_result') {
        this._resolveLlm(msg.payload);
        return;
      }
      try {
        verifyMessage(msg.payload);
      } catch (e) {
        if (e instanceof DispatchAuthError) return;
        return;
      }
      try {
        await this.handle(msg);
      } catch (e) {
        console.error(`[AgentBase] handle() 오류: ${e.message}`);
      }
    });
  }

  /**
   * 수신 메시지 처리. 반드시 하위 클래스에서 override해야 합니다.
   * @param {import('./client').AgentMessage} msg
   */
  async handle(msg) {
    throw new Error('handle()을 구현해야 합니다');
  }

  /**
   * 카시오페아에 처리 결과를 반환합니다.
   * @param {string} taskId
   * @param {object} resultData
   * @param {string|null} error
   */
  async sendResult(taskId, resultData, error = null) {
    await this.client.sendMessage(
      'agent_result',
      {
        task_id: taskId,
        agent: this.agentId,
        status: error ? 'FAILED' : 'COMPLETED',
        result_data: resultData,
        error: error,
        usage_stats: {},
      },
      'orchestra'
    );
  }

  /**
   * 오케스트라 LLM 게이트웨이를 통해 LLM을 호출합니다.
   *
   * @param {Array<{role: 'user'|'assistant'|'system', content: string}>} messages
   * @param {object} [options]
   * @param {number}      [options.maxTokens=500]    - 최대 토큰 수 (1~2000)
   * @param {number}      [options.temperature=0.7]  - 온도 (0.0~1.0)
   * @param {number}      [options.timeout=30000]    - 응답 대기 밀리초
   * @param {string|null} [options.model=null]       - 모델 오버라이드 (null이면 서버 기본값)
   * @returns {Promise<object>} LLM 응답 payload
   * @throws {ZodError} 입력값이 유효하지 않을 때 (서버 전송 전 차단)
   * @throws {Error}    timeout 내에 응답이 없을 때
   */
  async requestLlm(messages, { maxTokens = 500, temperature = 0.7, timeout = 30000, model = null } = {}) {
    const taskId = crypto.randomUUID();

    // 페이로드 구성 (model=null이면 키 자체를 제외)
    const requestPayload = {
      task_id: taskId,
      agent_id: this.agentId,
      messages,
      max_tokens: maxTokens,
      temperature,
      ...(model !== null && model !== undefined ? { model } : {}),
    };

    // 서버 전송 전 Zod 검증 — 유효하지 않으면 ZodError 발생
    LLMRequestSchema.parse(requestPayload);

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this._pendingLlm.delete(taskId);
        reject(new Error('LLM 요청 타임아웃'));
      }, timeout);

      this._pendingLlm.set(taskId, { resolve, reject, timer });

      this.client
        .sendMessage('llm_call', requestPayload, 'orchestra')
        .catch((err) => {
          clearTimeout(timer);
          this._pendingLlm.delete(taskId);
          reject(err);
        });
    });
  }

  /**
   * HTTP API로 카시오페아에 에이전트를 등록합니다.
   * @param {string} cassiopeiaUrl
   * @param {object} [options]
   * @param {string[]} [options.capabilities=[]]
   * @param {string}   [options.lifecycleType='long_running']
   * @param {string}   [options.permissionPreset='standard']
   * @param {boolean}  [options.allowLlmAccess=false]
   * @param {string}   [options.apiKey='']
   * @returns {Promise<boolean>}
   */
  async register(cassiopeiaUrl, {
    capabilities = [],
    lifecycleType = 'long_running',
    permissionPreset = 'standard',
    allowLlmAccess = false,
    apiKey = '',
  } = {}) {
    const response = await fetch(`${cassiopeiaUrl}/agents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({
        agent_name: this.agentId,
        capabilities,
        lifecycle_type: lifecycleType,
        permission_preset: permissionPreset,
        allow_llm_access: allowLlmAccess,
      }),
    });
    return response.status === 201;
  }

  /** @private */
  _resolveLlm(payload) {
    const taskId = payload.task_id;
    const pending = this._pendingLlm.get(taskId);
    if (pending) {
      clearTimeout(pending.timer);
      this._pendingLlm.delete(taskId);
      pending.resolve(payload);
    }
  }
}

module.exports = { AgentBase };
