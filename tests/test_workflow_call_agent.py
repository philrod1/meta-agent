import pytest
from src.workflow import compiler, executor


def test_workflow_call_agent_inline_child(tmp_path):
    # Child workflow (simple tool call that returns an 'order')
    child_yaml = """
name: child_workflow
description: returns an order
inputs: [order_id, customer_id]
outputs: [order]
nodes:
  - id: get_order
    type: tool
    params:
      tool: orders.get
    io:
      inputs: [order_id, customer_id]
      outputs: [order]
edges: []
preconditions: []
success_criteria: ["order != None"]
failure_conditions: []
"""

    # Parent workflow that calls the child via workflow_call with inline YAML
    parent_yaml = f"""
name: parent_workflow
description: calls child workflow
inputs: [order_id, customer_id]
outputs: [order]
nodes:
  - id: call_child
    type: workflow_call
    params:
      workflow_text: |
{child_yaml.replace('\n', '\n        ')}
    io:
      inputs: [order_id, customer_id]
      outputs: [order]
edges: []
preconditions: []
success_criteria: ["order != None"]
failure_conditions: []
"""

    wf = compiler.load_workflow(parent_yaml)

    inputs = {"order_id": "o-123", "customer_id": "c-456"}
    outputs = executor.run_workflow(wf, inputs)

    assert "order" in outputs
    assert outputs["order"]["id"] == "o-123"
