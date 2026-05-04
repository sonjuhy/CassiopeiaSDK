from pydantic import BaseModel
from typing import Dict, Any, Callable

class Tool(BaseModel):
    """
    Definition of a tool that the agent can execute.
    에이전트가 실행할 수 있는 도구의 정의입니다.
    """
    name: str
    description: str
    parameters: Dict[str, Any]

class ToolExecutor:
    """
    Manages registration and execution of tools.
    도구의 등록 및 실행을 관리합니다.
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._callbacks: Dict[str, Callable] = {}

    def register_tool(self, tool: Tool, callback: Callable):
        """
        Register a tool with its handler function.
        도구와 해당 핸들러 함수를 등록합니다.
        """
        self._tools[tool.name] = tool
        self._callbacks[tool.name] = callback

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a registered tool by name with the given parameters.
        이름으로 등록된 도구를 주어진 매개변수와 함께 실행합니다.
        """
        if tool_name not in self._callbacks:
            raise ValueError(f"Tool '{tool_name}' not found. (도구 '{tool_name}'을(를) 찾을 수 없습니다.)")

        # In a real implementation, you might want to validate parameters against tool.parameters schema
        # 실제 구현에서는 tool.parameters 스키마를 사용하여 parameters의 유효성을 검사할 수 있습니다.
        return self._callbacks[tool_name](**parameters)

    def get_registered_tools(self) -> list[Dict[str, Any]]:
        """
        Return a list of all registered tools.
        등록된 모든 도구의 목록을 반환합니다.
        """
        return [tool.model_dump() for tool in self._tools.values()]
