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


NUM = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,
       "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,
       "seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,"thirty":30,"forty":40,"fifty":50,
       "sixty":60,"seventy":70,"eighty":80,"ninety":90,"hundred":100}
SOUNDS_LIKE = {"to":"2","too":"2","for":"4","won":"1","ate":"8"}  # only used when a number is expected

def words_to_digits(text, loose=False):
    """'five plus three' -> '5 + 3'. loose=True also fixes to/too/for/won/ate."""
    out = []
    for w in text.lower().replace("-", " ").split():
        if w in NUM:
            out.append(str(NUM[w]))
        elif loose and w in SOUNDS_LIKE:
            out.append(SOUNDS_LIKE[w])
        else:
            out.append(w)
    # "twenty 5" -> "25"
    merged = []
    for w in out:
        if merged and w.isdigit() and merged[-1].isdigit() and int(merged[-1]) % 10 == 0 \
                and int(merged[-1]) >= 20 and int(merged[-1]) < 100 and int(w) < 10:
            merged[-1] = str(int(merged[-1]) + int(w))
        else:
            merged.append(w)
    return " ".join(merged)

def spoken_to_math(text):
    """'what is five plus three' -> '5 + 3' (for voice). Returns text unchanged if no number."""
    t = words_to_digits(text)
    for a, b in (("multiplied by", "*"), ("divided by", "/"), ("plus", "+"), ("minus", "-"),
                 ("times", "*"), ("over", "/"), ("what is", ""), ("what's", ""), ("how much is", "")):
        t = t.replace(a, b)
    return t.strip()
