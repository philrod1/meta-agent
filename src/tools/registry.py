from typing import Callable, Dict

_TOOLS: Dict[str, Callable] = {}

def register_tool(name: str):
    def _wrap(fn):
        _TOOLS[name] = fn
        return fn
    return _wrap

def get_tool(name: str) -> Callable:
    if name not in _TOOLS:
        raise ValueError(f"Tool not found: {name}")
    return _TOOLS[name]

# Example tool registration
@register_tool("orders.get")
def orders_get(order_id: str, customer_id: str) -> Dict[str, str]:
    """ Retrieve order details by order ID. """
    return {
        "order": {"id": order_id, "status": "completed"},
        "account": {"id": customer_id, "email": "customer@example.com"}
    }

@register_tool("payments.refund")
def payments_refund(order: dict, payment_method: str, price: float) -> Dict[str, dict]:
    """ Process a refund for a given order. """
    return {
        "refund_receipt": {
            "status": "ok",
            "amount": price,
            "method": payment_method,
            "order_id": order.get("id")
        }
    }

@register_tool("notifications.email")
def notifications_email(email: str, refund_receipt: dict, template: str = "refund_success") -> Dict[str, str]:
    """ Send an email notification. """
    return {"email_id": f"email-{refund_receipt.get('order_id', 'unknown')}"}

@register_tool("audit.write")
def audit_write(order_id: str, refund_receipt: dict, email_id: str) -> Dict[str, str]:
    """ Write an audit log entry. """
    return {"audit_id": f"audit-{order_id}"}