import ast
import operator

# _ALLOWED_OPERATORS = {
#     "==": operator.eq,
#     "!=": operator.ne,
#     "<": operator.lt,
#     "<=": operator.le,
#     ">": operator.gt,
#     ">=": operator.ge,
#     "and": lambda a, b: a and b,
#     "or": lambda a, b: a or b
# }

def evaluate_condition(expression: str, context: dict) -> bool:
    """
    Evaluate a guard expression in the provided context.
    """
    expression = expression.strip().lower()
    if expression in ("true", ""):  # Default to true
        return True
    
    expression = expression.replace("&&", " and ").replace("||", " or ")
    try:
        return bool(_safe_eval(expression, context))
    except Exception:
        return False
    
def _safe_eval(expression: str, context: dict) -> bool:
    node = ast.parse(expression, mode='eval')

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        
        if isinstance(node, ast.BoolOp):
            values = [_eval(v) for v in node.values]
            if isinstance(node.op, ast.And):
                out = True
                for v in values:
                    out = out and v
                return out
            elif isinstance(node.op, ast.Or):
                out = False
                for v in values:
                    out = out or v
                return out
            
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                if isinstance(op, ast.Eq):      ok = (left == right)
                elif isinstance(op, ast.NotEq): ok = (left != right)
                elif isinstance(op, ast.Lt):    ok = (left < right)
                elif isinstance(op, ast.LtE):   ok = (left <= right)
                elif isinstance(op, ast.Gt):    ok = (left > right)
                elif isinstance(op, ast.GtE):   ok = (left >= right)
                else:
                    raise ValueError(f"Unsupported operator: {op}")
                if not ok:
                    return False
                left = right
            return True
        
        if isinstance(node, ast.Name):
            return context[node.id]
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError("Unsupported expression")
    
    return _eval(node)

# Alias for backward compatibility
eval_guard = evaluate_condition