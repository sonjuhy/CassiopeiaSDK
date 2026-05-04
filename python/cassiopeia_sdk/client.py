import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
import redis.asyncio as aioredis

_CHANNEL_PREFIX = "agent"

class AgentMessage(BaseModel):
    """
    Standard message format for communication between agents.
    에이전트 간 통신을 위한 표준 메시지 형식입니다.
    """
    model_config = ConfigDict(frozen=True)

    sender: str
    receiver: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    reference_id: Optional[str] = None
    payload_summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_json(self) -> str:
        """
        Serialize to JSON string.
        JSON 문자열로 직렬화합니다.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """
        Deserialize from JSON string.
        JSON 문자열에서 역직렬화합니다.
        """
        return cls.model_validate_json(json_str)

class CassiopeiaClient:
    """
    Client for interacting with the Cassiopeia messaging bus via Redis.
    Redis를 통해 Cassiopeia 메시징 버스와 상호작용하는 클라이언트입니다.
    """
    def __init__(self, agent_id: str, redis_url: str):
        self.agent_id = agent_id
        self.redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None

    async def connect(self):
        """
        Connect to the Redis server.
        Redis 서버에 연결합니다.
        """
        self._client = aioredis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        """
        Disconnect from the Redis server.
        Redis 서버와의 연결을 해제합니다.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis connection not initialized. Call connect() first. (Redis 연결이 초기화되지 않았습니다. 먼저 connect()를 호출하세요.)")
        return self._client

    async def send_message(self, action: str, payload: Dict[str, Any] = None, receiver: str = "cassiopeia") -> bool:      
        """
        Send a message to a specific receiver (default: cassiopeia).
        특정 수신자(기본값: cassiopeia)에게 메시지를 전송합니다.
        """
        if payload is None:
            payload = {}

        client = self._require_client()
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            action=action,
            payload=payload
        )
        channel = f"{_CHANNEL_PREFIX}:{receiver}"
        try:
            await client.publish(channel, message.to_json())
            return True
        except Exception:
            return False

    async def listen(self) -> AsyncIterator[AgentMessage]:
        """
        Listen for incoming messages targeted at this agent_id.
        이 에이전트 ID를 대상으로 하는 수신 메시지를 수신 대기합니다.
        """
        client = self._require_client()
        channel = f"{_CHANNEL_PREFIX}:{self.agent_id}"
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw.get("type") == "message":
                    yield AgentMessage.from_json(raw["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
