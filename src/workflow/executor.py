import time
from typing import Dict, Any
from .guards import evaluate_condition
from .factory import make_agent
from .models import Workflow, Node, Edge

def run_workflow(workflow: Workflow, inputs: Dict[str, Any], *, dry_run: bool = False) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "__start_ts": time.time(),
        "none": None,
        "true": True,
        "false": False,
        **inputs
    }
    
    # repeatedly find ready nodes whose predecessors have run, follow guards
    executed = set()
    ready = [n for n in workflow.nodes if _indegree(workflow, n.id) == 0]

    # Check preconditions
    for expression in workflow.preconditions:
        assert evaluate_condition(expression, context), f"Precondition failed: {expression}"
    
    # Adjacency
    in_edges: Dict[str, Any] = {}
    out_edges: Dict[str, Any] = {}
    for edge in workflow.edges:
        out_edges.setdefault(edge.src, []).append(edge)
        in_edges.setdefault(edge.dest, []).append(edge)
        in_edges.setdefault(edge.src, in_edges.get(edge.src, []))
    
    while ready:
        node = ready.pop(0)
        if node.id in executed:
            continue
        
        agent = make_agent(node)
        produced = agent.dry_run(context) if dry_run else agent.execute(context)
        context.update(produced)

        for test in node.tests:
            assert evaluate_condition(_normalize(test), context), f"Test failed for node {node.id}: {test}"
        
        executed.add(node.id)
    
        # Successors
        for edge in out_edges.get(node.id, []):
            if evaluate_condition(_normalize(edge.when), context):
                dest_node = next(n for n in workflow.nodes if n.id == edge.dest)
                if all(pred.src in executed for pred in in_edges.get(dest_node.id, [])):
                    ready.append(dest_node)
    
    # Check success criteria
    for expression in workflow.success_criteria:
        assert evaluate_condition(expression, context), f"Success criteria failed: {expression}"

    # Check failure conditions
    for expression in workflow.failure_conditions:
        assert not evaluate_condition(expression, context), f"Failure condition met: {expression}"

    return {k: context.get(k) for k in workflow.outputs}


def _indegree(wf: Workflow, node_id: str) -> int:
    """Calculate the in-degree of a node."""
    return sum(1 for e in wf.edges if e.dest == node_id)

def _normalize(expr: str) -> str:
    # Allow tests like "email_id != null" in YAML
    return expr.replace("null", "None")