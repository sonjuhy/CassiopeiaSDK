# Spec: Cassiopeia Agent Node.js SDK

## 1. Objective (목적)
노코드(No-code) 혹은 바이브 코딩(Vibe-coding) 환경의 개발자가 **단 하나의 라이브러리**만으로 오케스트라(Cassiopeia) 에이전트와 통신하고, LLM을 호출하는 에이전트를 손쉽게 빌드할 수 있도록 하는 Node.js SDK와 그 활용 가이드를 제공합니다. 통신 규격(Redis Pub/Sub), HMAC 서명 검증, LLM 게이트웨이 연동, 에러 처리 등의 복잡성을 라이브러리가 완전히 추상화하여, 개발자는 비즈니스 로직에만 집중할 수 있어야 합니다.

## 2. Tech Stack (기술 스택)
- **Node.js SDK:** Node.js 18+, `ioredis` (비동기 통신), `jest` (테스트), `zod` (데이터 유효성 검증)
- **내장 모듈:** `crypto` (HMAC 서명 검증), `fetch` (오케스트라 HTTP 등록)
- **문서화:** Markdown (`GUIDE.md`, `README.md`)

## 3. Commands (실행 명령어)
- 의존성 설치: `npm install`
- 테스트: `npm test`

## 4. Project Structure (프로젝트 구조)
```text
node/
├── SPEC.md                  # 스펙 정의 문서
├── GUIDE.md                 # 에이전트 개발 가이드 문서
├── README.md                # 설치 및 빠른 시작
├── package.json
├── src/
│   ├── index.js             # 진입점 (공개 API 재수출)
│   ├── client.js            # Redis Pub/Sub 저수준 통신 클라이언트
│   ├── agent.js             # AgentBase — 에이전트 기본 클래스
│   ├── auth.js              # HMAC 서명 검증, pythonJsonDumps
│   ├── schemas.js           # JSDoc 타입 정의 (AgentResult, OrchestraTask, LLMRequest, LLMResponse)
│   └── tools.js             # 도구 호출 규격 처리
└── tests/
    ├── agent.test.js        # AgentBase 단위 테스트
    ├── auth.test.js         # verifyMessage, pythonJsonDumps 단위 테스트
    ├── client.test.js       # CassiopeiaClient 단위 테스트
    └── tools.test.js        # Tool/ToolExecutor 단위 테스트
```

## 5. Module Responsibilities (모듈 책임)

| 모듈 | 책임 |
|------|------|
| `client.js` | Redis Pub/Sub 연결·발행·구독. 저수준 메시지 직렬화/역직렬화 |
| `agent.js` | `AgentBase` 클래스 — `start()`, `handle()`, `sendResult()`, `requestLlm()`, `register()` |
| `auth.js` | HMAC-SHA256 서명 검증 (`verifyMessage`), Python 호환 JSON 직렬화 (`pythonJsonDumps`) |
| `schemas.js` | JSDoc 타입 정의만 포함. 런타임 로직 없음 |
| `tools.js` | `Tool`, `ToolExecutor` — zod 스키마 기반 도구 정의 및 실행 |
| `index.js` | 공개 API 재수출 (`AgentBase`, `CassiopeiaClient`, `verifyMessage`, `DispatchAuthError`, JSDoc 타입) |

## 6. Code Style (코드 스타일)
```javascript
// src/agent.js — AgentBase 사용 패턴
const { AgentBase } = require('cassiopeia-sdk');

class MyAgent extends AgentBase {
  async handle(msg) {
    const response = await this.requestLlm([
      { role: 'user', content: msg.payload.content }
    ], { maxTokens: 500, temperature: 0.7 });

    await this.sendResult(msg.payload.task_id, { answer: response.content });
  }
}

const agent = new MyAgent(process.env.AGENT_ID, process.env.REDIS_URL);
await agent.register(process.env.ORCHESTRA_URL, {
  capabilities: ['my_action'],
  allowLlmAccess: true,
  apiKey: process.env.ORCHESTRA_API_KEY,
});
await agent.start();
```

## 7. Key Design Decisions (핵심 설계 결정)

### LLM 게이트웨이 연동 패턴
외부 에이전트는 직접 LLM API를 호출하지 않습니다. `requestLlm()`이 오케스트라로 `llm_call` 액션을 전송하고, 오케스트라가 LLM을 호출한 뒤 `llm_result`로 응답합니다. Node.js의 Promise + Map 패턴으로 비동기 응답을 매칭합니다.

```javascript
// _pendingLlm: Map<taskId, { resolve, reject, timer }>
requestLlm(messages, opts) {
  const taskId = crypto.randomUUID();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { reject(new Error('타임아웃')); }, opts.timeout);
    this._pendingLlm.set(taskId, { resolve, reject, timer });
    this.client.sendMessage('llm_call', { task_id: taskId, ... }, 'orchestra');
  });
}
```

### Python 호환 HMAC 서명
오케스트라(Python)가 `json.dumps(sort_keys=True)`로 서명합니다. Python의 기본 구분자는 `": "`, `", "` (공백 포함)입니다. Node.js의 `JSON.stringify()`는 공백 없이 직렬화하므로 `pythonJsonDumps()`로 동일한 형식을 재현합니다.

```javascript
// pythonJsonDumps({ z: 1, a: 2 }) === '{"a": 1, "z": 2}'
```

## 8. Testing Strategy (테스트 전략)
- **TDD 원칙:** RED → GREEN → REFACTOR 사이클 준수
- **단위 테스트:** `jest`로 모든 공개 API 커버
- **모킹:** `jest.mock('../src/client')`으로 Redis 통신 격리
- **크로스 언어 검증:** `pythonJsonDumps` 출력이 Python `json.dumps` 결과와 일치함을 테스트로 확인
- **테스트 현황:** 27개 테스트 전체 통과

## 9. Boundaries (경계 및 규칙)
- **Always do:** 테스트 코드를 먼저 작성하고 통과를 확인합니다. 문서와 주석은 한국어로 작성합니다.
- **Never do:** 시크릿 키나 하드코딩된 Redis URL을 라이브러리에 노출하지 않습니다. `system` 역할 메시지를 LLM 요청에 허용하지 않습니다 (프롬프트 인젝션 방어).
- **Ask first:** 외부 의존성을 크게 추가해야 할 경우.

## 10. Success Criteria (성공 기준)
- [x] `AgentBase` 클래스 구현 — `handle()` 오버라이드만으로 에이전트 완성
- [x] `requestLlm()` — 오케스트라 LLM 게이트웨이를 통한 비동기 LLM 호출 (별도 API 키 불필요)
- [x] `sendResult()` — COMPLETED/FAILED 결과를 오케스트라로 반환
- [x] `register()` — 오케스트라 `/agents` 엔드포인트에 에이전트 등록 (Node 18 내장 fetch)
- [x] `verifyMessage()` — Python 오케스트라와 호환되는 HMAC-SHA256 서명 검증
- [x] 27개 단위 테스트 전체 통과 (GREEN)
- [x] `GUIDE.md` — 11개 섹션의 완전한 참조 문서
- [x] `README.md` — 영문/한국어 이중 언어 빠른 시작 가이드

## 11. Open Questions (미결 질문)
- 특이사항 없음.
