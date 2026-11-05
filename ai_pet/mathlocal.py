import ast, operator

OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}

def calc(node):
    """Numbers and + - * / // % ** only. Anything else is rejected."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = calc(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left = calc(node.left)
        right = calc(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too big")
        return OPS[type(node.op)](left, right)
    raise ValueError("not math")

def try_math(text):
    """Return the answer as a string, or None if this is not simple math."""
    text = text.strip().rstrip("=? ")
    text = text.replace("^", "**").replace("×", "*").replace("÷", "/")
    if len(text) > 100:
        return None
    try:
        tree = ast.parse(text, mode="eval")
        if not isinstance(tree.body, (ast.BinOp, ast.UnaryOp)):
            return None
        result = calc(tree.body)
    except ZeroDivisionError:
        return "You can't divide by zero!"
    except (SyntaxError, ValueError, OverflowError, RecursionError):
        return None
    if isinstance(result, float):
        result = int(result) if result.is_integer() else round(result, 6)
    return str(result)
