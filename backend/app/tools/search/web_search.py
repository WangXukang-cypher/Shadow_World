import asyncio

from pydantic import BaseModel, Field

from app.tools.base import AgentTool, SideEffect, ToolContext


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500, description="搜索关键词")
    max_results: int = Field(default=5, ge=1, le=10, description="返回结果数量上限")


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchOutput(BaseModel):
    results: list[SearchResult]
    query: str
    error: str | None = None


class WebSearchTool(AgentTool["WebSearchInput", "WebSearchOutput"]):
    name = "web_search"
    description = (
        "使用DuckDuckGo搜索互联网信息。当用户询问实时信息、新闻、"
        "不确定的事实或需要最新数据时使用。返回标题、链接和摘要。"
    )
    input_model = WebSearchInput
    output_model = WebSearchOutput
    side_effect = SideEffect.READ
    timeout_seconds = 25

    async def execute(self, ctx: ToolContext, params: WebSearchInput) -> WebSearchOutput:
        try:
            raw = await asyncio.to_thread(self._search_sync, params.query, params.max_results)
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                )
                for r in raw
            ]
            return WebSearchOutput(results=results, query=params.query)
        except Exception as exc:  # noqa: BLE001 - search failures are returned as tool output
            return WebSearchOutput(
                results=[],
                query=params.query,
                error=f"搜索失败：{type(exc).__name__}: {str(exc)[:200]}",
            )

    @staticmethod
    def _search_sync(query: str, max_results: int) -> list[dict]:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            return ddgs.text(query, max_results=max_results)
