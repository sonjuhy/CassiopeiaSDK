const { CassiopeiaClient } = require('../src/client');
const Redis = require('ioredis');

jest.mock('ioredis');

describe('CassiopeiaClient', () => {
  let mockRedisInstance;

  beforeEach(() => {
    mockRedisInstance = {
      publish: jest.fn().mockResolvedValue(1),
      subscribe: jest.fn().mockResolvedValue(1),
      unsubscribe: jest.fn().mockResolvedValue(1),
      quit: jest.fn().mockResolvedValue('OK'),
      on: jest.fn()
    };
    Redis.mockImplementation(() => mockRedisInstance);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with agentId and redisUrl', () => {
    const client = new CassiopeiaClient('test_agent', 'redis://localhost:6379');
    expect(client.agentId).toBe('test_agent');
    expect(client.redisUrl).toBe('redis://localhost:6379');
  });

  it('should connect and disconnect successfully', async () => {
    const client = new CassiopeiaClient('test_agent', 'redis://localhost:6379');
    
    await client.connect();
    expect(Redis).toHaveBeenCalledWith('redis://localhost:6379');
    expect(client._pubClient).toBe(mockRedisInstance);
    expect(client._subClient).toBe(mockRedisInstance); // Mock returns the same instance for both but in real life they are two

    await client.disconnect();
    expect(mockRedisInstance.quit).toHaveBeenCalledTimes(2); // one for pub, one for sub
  });

  it('should send message successfully', async () => {
    const client = new CassiopeiaClient('test_agent', 'redis://localhost:6379');
    await client.connect();
    
    const success = await client.sendMessage('do_task', { task: 'test' }, 'cassiopeia');
    
    expect(success).toBe(true);
    expect(mockRedisInstance.publish).toHaveBeenCalledTimes(1);
    
    const [channel, messageStr] = mockRedisInstance.publish.mock.calls[0];
    expect(channel).toBe('agent:cassiopeia');
    
    const parsed = JSON.parse(messageStr);
    expect(parsed.sender).toBe('test_agent');
    expect(parsed.receiver).toBe('cassiopeia');
    expect(parsed.action).toBe('do_task');
    expect(parsed.payload).toEqual({ task: 'test' });
    expect(parsed.timestamp).toBeDefined();
  });

  it('should listen to messages on correct channel', async () => {
    const client = new CassiopeiaClient('test_agent', 'redis://localhost:6379');
    await client.connect();

    const mockCallback = jest.fn();
    
    await client.listen(mockCallback);
    
    expect(mockRedisInstance.subscribe).toHaveBeenCalledWith('agent:test_agent');
    
    // Simulate receiving a message
    const messageData = {
      sender: 'cassiopeia',
      receiver: 'test_agent',
      action: 'do_task',
      payload: { task: 'test' },
      timestamp: new Date().toISOString()
    };
    
    // In our mock, on('message') is the second call (first might be on('error'))
    const onMessageCall = mockRedisInstance.on.mock.calls.find(call => call[0] === 'message');
    expect(onMessageCall).toBeDefined();
    
    const messageHandler = onMessageCall[1];
    
    // Execute handler
    messageHandler('agent:test_agent', JSON.stringify(messageData));
    
    expect(mockCallback).toHaveBeenCalledTimes(1);
    expect(mockCallback).toHaveBeenCalledWith(expect.objectContaining({
      sender: 'cassiopeia',
      action: 'do_task'
    }));
  });
});
