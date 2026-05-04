import pytest
from cassiopeia_sdk.tools import Tool, ToolExecutor

def test_tool_definition():
    tool = Tool(
        name="get_weather",
        description="Get current weather",
        parameters={"type": "object", "properties": {"location": {"type": "string"}}}
    )
    assert tool.name == "get_weather"
    assert "location" in tool.parameters["properties"]

def test_tool_executor():
    def mock_weather(location: str):
        return f"Weather in {location} is sunny"
    
    executor = ToolExecutor()
    executor.register_tool(
        Tool(name="get_weather", description="Get weather", parameters={"type": "object"}),
        mock_weather
    )
    
    result = executor.execute("get_weather", {"location": "Seoul"})
    assert result == "Weather in Seoul is sunny"

def test_tool_executor_not_found():
    executor = ToolExecutor()
    with pytest.raises(ValueError):
        executor.execute("unknown_tool", {})
