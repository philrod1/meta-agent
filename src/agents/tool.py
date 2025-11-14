from .base import BaseAgent
from ..tools.registry import get_tool

class ToolAgent(BaseAgent):
    """ Agent that wraps a tool from the registry. """
    def execute(self, context: dict) -> dict:
        """ Execute the tool with provided context. """
        tool_name = self.params.get("tool")
        if not tool_name:
            raise ValueError(f"ToolAgent {self.node_id} missing 'tool' parameter")
        
        fn = get_tool(tool_name)
        args = {k: context.get(k) for k in self.inputs if k in context}
        result = fn(**args)
        
        # Ensure result is a dict
        if not isinstance(result, dict):
            result = {"result": result}
        
        return result