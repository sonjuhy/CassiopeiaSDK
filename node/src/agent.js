/**
 * AgentBase — 외부 에이전트 기본 클래스
 *
 * 사용법:
 *   class MyAgent extends AgentBase {
 *     async handle(msg) {
 *       const response = await this.requestLlm([{ role: 'user', content: msg.payload.content }]);
 *       await this.sendResult(msg.payload.task_id, { answer: response.content });
 *     }
 *   }
 *
 *   const agent = new MyAgent('my_agent', process.env.REDIS_URL);
 *   await agent.register(process.env.ORCHESTRA_URL, { capabilities: ['my_action'], allowLlmAccess: true });
 *   await agent.start();
 */
'use strict';

const crypto = require('crypto');
const { CassiopeiaClient } = require('./client');
const { verifyMessage, DispatchAuthError } = require('./auth');

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

  /**
   * 연결 후 메시지 수신 루프를 시작합니다. 프로세스가 종료될 때까지 실행됩니다.
   */
  async start() {
    await this.client.connect();
    await this.client.listen(async (msg) => {
      // LLM 게이트웨이 응답은 내부적으로 처리
      if (msg.action === 'llm_result') {
        this._resolveLlm(msg.payload);
        return;
      }

      // HMAC 검증
      try {
        verifyMessage(msg.payload);
      } catch (e) {
        if (e instanceof DispatchAuthError) return; // 무효 메시지 무시
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
   * 오케스트라에 처리 결과를 반환합니다.
   * @param {string} taskId        - msg.payload.task_id
   * @param {Object} resultData    - 처리 결과 데이터
   * @param {string|null} error    - 오류 메시지 (실패 시)
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
   * allow_llm_access=true로 등록된 에이전트만 사용 가능합니다.
   *
   * @param {Array<{role: 'user'|'assistant', content: string}>} messages
   * @param {Object} [options]
   * @param {number} [options.maxTokens=500]       - 최대 토큰 수 (1~2000)
   * @param {number} [options.temperature=0.7]     - 온도 (0.0~1.0)
   * @param {number} [options.timeout=30000]       - 응답 대기 밀리초
   * @returns {Promise<import('./schemas').LLMResponse>}
   */
  async requestLlm(messages, { maxTokens = 500, temperature = 0.7, timeout = 30000 } = {}) {
    const taskId = crypto.randomUUID();

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this._pendingLlm.delete(taskId);
        reject(new Error('LLM 요청 타임아웃'));
      }, timeout);

      this._pendingLlm.set(taskId, { resolve, reject, timer });

      this.client
        .sendMessage(
          'llm_call',
          {
            task_id: taskId,
            agent_id: this.agentId,
            messages,
            max_tokens: maxTokens,
            temperature,
          },
          'orchestra'
        )
        .catch((err) => {
          clearTimeout(timer);
          this._pendingLlm.delete(taskId);
          reject(err);
        });
    });
  }

  /**
   * 오케스트라 HTTP API로 이 에이전트를 등록합니다.
   * Node.js 18+ 내장 fetch를 사용합니다.
   *
   * @param {string} orchestraUrl  - 오케스트라 주소 (예: "http://localhost:8000")
   * @param {Object} [options]
   * @param {string[]} [options.capabilities=[]]
   * @param {string}   [options.lifecycleType='long_running']   - 'long_running' | 'ephemeral'
   * @param {string}   [options.permissionPreset='standard']    - 'minimal' | 'standard' | 'trusted'
   * @param {boolean}  [options.allowLlmAccess=false]
   * @param {string}   [options.apiKey='']
   * @returns {Promise<boolean>}
   */
  async register(orchestraUrl, {
    capabilities = [],
    lifecycleType = 'long_running',
    permissionPreset = 'standard',
    allowLlmAccess = false,
    apiKey = '',
  } = {}) {
    const response = await fetch(`${orchestraUrl}/agents`, {
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
