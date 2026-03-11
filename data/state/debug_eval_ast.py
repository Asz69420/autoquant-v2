import ast, json
prepared='v0 < v1'
token_map={'v0':3979.6,'v1':4078.8463159632306}
tree=ast.parse(prepared, mode='eval')

def eval_node(node):
    if isinstance(node, ast.Expression):
        return eval_node(node.body)
    if isinstance(node, ast.Name):
        return token_map.get(node.id)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.UnaryOp):
        operand = eval_node(node.operand)
        if operand is None:
            return None
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.Not):
            return not operand
    if isinstance(node, ast.BinOp):
        left = eval_node(node.left)
        right = eval_node(node.right)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right if right != 0 else None
        if isinstance(node.op, ast.Pow):
            return left ** right
    if isinstance(node, ast.BoolOp):
        vals = [eval_node(v) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in vals)
        if isinstance(node.op, ast.Or):
            return any(bool(v) for v in vals)
    if isinstance(node, ast.Compare):
        left = eval_node(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = eval_node(comparator)
            if left is None or right is None:
                return False
            ok = False
            if isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.Eq):
                ok = abs(left - right) < 1e-10
            elif isinstance(op, ast.NotEq):
                ok = abs(left - right) >= 1e-10
            if not ok:
                return False
            left = right
        return True
    raise ValueError(type(node).__name__)

print(json.dumps({'result': eval_node(tree)}))
