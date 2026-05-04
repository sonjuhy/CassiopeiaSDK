# Cassiopeia Agent Python SDK

[한국어](#한국어) | [English](#english)

<a name="english"></a>
## English

### Overview
This is the official Python SDK for the Cassiopeia Agent framework. It provides an asynchronous, easy-to-use interface to connect to the Cassiopeia messaging bus (via Redis Pub/Sub), register tools, and communicate with other agents.

### Installation
```bash
pip install cassiopeia-sdk
```

### Usage Example
```python
import asyncio
from cassiopeia_sdk.client import CassiopeiaClient
from cassiopeia_sdk.tools import Tool, ToolExecutor

async def main():
    # 1. Initialize the client
    client = CassiopeiaClient(agent_id="my_agent", redis_url="redis://localhost:6379")
    
    # 2. Define and register a custom tool
    executor = ToolExecutor()
    
    async def hello_handler(args):
        return f"Hello, {args.get('name')}!"
        
    my_tool = Tool(
        name="say_hello", 
        description="Greets the user", 
        parameters={"type": "object", "properties": {"name": {"type": "string"}}}
    )
    executor.register_tool(my_tool, hello_handler)
    
    # 3. Connect to the messaging bus
    await client.connect()
    
    # 4. Send a message
    await client.send_message(action="do_task", payload={"task": "test"})

if __name__ == "__main__":
    asyncio.run(main())
```

---

<a name="한국어"></a>
## 한국어

### 개요
Cassiopeia 에이전트 프레임워크를 위한 공식 Python SDK입니다. 비동기 기반의 쉬운 인터페이스를 통해 Cassiopeia 메시징 버스(Redis Pub/Sub)에 연결하고, 도구(Tool)를 등록하며, 다른 에이전트와 통신할 수 있도록 지원합니다.

### 설치 방법
```bash
pip install cassiopeia-sdk
```

### 사용 예시
```python
import asyncio
from cassiopeia_sdk.client import CassiopeiaClient
from cassiopeia_sdk.tools import Tool, ToolExecutor

async def main():
    # 1. 클라이언트 초기화
    client = CassiopeiaClient(agent_id="my_agent", redis_url="redis://localhost:6379")
    
    # 2. 커스텀 도구 등록
    executor = ToolExecutor()
    
    async def hello_handler(args):
        return f"안녕하세요, {args.get('name')}님!"
        
    my_tool = Tool(
        name="say_hello", 
        description="사용자에게 인사합니다", 
        parameters={"type": "object", "properties": {"name": {"type": "string"}}}
    )
    executor.register_tool(my_tool, hello_handler)
    
    # 3. 메시징 버스에 연결
    await client.connect()
    
    # 4. 메시지 전송
    await client.send_message(action="do_task", payload={"task": "test"})

if __name__ == "__main__":
    asyncio.run(main())
```