'use strict';

const { AgentBase } = require('../src/agent');

jest.mock('../src/client');
jest.mock('../src/schemas', () => {
  const actual = jest.requireActual('../src/schemas');
  return actual;
});

function makeAgent() {
  const agent = new AgentBase('my_agent', 'redis://localhost:6379');
  agent.client.connect = jest.fn().mockResolvedValue();
  agent.client.sendMessage = jest.fn().mockImplementation(async (action, payload) => {
    if (action === 'llm_call') {
      setImmediate(() =>
        agent._resolveLlm({
          task_id: payload.task_id,
          status: 'completed',
          content: '응답',
          model: payload.model || null,
        })
      );
    }
    return true;
  });
  return agent;
}

describe('AgentBase.requestLlm — model 파라미터', () => {

  it('model 미지정 시 payload에 model 키 없음', async () => {
    const agent = makeAgent();
    await agent.requestLlm([{ role: 'user', content: '안녕' }]);
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload).not.toHaveProperty('model');
  });

  it('model 지정 시 payload에 model 키 포함', async () => {
    const agent = makeAgent();
    await agent.requestLlm([{ role: 'user', content: '안녕' }], { model: 'gemini-1.5-pro' });
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload.model).toBe('gemini-1.5-pro');
  });

  it('system role 메시지를 payload에 포함', async () => {
    const agent = makeAgent();
    const messages = [
      { role: 'system', content: '너는 전문가야' },
      { role: 'user', content: '요약해줘' },
    ];
    await agent.requestLlm(messages);
    const payload = agent.client.sendMessage.mock.calls[0][1];
    expect(payload.messages[0].role).toBe('system');
  });

  it('유효하지 않은 model로 호출 시 ZodError — 서버 전송 전 차단', async () => {
    const agent = makeAgent();
    await expect(
      agent.requestLlm([{ role: 'user', content: '안녕' }], { model: 'invalid model!' })
    ).rejects.toThrow();
    expect(agent.client.sendMessage).not.toHaveBeenCalled();
  });

  it('max_tokens 범위 초과 시 ZodError — 서버 전송 전 차단', async () => {
    const agent = makeAgent();
    await expect(
      agent.requestLlm([{ role: 'user', content: '안녕' }], { maxTokens: 9999 })
    ).rejects.toThrow();
    expect(agent.client.sendMessage).not.toHaveBeenCalled();
  });

  it('잘못된 role 시 ZodError — 서버 전송 전 차단', async () => {
    const agent = makeAgent();
    await expect(
      agent.requestLlm([{ role: 'bad_role', content: '안녕' }])
    ).rejects.toThrow();
    expect(agent.client.sendMessage).not.toHaveBeenCalled();
  });

  it('model=null로 호출 시 하위 호환 유지', async () => {
    const agent = makeAgent();
    const result = await agent.requestLlm(
      [{ role: 'user', content: '안녕' }],
      { maxTokens: 500, temperature: 0.7 }
    );
    expect(result.status).toBe('completed');
    expect(agent.client.sendMessage).toHaveBeenCalledTimes(1);
  });
});
