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
    [{ role: 'user', content: msg.payload.content }],
    {
      maxTokens: 500,     // 최대 2000
      temperature: 0.7,   // 0.0 ~ 1.0
      timeout: 30000,     // 밀리초 단위 응답 대기
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
- `role`은 `'user'`, `'assistant'`만 허용 (`'system'` 불허)
- `maxTokens` 최대 2000
- `temperature` 0.0 ~ 1.0

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

## 9. 타입 참조 (JSDoc)

```javascript
const sdk = require('cassiopeia-sdk');
// AgentResult, OrchestraTask, LLMRequest, LLMResponse는 JSDoc으로 정의됩니다.
// IDE에서 자동완성 및 타입 힌트로 활용하세요.
```

---

## 10. 환경 변수 정리

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `REDIS_URL` | Redis 서버 주소 | `redis://localhost:6379` |
| `ORCHESTRA_URL` | 오케스트라 HTTP 주소 | `http://localhost:8000` |
| `ORCHESTRA_API_KEY` | 오케스트라 API 키 | — |
| `DISPATCH_HMAC_SECRET` | HMAC 서명 검증 시크릿 | — (미설정 시 검증 생략) |

---

## 11. Docker 환경

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
