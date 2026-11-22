from .executor import ToolExecutor
from .memory.create_memory import CreateMemoryTool
from .memory.delete_memory import DeleteMemoryTool
from .memory.list_memories import ListMemoriesTool
from .memory.update_memory import UpdateMemoryTool
from .people.add_commitment import AddCommitmentTool
from .people.add_person import AddPersonTool
from .people.list_people import ListPeopleTool
from .registry import ToolRegistry
from .search.web_search import WebSearchTool
from .skills.invoke_skill import InvokeSkillTool
from .skills.list_skills import ListSkillsTool
from .skills.manage_skill import ManageSkillTool
from .tasks.complete_task import CompleteTaskTool
from .tasks.create_task import CreateTaskTool
from .tasks.delete_task import DeleteTaskTool
from .tasks.list_tasks import ListTasksTool
from .utility import GetCurrentTimeTool


def build_tooling() -> tuple[ToolRegistry, ToolExecutor]:
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    registry.register(CreateMemoryTool())
    registry.register(ListMemoriesTool())
    registry.register(UpdateMemoryTool())
    registry.register(DeleteMemoryTool())
    registry.register(CreateTaskTool())
    registry.register(ListTasksTool())
    registry.register(CompleteTaskTool())
    registry.register(DeleteTaskTool())
    registry.register(AddPersonTool())
    registry.register(ListPeopleTool())
    registry.register(AddCommitmentTool())
    registry.register(ListSkillsTool())
    registry.register(ManageSkillTool())
    registry.register(InvokeSkillTool())
    registry.register(WebSearchTool())
    return registry, ToolExecutor(registry)
