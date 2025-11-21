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


@register_tool("split_in_half")
def split_in_half(numbers: list) -> dict:
    """Split a list into two halves (left, right). Returns dict with 'left' and 'right'."""
    if not isinstance(numbers, list):
        raise ValueError("split_in_half expects a list named 'numbers'")
    pivot = sum(numbers) / len(numbers) if numbers else 0
    left = []
    right = []
    for num in numbers:
        if num <= pivot:
            left.append(num)
        else:
            right.append(num)

    return {"left": left, "right": right}


@register_tool("compare_and_return")
def compare_and_return(numbers: list) -> dict:
    """Compare / sort small lists and return a sorted list under key 'sorted_numbers'.

    This tool is intended for the 'choice' alternative when a list is small
    (length == 2). Rather than splitting further, it can directly compare and return
    the sorted result.
    """
    if not isinstance(numbers, list):
        raise ValueError("compare_and_return expects a list named 'numbers'")
    if len(numbers) != 2:
        raise ValueError("compare_and_return only supports lists of length 2")
    
    sorted_list = numbers if numbers[0] <= numbers[1] else [numbers[1], numbers[0]]
    return {"sorted_numbers": sorted_list}


@register_tool("join_two_sorted_lists")
def join_two_sorted_lists(left: list, right: list) -> dict:
    """Merge two sorted lists and return combined sorted list under key 'sorted_numbers'."""
    if left is None:
        left = []
    if right is None:
        right = []
    merged = left + right
    return {"sorted_numbers": merged}