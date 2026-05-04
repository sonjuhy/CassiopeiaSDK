const Redis = require('ioredis');
const { z } = require('zod');

// Schema validation matching AgentMessage Python model
// Python 모델의 AgentMessage와 일치하는 스키마 유효성 검사
const AgentMessageSchema = z.object({
  sender: z.string(),
  receiver: z.string(),
  action: z.string(),
  payload: z.record(z.any()).default({}),
  reference_id: z.string().optional().nullable(),
  payload_summary: z.string().optional().nullable(),
  timestamp: z.string().datetime().optional()
});

const CHANNEL_PREFIX = 'agent';

/**
 * Client for interacting with the Cassiopeia messaging bus via Redis.
 * Redis를 통해 Cassiopeia 메시징 버스와 상호작용하는 클라이언트입니다.
 */
class CassiopeiaClient {
  constructor(agentId, redisUrl) {
    this.agentId = agentId;
    this.redisUrl = redisUrl;
    this._pubClient = null;
    this._subClient = null;
  }

  /**
   * Connect to the Redis server.
   * Redis 서버에 연결합니다.
   */
  async connect() {
    this._pubClient = new Redis(this.redisUrl);
    this._subClient = new Redis(this.redisUrl); // Separate connection for subscribing / 구독을 위한 별도 연결

    // Optional: wait for ready event, but ioredis queues commands by default
    // 선택 사항: 준비 이벤트를 기다릴 수 있지만, ioredis는 기본적으로 명령을 큐에 넣습니다.
    return Promise.resolve();
  }

  /**
   * Disconnect from the Redis server.
   * Redis 서버와의 연결을 해제합니다.
   */
  async disconnect() {
    if (this._pubClient) {
      await this._pubClient.quit();
      this._pubClient = null;
    }
    if (this._subClient) {
      await this._subClient.quit();
      this._subClient = null;
    }
  }

  _requireClient() {
    if (!this._pubClient || !this._subClient) {
      throw new Error("Redis connection not initialized. Call connect() first. (Redis 연결이 초기화되지 않았습니다. 먼저 connect()를 호출하세요.)");
    }
  }

  /**
   * Send a message to a specific receiver.
   * 특정 수신자에게 메시지를 전송합니다.
   */
  async sendMessage(action, payload = {}, receiver = 'cassiopeia') {
    this._requireClient();

    const message = {
      sender: this.agentId,
      receiver: receiver,
      action: action,
      payload: payload,
      timestamp: new Date().toISOString()
    };

    try {
      const validatedMessage = AgentMessageSchema.parse(message);
      const channel = `${CHANNEL_PREFIX}:${receiver}`;

      const count = await this._pubClient.publish(channel, JSON.stringify(validatedMessage));
      return count >= 0; // True if published / 발행 성공 시 true 반환
    } catch (error) {
      console.error(`Failed to send message: ${error.message} (메시지 전송 실패: ${error.message})`);
      return false;
    }
  }

  /**
   * Listen for incoming messages targeted at this agentId.
   * 이 에이전트 ID를 대상으로 하는 수신 메시지를 수신 대기합니다.
   */
  async listen(callback) {
    this._requireClient();

    const channel = `${CHANNEL_PREFIX}:${this.agentId}`;

    await this._subClient.subscribe(channel);

    this._subClient.on('message', (receivedChannel, message) => {
      if (receivedChannel === channel) {
        try {
          const parsedData = JSON.parse(message);
          const validatedData = AgentMessageSchema.parse(parsedData);
          callback(validatedData);
        } catch (error) {
          console.error(`Failed to parse or validate received message: ${error.message} (수신된 메시지 파싱 또는 유효성 검사 실패: ${error.message})`);
        }
      }
    });
  }
}

module.exports = { CassiopeiaClient, AgentMessageSchema };