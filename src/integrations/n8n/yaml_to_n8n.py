import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

import yaml

from src.workflow.schema import WorkflowSpec, validate_workflow


def _auto_layout(nodes) -> Dict[str, Tuple[int, int]]:
    """
    Very simple layout: put nodes in a vertical column.
    Returns a mapping from node.id -> (x, y).
    """
    positions = {}
    x = 400
    y = 200
    dy = 150
    for node in nodes:
        positions[node.id] = (x, y)
        y += dy
    return positions


def workflow_spec_to_n8n(spec: WorkflowSpec) -> Dict[str, Any]:
    """
    Convert a validated WorkflowSpec (flat DAG style) into an n8n workflow JSON dict.
    """
    n8n_nodes: List[Dict[str, Any]] = []
    n8n_connections: Dict[str, Any] = {}

    # Create a Manual Trigger node
    trigger_id = "Manual Trigger"
    trigger_node = {
        "id": "1",                      # internal n8n id (string)
        "name": trigger_id,
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [200, 200],
        "parameters": {},
    }
    n8n_nodes.append(trigger_node)

    # Layout positions for the rest of the nodes
    positions = _auto_layout(spec.nodes)

    # Create n8n nodes from spec.nodes
    node_id_counter = 2  # "1" is taken by the trigger
    node_name_to_n8n_id: Dict[str, str] = {}

    for node in spec.nodes:
        n8n_id = str(node_id_counter)
        node_id_counter += 1

        x, y = positions[node.id]

        # For now, represent everything as a Function node that just passes data through
        n8n_node = {
            "id": n8n_id,
            "name": node.id,  # use your node id as the n8n "name"
            "type": "n8n-nodes-base.function",
            "typeVersion": 1,
            "position": [x, y],
            "parameters": {
                # basic pass-through Function node
                "functionCode": "return items;",
            },
        }

        # Include metadata
        if node.description:
            n8n_node.setdefault("notesInFlow", True)
            n8n_node.setdefault("notes", node.description)

        n8n_nodes.append(n8n_node)
        node_name_to_n8n_id[node.id] = n8n_id

    # Build connections + Trigger -> all entry nodes (those with no incoming edges)
    all_node_ids = {n.id for n in spec.nodes}
    dests = {e.dest for e in spec.edges}
    entry_nodes = sorted(all_node_ids - dests)

    if entry_nodes:
        n8n_connections[trigger_id] = {"main": [[]]}
        for entry in entry_nodes:
            n8n_connections[trigger_id]["main"][0].append(
                {
                    "node": entry,
                    "type": "main",
                    "index": 0,
                }
            )

    # Edges between nodes (ignoring conditions for now)
    for edge in spec.edges:
        src = edge.src
        dest = edge.dest

        n8n_connections.setdefault(src, {"main": [[]]})
        n8n_connections[src]["main"][0].append(
            {
                "node": dest,
                "type": "main",
                "index": 0,
            }
        )

    # Assemble workflow
    workflow = {
        "name": spec.name,
        "nodes": n8n_nodes,
        "connections": n8n_connections,
    }
    return workflow


def yaml_file_to_n8n_json(yaml_path: Path, json_path: Path) -> None:
    """
    Load your YAML spec, validate it, convert to n8n, and write JSON.
    """
    raw = yaml.safe_load(yaml_path.read_text())
    spec, _ = validate_workflow(raw)
    n8n_workflow = workflow_spec_to_n8n(spec)
    json_path.write_text(json.dumps(n8n_workflow, indent=2))
    print(f"Wrote n8n workflow to {json_path}")


# if __name__ == "__main__":
#     yaml_file = Path("order_refund.yaml")
#     json_file = Path("order_refund_n8n.json")
#     yaml_file_to_n8n_json(yaml_file, json_file)