"""Example: demonstrate workflow_call node that runs an inline child workflow."""
from src.workflow import compiler, executor


def main():
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
    inputs = {"order_id": "o-1", "customer_id": "c-1"}
    outputs = executor.run_workflow(wf, inputs)
    print("Outputs:", outputs)


if __name__ == "__main__":
    main()
