""" Execution context for workflow agents. """
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class ExecutionContext:
    data: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def set_many(self, kv: Dict[str, Any]):
        self.data.update(kv)