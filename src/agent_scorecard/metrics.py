import ast
import mccabe
from typing import List, Dict
from .types import FunctionMetric

def get_loc(filepath: str) -> int:
    """Returns lines of code excluding whitespace/comments roughly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except UnicodeDecodeError:
        return 0

def get_complexity_score(filepath: str) -> float:
    """Returns average cyclomatic complexity."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0

    return sum(complexities) / len(complexities)

def check_type_hints(filepath: str) -> float:
    """Returns type hint coverage percentage."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return 100

    typed_functions = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        if has_return or has_args:
            typed_functions += 1

    return (typed_functions / len(functions)) * 100

def calculate_acl(complexity: float, loc: int) -> float:
    """Calculates Agent Cognitive Load (ACL). Formula: ACL = CC + (LLOC / 20)"""
    return complexity + (loc / 20.0)

def count_tokens(filepath: str) -> int:
    """Estimates the number of tokens in a file (approx 4 chars/token)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return len(content) // 4
    except UnicodeDecodeError:
        return 0

def get_function_stats(filepath: str) -> List[FunctionMetric]:
    """Returns statistics for each function in the file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)
    complexity_map = {graph.lineno: graph.complexity() for graph in visitor.graphs.values()}

    stats: List[FunctionMetric] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line)
            loc = end_line - start_line + 1
            complexity = complexity_map.get(start_line, 1)
            acl = calculate_acl(complexity, loc)

            stats.append({
                "name": node.name,
                "lineno": start_line,
                "complexity": complexity,
                "loc": loc,
                "acl": acl,
                "is_typed": (node.returns is not None) or any(arg.annotation is not None for arg in node.args.args)
            })
    return stats
