import ast
import mccabe
from typing import List, Dict, Any, Tuple, Set, Optional, cast
from .types import FunctionMetric


class NestingDepthVisitor(ast.NodeVisitor):
    """
    AST visitor that calculates the maximum nesting depth of control flow blocks.

    This visitor tracks If, For, AsyncFor, While, Try, With, AsyncWith,
    ListComp, SetComp, DictComp, GeneratorExp, and Lambda nodes.
    """

    def __init__(self) -> None:
        """Initializes the visitor with depth counters."""
        self.current_depth: int = 0
        self.max_depth: int = 0

    def _visit_control_block(self, node: ast.AST) -> None:
        """
        Increments depth, tracks max, visits children, then decrements.

        Args:
            node (ast.AST): The control block node to visit.
        """
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        """Visits an If node."""
        self._visit_control_block(node)

    def visit_For(self, node: ast.For) -> None:
        """Visits a For node."""
        self._visit_control_block(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Visits an AsyncFor node."""
        self._visit_control_block(node)

    def visit_While(self, node: ast.While) -> None:
        """Visits a While node."""
        self._visit_control_block(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Visits a Try node."""
        self._visit_control_block(node)

    def visit_With(self, node: ast.With) -> None:
        """Visits a With node."""
        self._visit_control_block(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Visits an AsyncWith node."""
        self._visit_control_block(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Visits a ListComp node."""
        self._visit_control_block(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Visits a SetComp node."""
        self._visit_control_block(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Visits a DictComp node."""
        self._visit_control_block(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Visits a GeneratorExp node."""
        self._visit_control_block(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Visits a Lambda node."""
        self._visit_control_block(node)


def calculate_max_depth(source_code: str) -> int:
    """
    Calculates the maximum nesting depth of control flow blocks in the given source code.

    Args:
        source_code (str): The Python source code to analyze.

    Returns:
        int: The maximum nesting depth detected.
    """
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return 0

    visitor = NestingDepthVisitor()
    visitor.visit(tree)
    return visitor.max_depth


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


def calculate_acl(complexity: float, loc: int) -> float:
    """
    Calculates Agent Cognitive Load (ACL).

    Formula: ACL = Cyclomatic Complexity + (Logical Lines of Code / 20)

    Args:
        complexity (float): Cyclomatic complexity of the code unit.
        loc (int): Logical lines of code of the code unit.

    Returns:
        float: Calculated ACL value.
    """
    return complexity + (loc / 20.0)


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
            acl = calculate_acl(complexity, loc)

            # Calculate Nesting Depth
            depth_visitor = NestingDepthVisitor()
            depth_visitor.visit(node)
            nesting_depth = depth_visitor.max_depth

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
