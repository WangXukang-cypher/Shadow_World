from app.llm.models import ToolDefinition

from .base import AgentTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"tool not found: {name}") from exc

    def definitions(self, allowed: set[str] | None = None) -> list[ToolDefinition]:
        tools = self._tools.values()
        if allowed is not None:
            tools = [tool for tool in tools if tool.name in allowed]
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.input_model.model_json_schema(),
            )
            for tool in tools
        ]
