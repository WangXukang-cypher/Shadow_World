import base64
from dataclasses import dataclass
from pathlib import Path

from app.application.services import ApplicationService
from app.llm.models import ImageUrlContent, MessageRole, ModelMessage, TextContent

SYSTEM_PROMPT = """## 对话风格
- 用轻松自然的口语聊天，不要像客服或机器人
- 可以用语气词（哈哈、嗯嗯、诶）、适当的emoji
- 回复简短有温度，不要长篇大论除非用户需要
- 记住之前聊过的事情并主动关联
- 用户情绪低落时先共情再建议，不要直接说教
- 严格使用你的人格设定中的称呼和风格

## 核心能力
你会默默记住用户生活中的重要信息，就像一个记性超好的朋友：

### 人物记忆（最重要的特色）
- 当用户提到某个人时（朋友、同事、家人），用 add_person 记录这个人的信息
- 不需要用户说"记住"，只要聊天中自然提到人物信息就记录
- 记录内容包括：姓名、关系、性格、生日、重要事件
- 用户问"小李是谁""上次说的那个同事怎么了"时，用 list_people 查找
- 当用户答应了某人什么事（"我跟小王说好周末请他吃饭"），用 add_commitment 记录社交承诺

### 自动记忆规则
以下情况不需要用户说"记住"，直接用 create_memory 保存：
- 用户的偏好和习惯（"我不吃辣""我习惯晚睡"）
- 重要的生活事件（"我下个月要搬家""我在准备考试"）
- 情绪和状态变化（"最近压力好大""今天心情不错"）
- 对人物的评价和关系动态（"跟老板关系不太好""小李最近升职了"）

不要记录的：
- 一次性的闲聊内容
- 用户明确表示"不要记"的内容
- 过于敏感的隐私信息（密码、证件号等）
- 角色扮演、虚构、游戏内的内容（如游戏战绩、虚拟剧情）——这些是娱乐内容不是用户真实信息
- 只与当前人格角色相关的虚构设定

### 其他能力
- 时间感知：get_current_time（创建提醒前先确认日期）
- 待办提醒：create_task / complete_task / delete_task / list_tasks
- 技能调用：翻译、润色、总结等（invoke_skill）
- 网络搜索：web_search（查实时信息）
- 技能管理：manage_skill（创建/修改自定义技能）

## 社交关怀
- 如果记忆中某人快过生日了，主动提醒用户
- 如果有未完成的社交承诺，适时提醒"对了，你上次说要给xxx的事..."
- 如果用户好几天没提某个重要的人，可以自然地问起

## 自进化规则
- 当连续调用 2 个以上工具完成组合任务时，考虑是否值得保存为技能
- 提议时用自然的口吻："诶我发现你经常让我xxx，要不要我记成一个快捷方式？"

## 重要约束
- 调用工具时必须诚实，不要伪造工具结果
- 记忆可能过时，当前用户说的话优先
- 不要过度热情或频繁追问，给用户空间
- 不要在每句话后面都问"还有什么需要帮忙的吗"
"""


@dataclass(frozen=True)
class TokenBudget:
    context_window: int = 16000
    output_reserve_ratio: float = 0.2
    recent_messages_ratio: float = 0.35
    memories_ratio: float = 0.1

    @property
    def input_budget(self) -> int:
        return int(self.context_window * (1 - self.output_reserve_ratio))

    def section_budget(self, ratio: float) -> int:
        return int(self.input_budget * ratio)


class TokenEstimator:
    @staticmethod
    def estimate(text: str) -> int:
        if not text:
            return 0
        ascii_chars = sum(character.isascii() for character in text)
        non_ascii = len(text) - ascii_chars
        return max(1, ascii_chars // 4 + non_ascii)


class ContextBuilder:
    def __init__(
        self,
        service: ApplicationService,
        budget: TokenBudget | None = None,
        estimator: TokenEstimator | None = None,
        uploads_dir: Path | None = None,
    ):
        self.service = service
        self.budget = budget or TokenBudget()
        self.estimator = estimator or TokenEstimator()
        self.uploads_dir = uploads_dir

    async def build(self, user_id: str, conversation_id: str, persona: dict | None = None) -> list[ModelMessage]:
        _, history = await self.service.get_conversation_with_messages(user_id, conversation_id)
        all_memories = await self.service.list_memories(user_id)

        # 按人格过滤记忆：只加载通用记忆 + 当前人格的记忆
        persona_name = persona.get("name") if persona else None
        memories = []
        for m in all_memories:
            mem_persona = getattr(m, "tags", None) or ""
            if not mem_persona or (persona_name and persona_name in mem_persona):
                memories.append(m)
            elif mem_persona.startswith("persona:") and persona_name and persona_name not in mem_persona:
                continue
            else:
                memories.append(m)

        system_prompt = self._build_system_prompt(persona)
        # 注入用户昵称，让人格知道在和谁说话（引导时用户填写）
        user = await self.service.users.get(user_id)
        if user is not None and user.display_name:
            system_prompt += f"\n\n## 用户信息\n用户昵称：{user.display_name}"
        messages = [ModelMessage(role=MessageRole.SYSTEM, content=system_prompt)]
        memory_lines = []
        for item in memories:
            line = f"[{item.type}] {item.content}"
            if getattr(item, "image_description", None):
                line += f"（附图：{item.image_description}）"
            memory_lines.append(line)
        memory_text = self._fit_texts(
            memory_lines,
            self.budget.section_budget(self.budget.memories_ratio),
        )
        if memory_text:
            messages.append(
                ModelMessage(
                    role=MessageRole.SYSTEM,
                    content="可参考的长期记忆（可能过时）：\n" + "\n".join(memory_text),
                )
            )
        history_budget = self.budget.section_budget(self.budget.recent_messages_ratio)
        selected = []
        used = 0
        for item in reversed(history):
            cost = self.estimator.estimate(item.content)
            if selected and used + cost > history_budget:
                break
            selected.append(item)
            used += cost
        for item in reversed(selected):
            role = MessageRole.USER if item.role == "user" else MessageRole.ASSISTANT
            attachments = getattr(item, "attachments", None)
            if role == MessageRole.USER and attachments:
                content = self._build_multimodal_content(item.content, attachments)
                messages.append(ModelMessage(role=role, content=content))
            else:
                messages.append(ModelMessage(role=role, content=item.content))
        return messages

    def _build_multimodal_content(
        self, text: str, attachments: list[dict]
    ) -> list[TextContent | ImageUrlContent]:
        parts: list[TextContent | ImageUrlContent] = []
        if text:
            parts.append(TextContent(text=text))
        for att in attachments:
            if att.get("mime", "").startswith("image/"):
                image_url = self._resolve_image_url(att)
                if image_url:
                    parts.append(ImageUrlContent(image_url={"url": image_url}))
        return parts if parts else [TextContent(text=text or "")]

    def _resolve_image_url(self, attachment: dict) -> str | None:
        if attachment.get("base64"):
            mime = attachment.get("mime", "image/png")
            return f"data:{mime};base64,{attachment['base64']}"
        if attachment.get("path") and self.uploads_dir:
            path = Path(attachment["path"])
            if path.exists():
                data = base64.b64encode(path.read_bytes()).decode()
                mime = attachment.get("mime", "image/png")
                return f"data:{mime};base64,{data}"
        return None

    def _fit_texts(self, values: list[str], token_budget: int) -> list[str]:
        result: list[str] = []
        used = 0
        for value in values:
            cost = self.estimator.estimate(value)
            if result and used + cost > token_budget:
                break
            result.append(value)
            used += cost
        return result

    def _build_system_prompt(self, persona: dict | None) -> str:
        if persona:
            name = persona.get("name", "小记")
            style = persona.get("style", "轻松自然")
            traits = persona.get("traits", "友好")
            address = persona.get("address_user", "你")
            group_members = persona.get("_group_members")
            if group_members:
                group_line = f"\n\n你在一个群聊中。群成员有：{group_members}。你可以在回复中用 @名字 来邀请其他人参与对话。如果想让别人接话就 @ 他们。"
            else:
                group_line = ""
            persona_block = f"""## 你的身份
你叫"{name}"，这是用户给你起的名字。
- 对话风格：{style}
- 性格特点：{traits}
- 称呼用户为：{address}

严格按照上面的人格设定来对话。如果用户在对话中要求你改名、换风格或换称呼，立即按新要求执行，不要拒绝。{group_line}"""
        else:
            persona_block = """## 你的身份
你叫"小记"，是用户的好朋友。
- 对话风格：平等对话的好朋友，轻松幽默
- 性格特点：真诚、有趣、随和
- 称呼用户为：你"""

        return f"""{persona_block}

{SYSTEM_PROMPT}"""
