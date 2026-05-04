# Cassiopeia Agent SDK 활용 가이드

본 가이드는 노코드(No-code) 혹은 바이브 코딩(Vibe-coding) 환경에서 **Cassiopeia Agent**와 통신하고 도구를 호출할 수 있는 에이전트를 개발하기 위한 SDK(Python, Node.js) 사용 설명서입니다.

---

## 1. 목적 (Purpose)
에이전트 개발자가 오케스트라와의 복잡한 비동기 통신 규격(Redis Pub/Sub 통신, 에러 핸들링, 스키마 유효성 검사 등)에 신경 쓰지 않고, **비즈니스 로직과 프롬프트 엔지니어링에만 집중할 수 있도록 돕는 것**이 핵심 목적입니다. 단 하나의 라이브러리를 임포트(Import)하는 것만으로 오케스트라 네트워크에 에이전트를 쉽게 연동할 수 있습니다.

---

## 2. 동작 환경 (Environment)
이 SDK를 사용하는 에이전트는 다양한 환경에서 동작할 수 있습니다. 가장 권장되는 환경은 **Docker 컨테이너**입니다.

- **컨테이너 환경(Docker):** 각 에이전트를 독립적인 컨테이너로 빌드하면 오케스트라와의 네트워크 격리 및 배포가 용이합니다.
- **언어별 지원 런타임:**
  - Python: 3.10 이상
  - Node.js: 18.x 이상 (LTS 권장)
- **네트워크 요구사항:** 에이전트 구동 환경에서 오케스트라가 사용하는 **Redis 서버**(예: `redis://localhost:6379`)로의 접근이 허용되어야 합니다.

---

## 3. 권한 (Permissions)
에이전트가 오케스트라에 접근하고 도구를 호출하려면 적절한 권한 및 식별자가 필요합니다.

1. **에이전트 식별자 (Agent ID):** 오케스트라 서버에서 발급받은 고유한 `agent_id`를 SDK 초기화 시 주입해야 합니다. 이를 통해 오케스트라가 어떤 에이전트로부터 온 메시지인지 식별합니다 (Redis 채널에 매핑됨).
2. **도구 호출 권한:** 각 에이전트는 사용할 수 있는 도구(Tool)의 권한이 사전에 오케스트라 단에 정의되어 있어야 합니다. SDK의 `ToolExecutor`를 통해 로컬 도구를 등록할 수 있지만, 오케스트라의 전역 도구 사용 시 오케스트라 설정에서 해당 `agent_id`의 권한을 확인하세요.
3. **네트워크 및 환경 변수:** 코드 내에 URL이나 식별자를 하드코딩하지 말고 `.env`와 같은 환경 변수를 통해 주입하는 것을 권장합니다 (예: `REDIS_URL`).

---

## 4. 라이브러리 사용 방법 (Usage)

### 4.1. Python SDK

**설치:**
```bash
pip install -r requirements.txt
```

**클라이언트 및 도구 호출 예시:**
```python
import asyncio
import os
from cassiopeia_sdk.client import CassiopeiaClient
from cassiopeia_sdk.tools import Tool, ToolExecutor

async def main():
    # 1. 환경 변수에서 설정 로드
    AGENT_ID = os.getenv("AGENT_ID", "my_awesome_agent")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # 2. 클라이언트 초기화 및 연결
    client = CassiopeiaClient(agent_id=AGENT_ID, redis_url=REDIS_URL)
    await client.connect()

    # 3. 도구(Tool) 등록
    executor = ToolExecutor()

    def get_weather(location: str):
        return f"{location}의 날씨는 맑음입니다."

    weather_tool = Tool(
        name="get_weather",
        description="특정 지역의 현재 날씨를 가져옵니다.",
        parameters={"type": "object", "properties": {"location": {"type": "string"}}}
    )
    executor.register_tool(weather_tool, get_weather)

    # 4. 오케스트라에 메시지 전송 (Publish)
    success = await client.send_message(
        action="start_task", 
        payload={"task": "날씨 확인을 부탁해!"},
        receiver="cassiopeia"
    )

    if success:
        print("메시지 전송을 완료했습니다.")

    # 5. 오케스트라로부터의 메시지 수신 대기 (Subscribe)
    print("수신 대기 중...")
    async for message in client.listen():
        print(f"[{message.sender} 로부터 메시지 수신] 액션: {message.action}")
        
        # (필요 시) 오케스트라의 도구 호출 지시를 받아 도구 실행
        if message.action == "execute_tool":
            tool_name = message.payload.get("tool_name")
            tool_args = message.payload.get("args", {})
            result = executor.execute(tool_name, tool_args)
            print(f"도구 실행 결과: {result}")

    # 6. 연결 종료
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2. Node.js SDK

**설치:**
```bash
npm install
```

**클라이언트 및 도구 호출 예시:**
```javascript
const { CassiopeiaClient } = require('./src/client');
const { ToolExecutor } = require('./src/tools');

async function main() {
  // 1. 환경 변수에서 설정 로드
  const AGENT_ID = process.env.AGENT_ID || 'my_awesome_agent';
  const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

  // 2. 클라이언트 초기화 및 연결
  const client = new CassiopeiaClient(AGENT_ID, REDIS_URL);
  await client.connect();

  // 3. 도구(Tool) 등록
  const executor = new ToolExecutor();

  const weatherTool = {
    name: 'get_weather',
    description: '특정 지역의 현재 날씨를 가져옵니다.',
    parameters: {
      type: 'object',
      properties: { location: { type: 'string' } }
    }
  };

  function getWeather({ location }) {
    return `${location}의 날씨는 맑음입니다.`;
  }

  executor.registerTool(weatherTool, getWeather);

  // 4. 오케스트라에 메시지 전송 (Publish)
  const success = await client.sendMessage('start_task', { task: '날씨 확인을 부탁해!' });
  if (success) {
    console.log('메시지 전송을 완료했습니다.');
  }

  // 5. 오케스트라로부터 메시지 수신 대기 (Subscribe)
  console.log("수신 대기 중...");
  await client.listen(async (message) => {
    console.log(`[${message.sender} 로부터 메시지 수신] 액션: ${message.action}`);
    
    // (필요 시) 오케스트라의 도구 호출 지시를 받아 도구 실행
    if (message.action === 'execute_tool') {
      const toolName = message.payload.tool_name;
      const toolArgs = message.payload.args || {};
      const result = await executor.execute(toolName, toolArgs);
      console.log(`도구 실행 결과: ${result}`);
    }
  });

  // graceful shutdown 처리 등 필요시 disconnect 호출
  // await client.disconnect();
}

main().catch(console.error);
```

---

## 5. 마무리
본 SDK를 통해 복잡한 Redis 통신 계층이나 메시징 스키마(`AgentMessage`)에 얽매이지 않고, 에이전트 본연의 '지능'과 '로직' 설계에 집중하시길 바랍니다. 추가적인 문의나 버그 리포트는 오케스트라 관리 팀을 통해 지원받으실 수 있습니다.
