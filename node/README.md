# Cassiopeia Agent Node.js SDK

[한국어](#한국어) | [English](#english)

<a name="english"></a>
## English

### Overview
Official Node.js SDK for the Cassiopeia Agent framework. Install this single library to connect your agent to the orchestra network — no Redis wiring, no message schema boilerplate.

**What you get:**
- `AgentBase` — base class: implement `handle()` and you're done
- `CassiopeiaClient` — low-level Redis Pub/Sub messaging
- `verifyMessage` — HMAC signature verification for incoming tasks
- JSDoc types: `AgentResult`, `OrchestraTask`, `LLMRequest`, `LLMResponse`

### Requirements
- Node.js 18+ (uses built-in `fetch`)
- Access to the orchestra's Redis server

### Installation
```bash
npm install cassiopeia-sdk
```

### Quickstart
```javascript
const { AgentBase } = require('cassiopeia-sdk');

class MyAgent extends AgentBase {
  async handle(msg) {
    // Call LLM through the orchestra gateway (no API key needed)
    const response = await this.requestLlm([
      { role: 'user', content: msg.payload.content }
    ]);
    await this.sendResult(msg.payload.task_id, { answer: response.content });
  }
}

async function main() {
  const agent = new MyAgent(process.env.AGENT_ID, process.env.REDIS_URL);
  await agent.register(process.env.ORCHESTRA_URL, {
    capabilities: ['my_action'],
    allowLlmAccess: true,
    apiKey: process.env.ORCHESTRA_API_KEY,
  });
  await agent.start();
}

main().catch(console.error);
```

See [GUIDE.md](GUIDE.md) for the full reference.

---

<a name="한국어"></a>
## 한국어

### 개요
Cassiopeia 에이전트 프레임워크의 공식 Node.js SDK입니다. 이 라이브러리 하나만 설치하면 오케스트라 네트워크에 에이전트를 연결할 수 있습니다. Redis 연결이나 메시지 스키마를 직접 다룰 필요가 없습니다.

**제공 기능:**
- `AgentBase` — 기본 클래스: `handle()`만 구현하면 동작
- `CassiopeiaClient` — 저수준 Redis Pub/Sub 메시징
- `verifyMessage` — 수신 메시지 HMAC 서명 검증
- JSDoc 타입: `AgentResult`, `OrchestraTask`, `LLMRequest`, `LLMResponse`

### 요구사항
- Node.js 18 이상 (내장 `fetch` 사용)
- 오케스트라의 Redis 서버 접근 가능

### 설치
```bash
npm install cassiopeia-sdk
```

### 빠른 시작
```javascript
const { AgentBase } = require('cassiopeia-sdk');

class MyAgent extends AgentBase {
  async handle(msg) {
    // 오케스트라 LLM 게이트웨이 호출 (별도 API 키 불필요)
    const response = await this.requestLlm([
      { role: 'user', content: msg.payload.content }
    ]);
    await this.sendResult(msg.payload.task_id, { answer: response.content });
  }
}

async function main() {
  const agent = new MyAgent(process.env.AGENT_ID, process.env.REDIS_URL);
  await agent.register(process.env.ORCHESTRA_URL, {
    capabilities: ['my_action'],
    allowLlmAccess: true,
    apiKey: process.env.ORCHESTRA_API_KEY,
  });
  await agent.start();
}

main().catch(console.error);
```

전체 레퍼런스는 [GUIDE.md](GUIDE.md)를 참고하세요.
