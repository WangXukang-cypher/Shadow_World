import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MockDecision:
    route: str
    argument: str | None
    reply: str


class MockLLMProvider:
    def decide(self, text: str) -> MockDecision:
        query = " ".join(text.strip().split())
        memory_match = re.search(r"(?:请)?(?:记住|记得)(?:一下)?[：,:， ]*(.+)", query)
        if memory_match and memory_match.group(1).strip():
            content = memory_match.group(1).strip("。.!！ ")
            return MockDecision("create_memory", content, f"好的，我记住了：{content}")
        if re.search(r"我的记忆|你记得我什么|你记住了什么", query):
            return MockDecision("list_memories", None, "")
        task_match = re.search(r"(?:提醒我|添加待办|记个待办)[：,:， ]*(.+)", query)
        if task_match and task_match.group(1).strip():
            content = task_match.group(1).strip("。.!！ ")
            if not re.search(
                r"\d{1,2}[:：]\d{2}|今天|明天|后天|周[一二三四五六日天]|星期", content
            ):
                return MockDecision(
                    "clarify_task_time", content, f"什么时候提醒你“{content}”？请给出具体时间。"
                )
            return MockDecision("create_task", content, f"已创建待办：{content}")
        if re.search(r"我的待办|有什么事|待办列表|有哪些待办", query):
            return MockDecision("list_tasks", None, "")
        return MockDecision("chat", None, f"Mock 模式已收到：{query}")
