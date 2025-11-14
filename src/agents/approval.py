import time
from .base import BaseAgent

class ApprovalAgent(BaseAgent):
    def execute(self, context):
        # MVP: just approve it!
        timeout = int(self.params.get("timeout_hours", 24))
        approved = context.get("approved")
        if approved is None:
            # simulate pending -> approved
            approved = True
        return {"approved": approved}