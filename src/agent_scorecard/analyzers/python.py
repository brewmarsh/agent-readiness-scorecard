import ast
import mccabe
from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS


class NestingDepthVisitor(ast.NodeVisitor):
    """
    AST visitor that calculates the maximum nesting depth of control flow blocks.
    """

    def __init__(self) -> None:
        self.current_depth: int = 0
        self.max_depth: int = 0

    def _visit_control_block(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._visit_control_block(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_control_block(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_control_block(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_control_block(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_control_block(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_control_block(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_control_block(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_control_block(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_control_block(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_control_block(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_control_block(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_control_block(node)


class PythonAnalyzer(BaseAnalyzer):
    """
    Python-specific implementation of the BaseAnalyzer.
    """

    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """
        Calculates score based on the selected profile and Agent Readiness spec.
        """
        p_thresholds = profile.get("thresholds", {})

        if thresholds is None:
            thresholds = {
                "acl_yellow": p_thresholds.get(
                    "acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]
                ),
                "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
                "type_safety": p_thresholds.get(
                    "type_safety", DEFAULT_THRESHOLDS["type_safety"]
                ),
                "token_limit": p_thresholds.get(
                    "token_limit", DEFAULT_THRESHOLDS["token_limit"]
                ),
            }

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100
        details = []

        if loc > 200:
            bloat_penalty = (loc - 200) // 10
            if bloat_penalty > 0:
                score -= bloat_penalty
                details.append(f"Bloated File: {loc} lines (-{bloat_penalty})")

        if not metrics:
            return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
        type_safety_threshold = thresholds.get(
            "type_safety", DEFAULT_THRESHOLDS["type_safety"]
        )
        token_limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])

        if cumulative_tokens > token_limit:
            penalty = 15
            score -= penalty
            details.append(
                f"Cumulative Token Budget Exceeded: {cumulative_tokens:,} > {token_limit:,} (-{penalty})"
            )

        red_count = sum(1 for m in metrics if m["acl"] > acl_red)
        yellow_count = sum(1 for m in metrics if acl_yellow < m["acl"] <= acl_red)

        if red_count > 0:
            penalty = red_count * 15
            score -= penalty
            details.append(f"{red_count} Red ACL functions (-{penalty})")

        if yellow_count > 0:
            penalty = yellow_count * 5
            score -= penalty
            details.append(f"{yellow_count} Yellow ACL functions (-{penalty})")

        typed_count = sum(1 for m in metrics if m["is_typed"])
        type_safety_index = (typed_count / len(metrics)) * 100

        if type_safety_index < type_safety_threshold:
            penalty = 20
            score -= penalty
            details.append(
                f"Type Safety Index {type_safety_index:.0f}% < {type_safety_threshold}% (-{penalty})"
            )

        avg_complexity = sum(m["complexity"] for m in metrics) / len(metrics)

        return (
            max(score, 0),
            ", ".join(details),
            loc,
            avg_complexity,
            type_safety_index,
            metrics,
        )

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        """
        Returns statistics for each function in the file including ACL and Type coverage.
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

                depth_visitor = NestingDepthVisitor()
                depth_visitor.visit(node)
                nesting_depth = depth_visitor.max_depth

                acl = self.calculate_acl(complexity, loc, nesting_depth)

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

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL).
        """
        return (depth * 2.0) + (complexity * 1.5) + (loc / 50.0)

    def _get_loc(self, filepath: str) -> int:
        """
        Returns lines of code excluding whitespace/comments.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(
                    1 for line in f if line.strip() and not line.strip().startswith("#")
                )
        except (UnicodeDecodeError, FileNotFoundError):
            return 0

    def get_complexity_score(self, filepath: str) -> float:
        """
        Returns average cyclomatic complexity for all functions in a file.
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

    def check_type_hints(self, filepath: str) -> float:
        """
        Returns type hint coverage percentage for functions and async functions.
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

    def calculate_max_depth(self, source_code: str) -> int:
        """
        Calculates the maximum nesting depth of control flow blocks in the given source code.
        """
        try:
            tree = ast.parse(source_code)
        except (SyntaxError, ValueError):
            return 0

        visitor = NestingDepthVisitor()
        visitor.visit(tree)
        return visitor.max_depth

    def count_tokens(self, filepath: str) -> int:
        """
        Estimates the number of tokens in a file (approx 4 chars/token).
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                return len(content) // 4
        except (UnicodeDecodeError, FileNotFoundError):
            return 0
