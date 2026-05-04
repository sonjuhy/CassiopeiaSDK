# Cassiopeia Agent Node.js SDK

[한국어](#한국어) | [English](#english)

<a name="english"></a>
## English

### Overview
This is the official Node.js SDK for the Cassiopeia Agent framework. It provides an easy-to-use interface to connect to the Cassiopeia messaging bus (via Redis Pub/Sub), register tools, and communicate with other agents.

### Installation
```bash
npm install cassiopeia-sdk
```

### Usage Example
```javascript
const { CassiopeiaClient, ToolExecutor } = require('cassiopeia-sdk');

async function main() {
  // 1. Initialize the client
  const client = new CassiopeiaClient('my_agent_id', 'redis://localhost:6379');

  // 2. Define and register a custom tool
  const executor = new ToolExecutor();
  const myTool = {
      name: 'say_hello',
      description: 'Greets the user',
      parameters: { type: 'object', properties: { name: { type: 'string' } } }
  };
  
  executor.registerTool(myTool, async (args) => {
      return `Hello, ${args.name}!`;
  });

  // 3. Connect to the messaging bus
  await client.connect();

  // 4. Send a message to the Cassiopeia orchestra
  await client.sendMessage('task_request', { task: 'Analyze data' });
}

main().catch(console.error);
```

---

<a name="한국어"></a>
## 한국어

### 개요
Cassiopeia 에이전트 프레임워크를 위한 공식 Node.js SDK입니다. Cassiopeia 메시징 버스(Redis Pub/Sub 기반)에 연결하고, 도구(Tool)를 등록하며, 다른 에이전트와 통신할 수 있는 사용하기 쉬운 인터페이스를 제공합니다.

### 설치 방법
```bash
npm install cassiopeia-sdk
```

### 사용 예시
```javascript
const { CassiopeiaClient, ToolExecutor } = require('cassiopeia-sdk');

async function main() {
  // 1. 클라이언트 초기화
  const client = new CassiopeiaClient('my_agent_id', 'redis://localhost:6379');

  // 2. 커스텀 도구 등록
  const executor = new ToolExecutor();
  const myTool = {
      name: 'say_hello',
      description: '사용자에게 인사합니다',
      parameters: { type: 'object', properties: { name: { type: 'string' } } }
  };
  
  executor.registerTool(myTool, async (args) => {
      return `안녕하세요, ${args.name}님!`;
  });

  // 3. 메시징 버스에 연결
  await client.connect();

  // 4. Cassiopeia 오케스트라로 메시지 전송
  await client.sendMessage('task_request', { task: '데이터 분석' });
}

main().catch(console.error);
```