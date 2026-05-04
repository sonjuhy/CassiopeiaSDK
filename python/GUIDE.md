# Cassiopeia Agent SDK 활용 가이드

외부 프로젝트에서 `cassiopeia-sdk` 하나만 설치해 오케스트라 네트워크에 에이전트를 연결하는 방법을 설명합니다.

---

## 1. 설치

```bash
pip install cassiopeia-sdk
```

의존성: `redis`, `pydantic`, `httpx`

---

## 2. 빠른 시작 — AgentBase

가장 간단한 에이전트 구현입니다. `AgentBase`를 상속하고 `handle()`만 구현하면 됩니다.

```python
import asyncio
import os
from cassiopeia_sdk import AgentBase, AgentMessage

class MyAgent(AgentBase):
    async def handle(self, msg: AgentMessage) -> None:
        # 오케스트라로부터 태스크 수신
        task_id = msg.payload["task_id"]
        content = msg.payload["content"]

        # 처리 후 결과 반환
        await self.send_result(
            task_id=task_id,
            result_data={"answer": f"처리 완료: {content}"},
        )

async def main():
    agent = MyAgent(
        agent_id=os.getenv("AGENT_ID", "my_agent"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    )

    # 오케스트라에 등록 (최초 1회)
    await agent.register(
        orchestra_url=os.getenv("ORCHESTRA_URL", "http://localhost:8000"),
        capabilities=["my_action"],
        api_key=os.getenv("ORCHESTRA_API_KEY", ""),
    )

    # 메시지 수신 루프 시작
    await agent.start()

asyncio.run(main())
```

---

## 3. 오케스트라에 에이전트 등록

오케스트라가 이 에이전트를 인식하고 태스크를 라우팅하려면 등록이 필요합니다.

```python
await agent.register(
    orchestra_url="http://localhost:8000",  # 오케스트라 주소
    capabilities=["search", "summarize"],   # 이 에이전트가 처리할 수 있는 액션 목록
    lifecycle_type="long_running",          # "long_running" | "ephemeral"
    permission_preset="standard",           # "minimal" | "standard" | "trusted"
    allow_llm_access=True,                  # LLM 게이트웨이 사용 여부
    api_key="your-api-key",
)
```

| `lifecycle_type` | 설명 |
|-----------------|------|
| `long_running` | 상시 구동, 헬스체크 대상 |
| `ephemeral` | 요청 시 실행, 헬스체크 없음 |

| `permission_preset` | LLM 접근 기본값 |
|--------------------|----------------|
| `minimal` | 불허 |
| `standard` | 불허 |
| `trusted` | 허용 |

> `allow_llm_access=True`를 명시하면 프리셋 기본값을 덮어씁니다.

---

## 4. 결과 반환

처리가 끝나면 반드시 `send_result()`로 오케스트라에 알려야 합니다.

```python
# 성공
await self.send_result(
    task_id=msg.payload["task_id"],
    result_data={"summary": "처리 결과 내용"},
)

# 실패
await self.send_result(
    task_id=msg.payload["task_id"],
    result_data={},
    error="처리 중 오류 발생",
)
```

`result_data`에 담는 내용은 에이전트 자유입니다. 오케스트라가 사용자에게 전달합니다.

---

## 5. LLM 사용 (게이트웨이)

`allow_llm_access=True`로 등록된 에이전트는 오케스트라의 LLM 게이트웨이를 통해 LLM을 호출할 수 있습니다. 별도의 API 키가 필요 없습니다.

```python
async def handle(self, msg: AgentMessage) -> None:
    response = await self.request_llm(
        messages=[
            {"role": "user", "content": msg.payload["content"]}
        ],
        max_tokens=500,      # 최대 2000
        temperature=0.7,     # 0.0 ~ 1.0
        timeout=30.0,        # 초 단위 응답 대기
    )

    if response["status"] == "completed":
        await self.send_result(msg.payload["task_id"], {"answer": response["content"]})
    elif response["status"] == "rate_limited":
        retry_after = response.get("retry_after", 60)
        # retry_after 초 후 재시도
    elif response["status"] == "unauthorized":
        # allow_llm_access=True 등록 필요
        pass
```

**제약 사항:**
- `role`은 `user`, `assistant`만 허용 (`system` 불허)
- `max_tokens` 최대 2000
- `temperature` 0.0 ~ 1.0

---

## 6. 수신 메시지 구조

`handle()`에 전달되는 `msg` 객체의 구조입니다.

```python
msg.sender    # 보낸 에이전트 (보통 "orchestra")
msg.receiver  # 이 에이전트의 agent_id
msg.action    # 수행할 액션 이름
msg.payload   # 태스크 데이터 (OrchestraTask 형식)
```

`msg.payload`의 주요 필드:

```python
{
    "task_id":    "uuid",          # 필수 — send_result()에 전달
    "session_id": "U1:C1",
    "content":    "사용자 요청 원문",
    "action":     "search",        # 이 에이전트에 요청된 액션
    "params":     {"query": "..."},
    "requester":  {"user_id": "U1", "channel_id": "C1"},
    "source":     "slack",
}
```

---

## 7. HMAC 서명 검증

`AgentBase`는 수신 메시지의 서명을 자동으로 검증합니다. 직접 검증이 필요한 경우:

```python
from cassiopeia_sdk import verify_message, DispatchAuthError

try:
    verify_message(payload, secret="your-hmac-secret")
except DispatchAuthError as e:
    print(f"서명 불일치: {e}")
```

환경변수 `DISPATCH_HMAC_SECRET`을 설정하면 `secret` 인수 없이 자동 적용됩니다. 미설정 시 검증을 건너뜁니다 (하위호환).

---

## 8. 저수준 API — CassiopeiaClient 직접 사용

`AgentBase` 없이 메시지를 직접 다루고 싶은 경우입니다.

```python
from cassiopeia_sdk import CassiopeiaClient, AgentMessage

client = CassiopeiaClient(agent_id="my_agent", redis_url="redis://localhost:6379")
await client.connect()

# 메시지 전송
await client.send_message(
    action="agent_result",
    receiver="orchestra",
    payload={"task_id": "...", "status": "COMPLETED", "result_data": {}},
)

# 메시지 수신
async for msg in client.listen():
    print(msg.action, msg.payload)

await client.disconnect()
```

---

## 9. 타입 참조

```python
from cassiopeia_sdk import AgentResult, OrchestraTask, LLMRequest, LLMResponse
```

| 타입 | 용도 |
|------|------|
| `OrchestraTask` | `msg.payload` 구조 힌트 |
| `AgentResult` | `send_result()` payload 구조 |
| `LLMRequest` | `request_llm()` 파라미터 구조 |
| `LLMResponse` | `request_llm()` 반환값 구조 |

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
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
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
