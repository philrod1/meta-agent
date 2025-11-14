""" Data models for workflow representation """

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

@dataclass
class Edge:
    src: str
    dest: str
    when: str = "true" # default boolean condition expression

@dataclass
class Node:
    id: str
    type: str
    summary: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    io_inputs: List[str] = field(default_factory=list)
    io_outputs: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)

@dataclass
class Workflow:
    name: str
    description: str = ""
    preconditions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)