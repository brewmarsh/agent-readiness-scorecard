import ast
import mccabe
from typing import List
from .types import FunctionMetric


def get_loc(filepath: str) -> int:
    """
    Returns lines of code excluding whitespace/comments roughly.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        int: Logical lines of code.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(
                1 for line in f if line.strip() and not line.strip().startswith("#")
            )
    except (UnicodeDecodeError, FileNotFoundError):
        return 0


def get_complexity_score(filepath: str) -> float:
    """
    Returns average cyclomatic complexity for all functions in a file.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        float: Average cyclomatic complexity.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return 0.0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0.0

    return sum(complexities) / len(complexities)


def check_type_hints(filepath: str) -> float:
    """
    Returns type hint coverage percentage for functions and async functions.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        float: Type hint coverage percentage (0-100).
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return 0.0

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if not functions:
        return 100.0

    typed_functions = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        if has_return or has_args:
            typed_functions += 1

    return (typed_functions / len(functions)) * 100.0


def calculate_acl(complexity: float, loc: int, depth: int) -> float:
    """
    Calculates Agent Cognitive Load (ACL).

    Formula: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)

    Args:
        complexity (float): Cyclomatic complexity of the code unit.
        loc (int): Logical lines of code of the code unit.
        depth (int): Maximum nesting depth of control flow blocks.

    Returns:
        float: Calculated ACL value.
    """
    return (depth * 2.0) + (complexity * 1.5) + (loc / 50.0)


def count_tokens(filepath: str) -> int:
    """
    Estimates the number of tokens in a file (approx 4 chars/token).

    Args:
        filepath (str): Path to the file.

    Returns:
        int: Estimated token count.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return len(content) // 4
    except (UnicodeDecodeError, FileNotFoundError):
        return 0


def get_function_stats(filepath: str) -> List[FunctionMetric]:
    """
    Returns statistics for each function in the file including ACL and Type coverage.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        List[FunctionMetric]: A list of metrics for each function found.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)
    complexity_map = {
        graph.lineno: graph.complexity() for graph in visitor.graphs.values()
    }

    stats: List[FunctionMetric] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            loc = end_line - start_line + 1
            complexity = float(complexity_map.get(start_line, 1))

            # --- CIRCULAR IMPORT MITIGATION ---
            # NestingDepthVisitor and calculate_max_depth were moved to analyzer.py
            # to satisfy the AGENTS.md architectural spec and project goals.
            from .analyzer import NestingDepthVisitor

            depth_visitor = NestingDepthVisitor()
            depth_visitor.visit(node)
            nesting_depth = depth_visitor.max_depth

            # Calculate ACL using the new structural-depth weighted formula
            acl = calculate_acl(complexity, loc, nesting_depth)

            stats.append(
                {
                    "name": node.name,
                    "lineno": start_line,
                    "complexity": complexity,
                    "loc": loc,
                    "acl": acl,
                    "is_typed": (node.returns is not None)
                    or any(arg.annotation is not None for arg in node.args.args),
                    "nesting_depth": nesting_depth,
                }
            )
    return stats
