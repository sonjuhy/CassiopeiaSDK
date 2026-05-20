# Cassiopeia Agent Node.js SDK 활용 가이드

외부 프로젝트에서 `cassiopeia-sdk` 하나만 설치해 오케스트라 네트워크에 에이전트를 연결하는 방법을 설명합니다.

---

## 1. 설치

```bash
npm install cassiopeia-sdk
```

의존성: `ioredis`, `zod`  
요구사항: **Node.js 18 이상** (내장 `fetch` 사용)

---

## 2. 빠른 시작 — AgentBase

가장 간단한 에이전트 구현입니다. `AgentBase`를 상속하고 `handle()`만 구현하면 됩니다.

```javascript
const { AgentBase } = require('cassiopeia-sdk');

class MyAgent extends AgentBase {
  async handle(msg) {
    const { task_id, content } = msg.payload;

    // 처리 후 결과 반환
    await this.sendResult(task_id, { answer: `처리 완료: ${content}` });
  }
}

async function main() {
  const agent = new MyAgent(
    process.env.AGENT_ID || 'my_agent',
    process.env.REDIS_URL || 'redis://localhost:6379'
  );

  // 오케스트라에 등록 (최초 1회)
  await agent.register(
    process.env.ORCHESTRA_URL || 'http://localhost:8000',
    {
      capabilities: ['my_action'],
      apiKey: process.env.ORCHESTRA_API_KEY || '',
    }
  );

  // 메시지 수신 루프 시작
  await agent.start();
}

main().catch(console.error);
```

---

## 3. 오케스트라에 에이전트 등록

```javascript
await agent.register('http://localhost:8000', {
  capabilities: ['search', 'summarize'],  // 이 에이전트가 처리할 액션 목록
  lifecycleType: 'long_running',          // 'long_running' | 'ephemeral'
  permissionPreset: 'standard',           // 'minimal' | 'standard' | 'trusted'
  allowLlmAccess: true,                   // LLM 게이트웨이 사용 여부
  apiKey: 'your-api-key',
});
```

| `lifecycleType` | 설명 |
|----------------|------|
| `long_running` | 상시 구동, 헬스체크 대상 |
| `ephemeral` | 요청 시 실행, 헬스체크 없음 |

| `permissionPreset` | LLM 접근 기본값 |
|-------------------|----------------|
| `minimal` | 불허 |
| `standard` | 불허 |
| `trusted` | 허용 |

> `allowLlmAccess: true`를 명시하면 프리셋 기본값을 덮어씁니다.

---

## 4. 결과 반환

```javascript
// 성공
await this.sendResult(msg.payload.task_id, { summary: '처리 결과' });

// 실패
await this.sendResult(msg.payload.task_id, {}, '처리 중 오류 발생');
```

---

## 5. LLM 사용 (게이트웨이)

`allowLlmAccess: true`로 등록된 에이전트는 별도의 API 키 없이 오케스트라의 LLM을 호출할 수 있습니다.

```javascript
async handle(msg) {
  const response = await this.requestLlm(
    [
      { role: 'system', content: '너는 친절한 도우미야.' },   // system 허용
      { role: 'user',   content: msg.payload.content },
    ],
    {
      maxTokens: 500,              // 최대 2000
      temperature: 0.7,            // 0.0 ~ 1.0
      timeout: 30000,              // 밀리초 단위 응답 대기
      model: 'gemini-1.5-pro',     // 모델 오버라이드 (생략 시 서버 기본값)
    }
  );

  if (response.status === 'completed') {
    await this.sendResult(msg.payload.task_id, { answer: response.content });
  } else if (response.status === 'rate_limited') {
    const retryAfter = response.retry_after || 60; // 초 단위
    // retryAfter 초 후 재시도
  } else if (response.status === 'unauthorized') {
    // allowLlmAccess: true 등록 필요
  }
}
```

**제약 사항:**
- `role`은 `'user'`, `'assistant'`, `'system'` 허용
- `maxTokens` 최대 2000
- `temperature` 0.0 ~ 1.0
- `model` 미지정 시 오케스트라 서버 기본값 사용 (payload에서 키 자체 제외됨)
- 잘못된 값은 서버 전송 전 Zod 오류로 차단됨

---

## 6. 수신 메시지 구조

`handle()`에 전달되는 `msg` 객체의 구조입니다.

```javascript
msg.sender    // 보낸 에이전트 (보통 'orchestra')
msg.receiver  // 이 에이전트의 agentId
msg.action    // 수행할 액션 이름
msg.payload   // 태스크 데이터
```

`msg.payload`의 주요 필드:

```javascript
{
  task_id:    'uuid',           // 필수 — sendResult()에 전달
  session_id: 'U1:C1',
  content:    '사용자 요청 원문',
  action:     'search',         // 이 에이전트에 요청된 액션
  params:     { query: '...' },
  requester:  { user_id: 'U1', channel_id: 'C1' },
  source:     'slack',
}
```

---

## 7. HMAC 서명 검증

`AgentBase`는 수신 메시지의 서명을 자동으로 검증합니다. 직접 검증이 필요한 경우:

```javascript
const { verifyMessage, DispatchAuthError } = require('cassiopeia-sdk');

try {
  verifyMessage(payload, 'your-hmac-secret');
} catch (e) {
  if (e instanceof DispatchAuthError) {
    console.error(`서명 불일치: ${e.message}`);
  }
}
```

환경변수 `DISPATCH_HMAC_SECRET`을 설정하면 `secret` 인수 없이 자동 적용됩니다. 미설정 시 검증을 건너뜁니다 (하위호환).

> **Python 호환:** 오케스트라(Python)가 서명한 HMAC과 동일한 알고리즘(HMAC-SHA256, sort_keys)을 사용합니다.

---

## 8. 저수준 API — CassiopeiaClient 직접 사용

`AgentBase` 없이 메시지를 직접 다루고 싶은 경우입니다.

```javascript
const { CassiopeiaClient } = require('cassiopeia-sdk');

const client = new CassiopeiaClient('my_agent', 'redis://localhost:6379');
await client.connect();

// 메시지 전송
await client.sendMessage('agent_result', {
  task_id: '...',
  status: 'COMPLETED',
  result_data: {},
}, 'orchestra');

// 메시지 수신
await client.listen((msg) => {
  console.log(msg.action, msg.payload);
});

await client.disconnect();
```

---

## 9. AgentBrain — 자연어 요청 분석 (v0.3.0)

`AgentBrain`은 사용자의 자연어 요청을 분석해 어떤 Tool을 어떤 파라미터로 호출해야 하는지 결정합니다. 프롬프트 인젝션 방어, 신뢰도 평가, 재시도, 출력 이스케이핑을 내장합니다.

### 9.1. 기본 사용법

```javascript
const { AgentBase, Tool, brain } = require('cassiopeia-sdk');
const { AgentBrain, AgentBrainConfig, BrainDecision } = brain;

class MyAgent extends AgentBase {
  constructor(agentId, redisUrl) {
    super(agentId, redisUrl);

    this.brain = new AgentBrain({
      agentName: agentId,
      capabilities: '파일 검색 및 노트 관리',
      backend: 'gateway',
      llmCaller: this.requestLlm.bind(this),   // 오케스트라 LLM 게이트웨이 재사용
      config: new AgentBrainConfig({
        confidenceThreshold: 0.7,    // 이 미만이면 ask_clarification 반환
        rateLimitPerMinute: 60,      // 분당 최대 analyzeTask 호출 수
        outputEscapePolicy: 'html',  // 출력 이스케이핑 정책
      }),
    });

    this.tools = [
      new Tool({
        name: 'search_file',
        description: '파일 검색',
        parameters: {
          type: 'object',
          properties: { query: { type: 'string' } },
          required: ['query'],
        },
      }),
    ];
  }

  async handle(msg) {
    const decision = await this.brain.analyzeTask(
      msg.payload.content,
      this.tools,
      msg.payload.history || null,   // 이전 대화 맥락 (선택)
    );

    if (decision.action === 'ask_clarification') {
      // 사용자에게 재질문
      await this.sendResult(msg.payload.task_id, {
        reply: decision.suggested_reply,
      });
      return;
    }

    // decision.action, decision.params 로 Tool 실행
    const result = await myExecutor(decision.action, decision.params);
    await this.sendResult(msg.payload.task_id, { answer: result });
  }
}
```

### 9.2. BrainDecision 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `action` | `string` | 실행할 Tool 이름 또는 `'ask_clarification'` |
| `params` | `object` | 검증된 Tool 파라미터 |
| `confidence` | `number` (0.0–1.0) | LLM 응답 신뢰도 (기본값 0.0) |
| `reasoning` | `string\|null` | LLM의 선택 이유 |
| `suggested_reply` | `string\|null` | ask_clarification 시 사용자에게 전달할 문구 |

### 9.3. AgentBrainConfig 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `confidenceThreshold` | `0.7` | 이 값 미만이면 `ask_clarification` 반환 |
| `maxRetries` | `2` | JSON 파싱/검증 실패 시 재시도 횟수 |
| `enableInjectionGuard` | `true` | 정규식 기반 인젝션 방어 활성화 |
| `injectionGuardPolicy` | `'fallback'` | `'fallback'`(ask_clarification 반환) 또는 `'raise'`(예외 발생) |
| `enableLlmSecondaryGuard` | `false` | LLM 기반 2차 인젝션 방어 (추가 LLM 호출 발생) |
| `rateLimitPerMinute` | `null` | 분당 최대 호출 수 (`null`=무제한) |
| `rateLimitBackend` | `'memory'` | `'memory'` 또는 `'redis'` |
| `outputEscapePolicy` | `'markdown'` | `'none'`, `'markdown'`, `'html'` 중 택일 |

### 9.4. 예외 처리

```javascript
const { brain } = require('cassiopeia-sdk');
const {
  PromptInjectionError,
  ParamsValidationError,
  RateLimitExceededError,
} = brain;

try {
  const decision = await this.brain.analyzeTask(userInput, tools);
} catch (e) {
  if (e instanceof RateLimitExceededError) {
    // 분당 한도 초과
  } else if (e instanceof PromptInjectionError) {
    // injectionGuardPolicy='raise' 설정 시 발생
  } else if (e instanceof ParamsValidationError) {
    // maxRetries 소진 후에도 유효한 응답 없음
  }
}
```

---

## 10. 타입 참조 (JSDoc)

```javascript
const sdk = require('cassiopeia-sdk');
// AgentResult, OrchestraTask, LLMRequest, LLMResponse는 JSDoc으로 정의됩니다.
// IDE에서 자동완성 및 타입 힌트로 활용하세요.
```

---

## 11. 환경 변수 정리

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `REDIS_URL` | Redis 서버 주소 | `redis://localhost:6379` |
| `ORCHESTRA_URL` | 오케스트라 HTTP 주소 | `http://localhost:8000` |
| `ORCHESTRA_API_KEY` | 오케스트라 API 키 | — |
| `DISPATCH_HMAC_SECRET` | HMAC 서명 검증 시크릿 | — (미설정 시 검증 생략) |
| `BRAIN_RATE_LIMIT_REDIS_URL` | AgentBrain RateLimiter redis 백엔드 URL | — (`rateLimitBackend: 'redis'` 시 필수) |

---

## 12. Docker 환경

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
CMD ["node", "main.js"]
```

```yaml
# docker-compose.yml
services:
  my_agent:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379
      - ORCHESTRA_URL=http://orchestra:8000
      - ORCHESTRA_API_KEY=${ORCHESTRA_API_KEY}
      - DISPATCH_HMAC_SECRET=${DISPATCH_HMAC_SECRET}
    depends_on:
      - redis
```

> 에이전트는 오케스트라의 **Redis 서버**에만 접근할 수 있으면 됩니다. 오케스트라 HTTP는 `register()` 호출 시에만 필요합니다.
