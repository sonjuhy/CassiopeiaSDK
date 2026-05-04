'use strict';

const { AgentBase } = require('../src/agent');
const { CassiopeiaClient } = require('../src/client');

jest.mock('../src/client');

function makeAgent() {
  const agent = new AgentBase('my_agent', 'redis://localhost:6379');
  agent.client.connect = jest.fn().mockResolvedValue();
  agent.client.sendMessage = jest.fn().mockResolvedValue(true);
  agent.client.listen = jest.fn().mockResolvedValue();
  return agent;
}

// ── sendResult ────────────────────────────────────────────────────────────────

describe('AgentBase.sendResult', () => {
  it('오케스트라로 결과를 전송합니다', async () => {
    const agent = makeAgent();
    await agent.sendResult('task-1', { answer: 'ok' });

    expect(agent.client.sendMessage).toHaveBeenCalledWith(
      'agent_result',
      expect.objectContaining({ task_id: 'task-1', status: 'COMPLETED' }),
      'orchestra'
    );
  });

  it('error 없으면 COMPLETED 상태입니다', async () => {
    const agent = makeAgent();
    await agent.sendResult('task-1', {});
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload.status).toBe('COMPLETED');
    expect(payload.error).toBeNull();
  });

  it('error 있으면 FAILED 상태입니다', async () => {
    const agent = makeAgent();
    await agent.sendResult('task-1', {}, '뭔가 잘못됨');
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload.status).toBe('FAILED');
    expect(payload.error).toBe('뭔가 잘못됨');
  });

  it('task_id가 payload에 포함됩니다', async () => {
    const agent = makeAgent();
    await agent.sendResult('task-xyz', { data: 1 });
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload.task_id).toBe('task-xyz');
  });
});

// ── requestLlm ────────────────────────────────────────────────────────────────

describe('AgentBase.requestLlm', () => {
  it('오케스트라로 llm_call을 전송합니다', async () => {
    const agent = makeAgent();

    // 즉시 llm_result 응답 시뮬레이션
    agent.client.sendMessage.mockImplementation(async (action, payload) => {
      if (action === 'llm_call') {
        setImmediate(() => agent._resolveLlm({
          task_id: payload.task_id,
          status: 'completed',
          content: '테스트 응답',
        }));
      }
      return true;
    });

    const result = await agent.requestLlm([{ role: 'user', content: '안녕' }]);

    expect(agent.client.sendMessage).toHaveBeenCalledWith(
      'llm_call',
      expect.objectContaining({ agent_id: 'my_agent' }),
      'orchestra'
    );
    expect(result.content).toBe('테스트 응답');
  });

  it('타임아웃 시 에러를 던집니다', async () => {
    const agent = makeAgent();
    await expect(
      agent.requestLlm([{ role: 'user', content: '질문' }], { timeout: 10 })
    ).rejects.toThrow('타임아웃');
  });

  it('task_id가 응답과 일치합니다', async () => {
    const agent = makeAgent();
    let capturedTaskId;

    agent.client.sendMessage.mockImplementation(async (action, payload) => {
      if (action === 'llm_call') {
        capturedTaskId = payload.task_id;
        setImmediate(() => agent._resolveLlm({
          task_id: payload.task_id,
          status: 'completed',
          content: '응답',
        }));
      }
      return true;
    });

    const result = await agent.requestLlm([{ role: 'user', content: 'hi' }]);
    expect(result.task_id).toBe(capturedTaskId);
  });
});

// ── _resolveLlm ───────────────────────────────────────────────────────────────

describe('AgentBase._resolveLlm', () => {
  it('대기 중인 Future를 해소합니다', () => {
    const agent = makeAgent();
    let resolved;
    agent._pendingLlm.set('task-abc', {
      resolve: (v) => { resolved = v; },
      reject: jest.fn(),
      timer: setTimeout(() => {}, 10000),
    });

    agent._resolveLlm({ task_id: 'task-abc', content: 'ok' });
    expect(resolved.content).toBe('ok');
    expect(agent._pendingLlm.has('task-abc')).toBe(false);
  });

  it('알 수 없는 task_id는 무시합니다', () => {
    const agent = makeAgent();
    expect(() => agent._resolveLlm({ task_id: 'unknown', content: 'orphan' })).not.toThrow();
  });
});

// ── register ──────────────────────────────────────────────────────────────────

describe('AgentBase.register', () => {
  it('오케스트라 /agents에 POST합니다', async () => {
    const agent = makeAgent();
    global.fetch = jest.fn().mockResolvedValue({ status: 201 });

    const result = await agent.register('http://localhost:8000', {
      capabilities: ['my_action'],
      apiKey: 'test-key',
    });

    expect(result).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/agents',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('등록 실패 시 false를 반환합니다', async () => {
    const agent = makeAgent();
    global.fetch = jest.fn().mockResolvedValue({ status: 400 });

    const result = await agent.register('http://localhost:8000', { capabilities: [] });
    expect(result).toBe(false);
  });
});
