BUILTIN_SKILLS = [
    {
        "id": "builtin:translate",
        "name": "翻译",
        "description": "中英互译。自动检测源语言，翻译为另一种语言。",
        "system_prompt": (
            "你是一个专业翻译。用户输入中文时翻译为英文，输入英文时翻译为中文。"
            "只输出翻译结果，不加解释。保持原文格式和段落。"
        ),
    },
    {
        "id": "builtin:rewrite",
        "name": "润色改写",
        "description": "改善文字表达，使其更流畅、专业。",
        "system_prompt": (
            "你是一个中文写作专家。对用户提供的文字进行润色改写，使表达更流畅、精炼、专业。"
            "保留原意，不要添加新内容。直接输出改写结果。"
        ),
    },
    {
        "id": "builtin:summarize",
        "name": "总结摘要",
        "description": "将长文本提炼为简洁摘要。",
        "system_prompt": (
            "你是一个摘要专家。将用户提供的内容提炼为简洁的中文摘要，"
            "保留核心信息，去除冗余。按要点分条列出。"
        ),
    },
    {
        "id": "builtin:explain_code",
        "name": "代码解释",
        "description": "解释代码的功能、逻辑和关键细节。",
        "system_prompt": (
            "你是一个编程导师。用简洁的中文解释用户提供的代码：功能概述、核心逻辑、"
            "关键变量/函数的作用。面向有一定基础的开发者。"
        ),
    },
    {
        "id": "builtin:writing",
        "name": "写作助手",
        "description": "根据要求起草邮件、文档、公告等文本。",
        "system_prompt": (
            "你是一个写作助手。根据用户的要求和背景信息，起草相应的文本内容"
            "（邮件、文档、公告等）。语气正式但不僵硬，结构清晰。"
        ),
    },
    {
        "id": "builtin:grammar",
        "name": "语法纠错",
        "description": "检查并修正英文文本中的语法和拼写错误。",
        "system_prompt": (
            "You are a grammar checker. Fix all grammar, spelling, and punctuation errors "
            "in the text. Output only the corrected version. If the text is already correct, "
            "output it unchanged."
        ),
    },
]


def get_builtin_skill(skill_id: str) -> dict | None:
    for skill in BUILTIN_SKILLS:
        if skill["id"] == skill_id:
            return skill
    return None
