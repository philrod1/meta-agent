""" Factory for creating agent instances based on node type. """
from typing import Dict, Type
from ..agents.base import BaseAgent
from ..agents.tool import ToolAgent
from ..agents.router import RouterAgent
from ..agents.approval import ApprovalAgent
_AGENT_MAP: Dict[str, Type[BaseAgent]] = {
    "tool": ToolAgent,
    "router": RouterAgent,
    "approval": ApprovalAgent,
    # "llm": LLMAgent, ...
}


def make_agent(node):
    # Handle special-case agent types that would cause import cycles by importing lazily
    if node.type == "workflow_call":
        from ..agents.workflow_call import WorkflowCallAgent
        cls = WorkflowCallAgent
    else:
        cls = _AGENT_MAP.get(node.type)

    if not cls:
        raise ValueError(f"Unsupported agent type: {node.type}")

    # instantiate and track creation count
    instance = cls(node.id, node.params, node.io_inputs, node.io_outputs, node.tests)
    try:
        # increment global counter if present
        globals()['_AGENT_CREATION_COUNT'] += 1
    except Exception:
        globals()['_AGENT_CREATION_COUNT'] = 1

    return instance


def get_agent_creation_count() -> int:
    """Return the number of agent instances created so far."""
    return globals().get('_AGENT_CREATION_COUNT', 0)


def reset_agent_creation_count() -> None:
    """Reset the agent creation counter to zero."""
    globals()['_AGENT_CREATION_COUNT'] = 0


def increment_agent_creation_count(n: int = 1) -> None:
    """Increment the global agent creation counter by n (default 1)."""
    try:
        globals()['_AGENT_CREATION_COUNT'] += n
    except Exception:
        globals()['_AGENT_CREATION_COUNT'] = n