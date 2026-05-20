'use strict';

/**
 * GatewayProvider — AgentBase.requestLlm을 주입받아 카시오페아 LLM 게이트웨이를 통해 호출합니다.
 *
 * Future 대기(pendingLlm 매핑) 메커니즘은 AgentBase에 구현되어 있습니다.
 * CassiopeiaClient만으로는 이 메커니즘을 재현할 수 없으므로,
 * AgentBase.requestLlm 메서드를 함수로 직접 주입받아 위임합니다.
 */
class GatewayProvider {
  /** @param {Function} caller - AgentBase.requestLlm 바인딩된 메서드 */
  constructor(caller) {
    this.caller = caller;
  }

  /**
   * @param {Array<{role:string,content:string}>} messages
   * @param {object} [options]
   * @returns {Promise<object>} LLM 응답 payload
   */
  async call(messages, { model = null, maxTokens = 500, temperature = 0.7 } = {}) {
    return await this.caller(messages, { model, maxTokens, temperature });
  }
}

/**
 * DirectProvider — 외부 LLM API를 직접 호출합니다. (3rd-party 독립 에이전트용)
 *
 * API 키는 에이전트 범위 환경변수를 통해 격리 로드합니다.
 * 환경변수 명명 규칙: {AGENT_NAME}_{PROVIDER}_API_KEY
 * 예: ARCHIVE_AGENT_GEMINI_API_KEY, RESEARCH_AGENT_ANTHROPIC_API_KEY
 *
 * ⚠️ v0.3.0에서는 GatewayProvider가 최우선 지원됩니다.
 *    DirectProvider는 인터페이스만 정의되어 있으며,
 *    실제 API 호출 구현은 각 provider별 확장 패키지에서 추가됩니다.
 */
class DirectProvider {
  static _PROVIDER_ENV_MAP = {
    gemini: 'GEMINI',
    claude: 'ANTHROPIC',
    local: 'LOCAL',
  };

  /** @param {'gemini'|'claude'|'local'} backend @param {string} agentName */
  constructor(backend, agentName) {
    if (backend === 'gateway') {
      throw new Error('DirectProvider는 gateway 백엔드를 지원하지 않습니다. GatewayProvider를 사용하세요.');
    }
    this.backend = backend;
    this.agentName = agentName.toUpperCase();
    this._apiKey = this._loadApiKey();
  }

  _loadApiKey() {
    const providerKey = DirectProvider._PROVIDER_ENV_MAP[this.backend] || this.backend.toUpperCase();
    const envVar = `${this.agentName}_${providerKey}_API_KEY`;
    return process.env[envVar] || null;
  }

  async call(messages, options = {}) {
    throw new Error(
      `DirectProvider(${this.backend})는 v0.3.0에서 아직 구현되지 않았습니다. ` +
      'GatewayProvider를 사용하거나 해당 provider 구현체를 추가하세요.'
    );
  }
}

class LLMProviderFactory {
  static create(backend, agentName) {
    return new DirectProvider(backend, agentName);
  }
}

module.exports = { GatewayProvider, DirectProvider, LLMProviderFactory };
