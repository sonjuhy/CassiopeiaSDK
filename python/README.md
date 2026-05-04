# Cassiopeia Agent Python SDK

[한국어](#한국어) | [English](#english)

<a name="english"></a>
## English

### Overview
Official Python SDK for the Cassiopeia Agent framework. Install this single library to connect your agent to the orchestra network — no Redis wiring, no message schema boilerplate.

**What you get:**
- `AgentBase` — base class: implement `handle()` and you're done
- `CassiopeiaClient` — low-level Redis Pub/Sub messaging
- `verify_message` — HMAC signature verification for incoming tasks
- Protocol types: `AgentResult`, `OrchestraTask`, `LLMRequest`, `LLMResponse`

### Requirements
- Python 3.10+
- Access to the orchestra's Redis server

### Installation
```bash
pip install cassiopeia-sdk
```

### Quickstart
```python
import asyncio, os
from cassiopeia_sdk import AgentBase, AgentMessage

class MyAgent(AgentBase):
    async def handle(self, msg: AgentMessage) -> None:
        # Call LLM through the orchestra gateway (no API key needed)
        response = await self.request_llm([
            {"role": "user", "content": msg.payload["content"]}
        ])
        await self.send_result(msg.payload["task_id"], {"answer": response["content"]})

async def main():
    agent = MyAgent(os.getenv("AGENT_ID"), os.getenv("REDIS_URL"))
    await agent.register(os.getenv("ORCHESTRA_URL"), capabilities=["my_action"],
                         allow_llm_access=True, api_key=os.getenv("ORCHESTRA_API_KEY"))
    await agent.start()

asyncio.run(main())
```

See [GUIDE.md](GUIDE.md) for the full reference.

---

<a name="한국어"></a>
## 한국어

### 개요
Cassiopeia 에이전트 프레임워크의 공식 Python SDK입니다. 이 라이브러리 하나만 설치하면 오케스트라 네트워크에 에이전트를 연결할 수 있습니다. Redis 연결이나 메시지 스키마를 직접 다룰 필요가 없습니다.

**제공 기능:**
- `AgentBase` — 기본 클래스: `handle()`만 구현하면 동작
- `CassiopeiaClient` — 저수준 Redis Pub/Sub 메시징
- `verify_message` — 수신 메시지 HMAC 서명 검증
- 프로토콜 타입: `AgentResult`, `OrchestraTask`, `LLMRequest`, `LLMResponse`

### 요구사항
- Python 3.10 이상
- 오케스트라의 Redis 서버 접근 가능

### 설치
```bash
pip install cassiopeia-sdk
```

### 빠른 시작
```python
import asyncio, os
from cassiopeia_sdk import AgentBase, AgentMessage

class MyAgent(AgentBase):
    async def handle(self, msg: AgentMessage) -> None:
        # 오케스트라 LLM 게이트웨이 호출 (별도 API 키 불필요)
        response = await self.request_llm([
            {"role": "user", "content": msg.payload["content"]}
        ])
        await self.send_result(msg.payload["task_id"], {"answer": response["content"]})

async def main():
    agent = MyAgent(os.getenv("AGENT_ID"), os.getenv("REDIS_URL"))
    await agent.register(os.getenv("ORCHESTRA_URL"), capabilities=["my_action"],
                         allow_llm_access=True, api_key=os.getenv("ORCHESTRA_API_KEY"))
    await agent.start()

asyncio.run(main())
```

전체 레퍼런스는 [GUIDE.md](GUIDE.md)를 참고하세요.
