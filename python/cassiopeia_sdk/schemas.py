from typing import TypedDict, Literal, Any


# 오케스트라로 결과 반환 시
class AgentResult(TypedDict):
    task_id: str
    agent: str
    status: Literal["COMPLETED", "FAILED", "PROCESSING"]
    result_data: dict[str, Any]
    error: str | None
    usage_stats: dict[str, Any]


# 오케스트라에서 수신하는 태스크
class OrchestraTask(TypedDict):
    task_id: str
    session_id: str
    requester: dict  # {user_id, channel_id}
    content: str
    source: str  # "slack" | "api" | ...
    action: str
    params: dict[str, Any]


# LLM 게이트웨이 요청
class LLMRequest(TypedDict):
    task_id: str
    agent_id: str
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    max_tokens: int  # 1~2000
    temperature: float  # 0.0~1.0


# LLM 게이트웨이 응답
class LLMResponse(TypedDict):
    task_id: str
    status: Literal["completed", "rate_limited", "unauthorized", "error"]
    content: str
    usage: dict  # {prompt_tokens, completion_tokens, total_tokens}
    error: str | None
    retry_after: int | None  # rate_limited일 때만
