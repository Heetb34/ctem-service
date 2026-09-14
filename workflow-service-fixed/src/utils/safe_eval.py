"""
Restricted evaluator for workflow "condition" expressions.

Workflow definitions are user-authored data, not trusted code. The
original implementation ran them through eval() with an empty
__builtins__ dict, which is a well-known, frequently-bypassed sandbox
(e.g. via `().__class__.__base__.__subclasses__()`-style attribute
chains). This module instead parses the expression to an AST and only
evaluates a small, explicitly allow-listed set of node types, so there
is no way to reach an attribute, a function call, or an import.

Supported: comparisons (==, !=, <, <=, >, >=, in, not in), boolean
operators (and/or/not), literals (str/int/float/bool/None/list/tuple),
and name/subscript access into the `context` (aka `data`) dict that was
passed in for the step.
"""

import ast
from typing import Any, Dict


class UnsafeExpressionError(ValueError):
    pass


_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_CMP_OPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn)
_ALLOWED_UNARY_OPS = (ast.Not,)


def evaluate_condition(expr: str, context: Dict[str, Any]) -> bool:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise UnsafeExpressionError(f"Invalid condition syntax: {e}") from e

    scope = {"context": context, "data": context}
    return bool(_eval_node(tree.body, scope))


def _eval_node(node: ast.AST, scope: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            return node.value
        raise UnsafeExpressionError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.Name):
        if node.id in scope:
            return scope[node.id]
        raise UnsafeExpressionError(f"Unknown name: {node.id}")

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval_node(elt, scope) for elt in node.elts]

    if isinstance(node, ast.Subscript):
        value = _eval_node(node.value, scope)
        key = _eval_node(node.slice, scope)
        try:
            return value[key]
        except (KeyError, IndexError, TypeError):
            return None

    if isinstance(node, ast.BoolOp):
        if not isinstance(node.op, _ALLOWED_BOOL_OPS):
            raise UnsafeExpressionError("Unsupported boolean operator")
        values = [_eval_node(v, scope) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)

    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY_OPS):
            raise UnsafeExpressionError("Unsupported unary operator")
        return not _eval_node(node.operand, scope)

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, scope)
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, _ALLOWED_CMP_OPS):
                raise UnsafeExpressionError("Unsupported comparison operator")
            right = _eval_node(comparator, scope)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            else:
                raise UnsafeExpressionError("Unsupported comparison operator")
            if not ok:
                return False
            left = right
        return True

    raise UnsafeExpressionError(f"Unsupported expression: {ast.dump(node)}")
