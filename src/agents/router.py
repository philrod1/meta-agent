from .base import BaseAgent

class RouterAgent(BaseAgent):
    """ Agent that routes tasks to other agents based on criteria. """
    def execute(self, context: dict) -> dict:
        """ Route the task and return the result. """
        # Simple routing logic based on a 'task_type' parameter
        task_type = self.params.get("task_type")
        if task_type == "type_a":
            # Route to Agent A
            result = {"result": f"Routed to Agent A for {context}"}
        elif task_type == "type_b":
            # Route to Agent B
            result = {"result": f"Routed to Agent B for {context}"}
        else:
            result = {"result": f"No suitable agent found for {context}"}
        return result