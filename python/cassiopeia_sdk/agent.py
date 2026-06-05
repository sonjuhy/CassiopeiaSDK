import asyncio, uuid
import httpx
from .client import CassiopeiaClient, AgentMessage
from .auth import verify_message, DispatchAuthError
from .schemas import AgentResult, LLMRequest, LLMResponse


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
        """카시오페아에 처리 결과를 반환합니다."""
        await self.client.send_message(
            action="agent_result",
            receiver="cassiopeia",
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
        model: str | None = None,
    ) -> LLMResponse:
        """
        오케스트라 LLM 게이트웨이를 통해 LLM을 호출합니다.

        Args:
            messages:     role/content 메시지 배열. role은 "user"|"assistant"|"system" 허용.
            max_tokens:   생성 최대 토큰 수 (기본 500, 최대 2000).
            temperature:  샘플링 온도 (0.0~1.0, 기본 0.7).
            timeout:      응답 대기 제한 시간(초).
            model:        사용할 모델 오버라이드. None이면 서버 기본 모델 사용.

        Raises:
            pydantic.ValidationError: 입력값이 유효하지 않을 때 (서버 전송 전 차단)
            TimeoutError:             timeout 초 내에 응답이 없을 때
        """
        task_id = str(uuid.uuid4())
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_llm[task_id] = fut

        # 입력 검증 — ValidationError 발생 시 서버로 전송하지 않음
        request = LLMRequest(
            task_id=task_id,
            agent_id=self.agent_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )

        await self.client.send_message(
            action="llm_call",
            receiver="cassiopeia",
            payload=request.model_dump(exclude_none=True),
        )

        raw: dict = await asyncio.wait_for(fut, timeout=timeout)
        return LLMResponse.model_validate(raw)

    async def register(
        self,
        cassiopeia_url: str,
        capabilities: list[str],
        lifecycle_type: str = "long_running",
        permission_preset: str = "standard",
        allow_llm_access: bool = False,
        api_key: str = "",
        nlu_description: str = "",
        params_schema: dict | None = None,
        default_timeout: int | None = None,
        routing: dict | None = None,
    ) -> bool:
        """
        카시오페아 HTTP API로 이 에이전트를 등록합니다.
        cassiopeia_url: 카시오페아 주소 (예: "http://localhost:8000")

        자기 기술(self-describing) 메타데이터 — 지휘자가 에이전트 이름을 코드에서
        특별 취급하지 않고 동일하게 다루도록, 에이전트가 자신의 능력을 선언합니다.
        모두 선택 사항이며, 생략하면 본문에서 빠집니다(하위호환).

            nlu_description: NLU 라우팅용 자연어 설명 (예: "- my_agent: 날씨 조회").
            params_schema:   지휘자가 LLM에 노출할 액션/파라미터 가이드(dict).
                             예: {"action": "get_weather", "params": {"location": "도시명"}}
            default_timeout: 이 에이전트 작업의 기본 타임아웃(초).
            routing:         라우팅 메타데이터. 예: 커뮤니케이션 에이전트라면
                             {"role": "communication", "platforms": ["slack", "discord"]}.
        """
        body: dict = {
            "agent_name": self.agent_id,
            "capabilities": capabilities,
            "lifecycle_type": lifecycle_type,
            "permission_preset": permission_preset,
            "allow_llm_access": allow_llm_access,
        }
        if nlu_description:
            body["nlu_description"] = nlu_description
        if params_schema is not None:
            body["params_schema"] = params_schema
        if default_timeout is not None:
            body["default_timeout"] = default_timeout
        if routing is not None:
            body["routing"] = routing

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{cassiopeia_url}/agents",
                json=body,
                headers={"X-API-Key": api_key},
            )
            return resp.status_code == 201

    def _resolve_llm(self, payload: dict) -> None:
        task_id = payload.get("task_id")
        fut = self._pending_llm.pop(task_id, None)
        if fut and not fut.done():
            fut.set_result(payload)
