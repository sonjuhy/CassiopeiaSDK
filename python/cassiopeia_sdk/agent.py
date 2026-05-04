import asyncio, uuid
import httpx
from .client import CassiopeiaClient, AgentMessage
from .auth import verify_message, DispatchAuthError
from .schemas import AgentResult, LLMResponse


class AgentBase:
    """
    외부 에이전트 기본 클래스.

    Usage:
        class MyAgent(AgentBase):
            async def handle(self, msg: AgentMessage) -> None:
                result = do_work(msg.payload)
                await self.send_result(msg.payload["task_id"], result)

        agent = MyAgent("my_agent", redis_url="redis://...")
        await agent.start()
    """

    def __init__(self, agent_id: str, redis_url: str) -> None:
        self.agent_id = agent_id
        self.client = CassiopeiaClient(agent_id, redis_url)
        self._pending_llm: dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        """연결 후 메시지 수신 루프 시작. Ctrl+C로 종료."""
        await self.client.connect()
        try:
            async for msg in self.client.listen():
                # LLM 게이트웨이 응답은 내부 처리
                if msg.action == "llm_result":
                    self._resolve_llm(msg.payload)
                    continue
                # HMAC 검증
                try:
                    verify_message(dict(msg.payload))
                except DispatchAuthError:
                    continue  # 무효 메시지 무시
                asyncio.create_task(self.handle(msg))
        finally:
            await self.client.disconnect()

    async def handle(self, msg: AgentMessage) -> None:
        """수신 메시지 처리. 반드시 override해야 합니다."""
        raise NotImplementedError

    async def send_result(
        self,
        task_id: str,
        result_data: dict,
        error: str | None = None,
    ) -> None:
        """오케스트라에 처리 결과를 반환합니다."""
        await self.client.send_message(
            action="agent_result",
            receiver="orchestra",
            payload=AgentResult(
                task_id=task_id,
                agent=self.agent_id,
                status="COMPLETED" if error is None else "FAILED",
                result_data=result_data,
                error=error,
                usage_stats={},
            ),
        )

    async def request_llm(
        self,
        messages: list[dict],
        max_tokens: int = 500,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """
        오케스트라 LLM 게이트웨이를 통해 LLM을 호출합니다.

        Raises:
            TimeoutError: timeout 초 내에 응답이 없을 때
        """
        task_id = str(uuid.uuid4())
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_llm[task_id] = fut

        await self.client.send_message(
            action="llm_call",
            receiver="orchestra",
            payload={
                "task_id": task_id,
                "agent_id": self.agent_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        return await asyncio.wait_for(fut, timeout=timeout)

    async def register(
        self,
        orchestra_url: str,
        capabilities: list[str],
        lifecycle_type: str = "long_running",
        permission_preset: str = "standard",
        allow_llm_access: bool = False,
        api_key: str = "",
    ) -> bool:
        """
        오케스트라 HTTP API로 이 에이전트를 등록합니다.
        orchestra_url: 오케스트라 주소 (예: "http://localhost:8000")
        """
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{orchestra_url}/agents",
                json={
                    "agent_name": self.agent_id,
                    "capabilities": capabilities,
                    "lifecycle_type": lifecycle_type,
                    "permission_preset": permission_preset,
                    "allow_llm_access": allow_llm_access,
                },
                headers={"X-API-Key": api_key},
            )
            return resp.status_code == 201

    def _resolve_llm(self, payload: dict) -> None:
        task_id = payload.get("task_id")
        fut = self._pending_llm.pop(task_id, None)
        if fut and not fut.done():
            fut.set_result(payload)
