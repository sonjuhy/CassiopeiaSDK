import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from cassiopeia_sdk.client import CassiopeiaClient, AgentMessage

def test_client_initialization():
    client = CassiopeiaClient(agent_id="test_agent", redis_url="redis://localhost:6379")
    assert client.agent_id == "test_agent"
    assert client.redis_url == "redis://localhost:6379"

@pytest.mark.asyncio
@patch("cassiopeia_sdk.client.aioredis.from_url")
async def test_connect_and_disconnect(mock_from_url):
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    mock_from_url.return_value = mock_redis
    
    client = CassiopeiaClient(agent_id="test_agent", redis_url="redis://localhost:6379")
    await client.connect()
    
    mock_from_url.assert_called_once_with("redis://localhost:6379", decode_responses=True)
    assert client._client is mock_redis
    
    await client.disconnect()
    mock_redis.aclose.assert_called_once()
    assert client._client is None

@pytest.mark.asyncio
@patch("cassiopeia_sdk.client.aioredis.from_url")
async def test_send_message_success(mock_from_url):
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()
    mock_from_url.return_value = mock_redis
    
    client = CassiopeiaClient(agent_id="test_agent", redis_url="redis://localhost:6379")
    await client.connect()
    
    success = await client.send_message(action="do_task", payload={"task": "test"}, receiver="cassiopeia")
    
    assert success is True
    mock_redis.publish.assert_called_once()
    args, _ = mock_redis.publish.call_args
    assert args[0] == "agent:cassiopeia"
    
    # check if the payload is valid json
    published_msg = json.loads(args[1])
    assert published_msg["sender"] == "test_agent"
    assert published_msg["receiver"] == "cassiopeia"
    assert published_msg["action"] == "do_task"
    assert published_msg["payload"] == {"task": "test"}

@pytest.mark.asyncio
@patch("cassiopeia_sdk.client.aioredis.from_url")
async def test_listen(mock_from_url):
    mock_redis = MagicMock()
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub
    mock_from_url.return_value = mock_redis
    
    # Setup mock pubsub.listen() to yield a message
    mock_msg_data = AgentMessage(
        sender="cassiopeia",
        receiver="test_agent",
        action="execute_tool",
        payload={"tool_name": "get_weather"}
    ).model_dump_json()
    
    async def mock_listen_generator():
        yield {"type": "message", "data": mock_msg_data}
    
    mock_pubsub.listen.return_value = mock_listen_generator()
    
    client = CassiopeiaClient(agent_id="test_agent", redis_url="redis://localhost:6379")
    await client.connect()
    
    messages = []
    gen = client.listen()
    async for msg in gen:
        messages.append(msg)
        break # Just get one for the test
    
    await gen.aclose() # Ensure finally block runs
        
    assert len(messages) == 1
    assert isinstance(messages[0], AgentMessage)
    assert messages[0].sender == "cassiopeia"
    assert messages[0].action == "execute_tool"
    assert messages[0].payload == {"tool_name": "get_weather"}
    
    mock_pubsub.subscribe.assert_called_once_with("agent:test_agent")
    mock_pubsub.unsubscribe.assert_called_once_with("agent:test_agent")
    mock_pubsub.aclose.assert_called_once()
