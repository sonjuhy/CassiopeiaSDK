# Spec: Cassiopeia Agent SDK 및 가이드

## 1. Objective (목적)
노코드(No-code) 혹은 바이브 코딩(Vibe-coding) 환경의 개발자가 **단 하나의 라이브러리**만으로 오케스트라(Cassiopeia) 에이전트와 통신하고, 도구를 호출하는 에이전트를 손쉽게 빌드할 수 있도록 하는 SDK(Python, Node.js)와 그 활용 가이드를 제공합니다. 통신 규격(Redis Pub/Sub), 권한 관리, 에러 처리 등의 복잡성을 라이브러리가 완전히 추상화하여, 개발자는 비즈니스 로직(혹은 프롬프트)에만 집중할 수 있어야 합니다.

## 2. Tech Stack (기술 스택)
- **Python SDK:** Python 3.10+, `redis` (비동기 통신), `pytest` (테스트), `pydantic` (데이터 유효성 검증)
- **Node.js SDK:** Node.js 18+, `ioredis` (비동기 통신), `jest` (테스트), `zod` (데이터 유효성 검증)
- **문서화:** Markdown (`GUIDE.md`)

## 3. Commands (실행 명령어)
### Python SDK
- 환경 설정: `python -m venv venv && venv\Scripts\activate` (Windows 기준)
- 의존성 설치: `pip install -r requirements.txt`
- 테스트: `pytest tests/ -v`

### Node.js SDK
- 환경 설정 및 설치: `npm install`
- 테스트: `npm test`

## 4. Project Structure (프로젝트 구조)
```text
agent_sdk/
├── SPEC.md                  # 스펙 정의 문서
├── GUIDE.md                 # 에이전트 개발 가이드 문서
├── python/                  # Python SDK
│   ├── cassiopeia_sdk/       # 실제 라이브러리 코드
│   │   ├── __init__.py
│   │   ├── client.py        # Redis Pub/Sub 오케스트라 통신 클라이언트
│   │   └── tools.py         # 도구 호출 규격 처리
│   ├── tests/               # 단위 테스트 (TDD 적용)
│   ├── pytest.ini
│   └── requirements.txt
└── node/                    # Node.js SDK
    ├── src/                 # 실제 라이브러리 코드
    │   ├── index.js         # 진입점
    │   ├── client.js        # Redis Pub/Sub 오케스트라 통신 클라이언트
    │   └── tools.js         # 도구 호출 규격 처리
    ├── tests/               # 단위 테스트 (TDD 적용)
    ├── package.json
    └── jest.config.js
```

## 5. Code Style (코드 스타일)
### Python (예시)
```python
# cassiopeia_sdk/client.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class AgentMessage(BaseModel):
    sender: str
    receiver: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class CassiopeiaClient:
    def __init__(self, agent_id: str, redis_url: str):
        self.agent_id = agent_id
        self.redis_url = redis_url

    async def connect(self):
        pass

    async def send_message(self, action: str, payload: dict) -> bool:
        # Redis 채널 'agent:cassiopeia' 로 메시지 발행
        pass

    async def listen(self):
        # Redis 채널 'agent:{agent_id}' 구독
        pass
```

### Node.js (예시)
```javascript
// src/client.js
class CassiopeiaClient {
    constructor(agentId, redisUrl) {
        this.agentId = agentId;
        this.redisUrl = redisUrl;
    }

    async connect() {
        // Redis 연결
    }

    async sendMessage(action, payload) {
        // Redis 채널 'agent:cassiopeia' 로 메시지 발행
    }
    
    async listen(callback) {
        // Redis 채널 'agent:{agentId}' 구독 및 콜백 실행
    }
}
module.exports = { CassiopeiaClient };
```

## 6. Testing Strategy (테스트 전략)
- **TDD(Test-Driven Development) 원칙 준수:** 항상 실패하는 테스트를 먼저 작성(RED)하고, 이를 통과하는 최소한의 코드를 작성(GREEN)한 뒤 리팩토링(REFACTOR)합니다.
- **Python:** `pytest`를 이용한 단위 테스트. `unittest.mock.AsyncMock`을 활용해 외부 Redis 통신 모킹(Mocking).
- **Node.js:** `jest`를 이용한 단위 테스트. `ioredis` 호출부 모킹.
- **테스트 범위:** 클라이언트 객체 생성, 오케스트라로의 메시지 발행(Publish), 오케스트라로부터의 메시지 구독(Subscribe) 및 도구 호출 요청/응답 규격 파싱.

## 7. Boundaries (경계 및 규칙)
- **Always do:** 테스트 코드를 작성하고 통과 여부를 먼저 확인합니다. 모든 문서 및 주석, 출력물은 한국어로 작성합니다.
- **Ask first:** 프레임워크나 외부 의존성을 크게 추가해야 할 경우. 이번 요구사항은 가벼운 래퍼(Wrapper) 라이브러리에 국한됩니다.
- **Never do:** 시크릿 키나 하드코딩된 Redis URL을 라이브러리에 노출하지 않습니다.

## 8. Success Criteria (성공 기준)
- [ ] `agent_sdk/python`에 Python 패키지가 완성되고 테스트가 모두 통과(GREEN)해야 합니다.
- [ ] `agent_sdk/node`에 Node.js 패키지가 완성되고 테스트가 모두 통과(GREEN)해야 합니다.
- [ ] 노코드 개발자가 쉽게 복사하여 쓸 수 있는 `GUIDE.md` 문서가 명확하게 작성되어야 하며, Redis 통신 설정 및 도구 호출 방법, 컨테이너 환경 적용 방법, 권한 안내가 포함되어야 합니다.

## 9. Open Questions (미결 질문)
- 특이사항 없음. (오케스트라 Redis 규격 파악 완료)
