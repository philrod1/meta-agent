from .base import BaseAgent
from ..workflow import compiler, executor
import os
from typing import Dict, Any


class WorkflowCallAgent(BaseAgent):
    """Agent that calls a named workflow YAML and runs it as a sub-workflow.

    Params expected in node.params:
      - workflow_file: path to a YAML file relative to repo root or absolute
      - workflow_text: inline YAML string (optional, takes precedence over file)
    """

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Build inputs for the called workflow from the current context
        inputs = {k: context.get(k) for k in self.inputs if k in context}

        # Determine workflow source
        yaml_text = None
        if self.params and isinstance(self.params, dict):
            yaml_text = self.params.get("workflow_text")
            wf_file = self.params.get("workflow_file")
        else:
            wf_file = None

        if not yaml_text:
            if not wf_file:
                # fallback: try using a workflow with same id in workflows/ directory
                wf_file = os.path.join(os.getcwd(), "workflows", f"{self.node_id}.yaml")

            if not os.path.isabs(wf_file):
                # allow relative path
                wf_file = os.path.join(os.getcwd(), wf_file)

            if not os.path.exists(wf_file):
                raise FileNotFoundError(f"Workflow file not found: {wf_file}")

            with open(wf_file, 'r') as f:
                yaml_text = f.read()

        # Load workflow and run it
        wf = compiler.load_workflow(yaml_text)
        outputs = executor.run_workflow(wf, inputs)

        # Return outputs to be merged into parent's context
        return outputs
