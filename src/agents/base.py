from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseAgent(ABC):
    """ Abstract base class for all agents. """

    def __init__(self, node_id: str, params: Dict[str, Any], 
                 inputs: List[str], outputs: List[str], tests: List[str] = []):
        self.node_id = node_id
        self.params = params
        self.inputs = inputs
        self.outputs = outputs
        self.tests = tests

    def plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a plan based on the provided context.
        """
        return {}
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main logic.  Must be implemented by subclasses.
        """
        pass

    def dry_run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate execution without side effects.
        """
        return {out: f"{self.node_id}:{out}:DRY" for out in self.outputs}