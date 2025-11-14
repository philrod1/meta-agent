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
    cls = _AGENT_MAP.get(node.type)
    if not cls:
        raise ValueError(f"Unsupported agent type: {node.type}")
    return cls(node.id, node.params, node.io_inputs, node.io_outputs, node.tests)