""" Load and validate Workflow from YAML. """

import yaml
from .models import Workflow, Node, Edge

def load_workflow(yaml_text: str) -> Workflow:
    """
    Load a Workflow from a YAML string.
    """
    data = yaml.safe_load(yaml_text)

    # basic validation
    for key in ["name", "inputs", "nodes", "edges", "success_criteria", "failure_conditions"]:
        if key not in data:
            raise ValueError(f"Missing required top-level field: {key}")

    nodes = []
    for node_data in data.get("nodes", []):
        nodes.append(Node(
            id=node_data["id"],
            type=node_data["type"],
            summary=node_data.get("summary", ""),
            params=node_data.get("params", {}),
            io_inputs=node_data.get("io", {}).get("inputs", []),
            io_outputs=node_data.get("io", {}).get("outputs", []),
            tests=node_data.get("tests", []),
        ))
    
    edges = []
    for edge_data in data.get("edges", []):
        edges.append(Edge(
            src=edge_data["from"],
            dest=edge_data["to"],
            when=edge_data.get("when", "true"),
        ))

    workflow = Workflow(
        name=data["name"],
        description=data.get("description", ""),
        preconditions=data.get("preconditions", []),
        success_criteria=data.get("success_criteria", []),
        failure_conditions=data.get("failure_conditions", []),
        inputs=data.get("inputs", []),
        outputs=data.get("outputs", []),
        nodes=nodes,
        edges=edges,
    )
    _validate_workflow(workflow)

    return workflow

def _validate_workflow(workflow: Workflow) -> None:
    """
    Cyclic check on DAG (DFS)
    """
    node_ids = {node.id for node in workflow.nodes}
    indegree = {node.id: 0 for node in workflow.nodes}
    
    for edge in workflow.edges:
        if edge.src not in node_ids or edge.dest not in node_ids:
            raise ValueError(f"Edge references unknown node: {edge.src} -> {edge.dest}")
        indegree[edge.dest] += 1
    
    queue = [node_id for node_id, deg in indegree.items() if deg == 0]
    visited = 0
    adjacency = {node.id: [] for node in workflow.nodes}
    for edge in workflow.edges:
        adjacency[edge.src].append(edge.dest)

    while queue:
        current = queue.pop(0)
        visited += 1
        for neighbor in adjacency[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    
    if visited != len(workflow.nodes):
        raise ValueError("Cycle detected in Workflow DAG.")