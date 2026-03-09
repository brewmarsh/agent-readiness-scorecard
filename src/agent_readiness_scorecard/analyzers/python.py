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

    @property
    def language(self) -> str:
        return "Python"

    def _parse_code(self, filepath: str) -> Optional[ast.AST]:
        """Reads and parses Python code from a file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            return ast.parse(code, filepath)
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            return None

    def _get_complexity_map(self, tree: ast.AST) -> Dict[int, float]:
        """Returns a mapping of line numbers to cyclomatic complexity."""
        visitor = mccabe.PathGraphingAstVisitor()
        visitor.preorder(tree, visitor)
        return {
            graph.lineno: float(graph.complexity())
            for graph in visitor.graphs.values()
        }

    def _is_typed(self, node: ast.AST) -> bool:
        """Checks if a function node has return or argument type hints."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        has_return = node.returns is not None
        has_args = any(arg.annotation is not None for arg in node.args.args)
        return has_return or has_args

    def _create_function_metric(
        self, node: ast.AST, complexity_map: Dict[int, float]
    ) -> Optional[FunctionMetric]:
        """Calculates metrics for a single function node."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        loc = end_line - start_line + 1
        complexity = float(complexity_map.get(start_line, 1.0))

        depth_visitor = NestingDepthVisitor()
        depth_visitor.visit(node)
        nesting_depth = depth_visitor.max_depth

        return {
            "name": node.name,
            "lineno": start_line,
            "complexity": complexity,
            "loc": loc,
            "acl": self.calculate_acl(complexity, loc, nesting_depth),
            "is_typed": self._is_typed(node),
            "nesting_depth": nesting_depth,
        }

    def _get_effective_thresholds(
        self, profile: Dict[str, Any], thresholds: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merges profile and provided thresholds."""
        # Start with defaults
        effective = DEFAULT_THRESHOLDS.copy()

        # Override with profile specific thresholds if they exist
        p_thresholds = profile.get("thresholds", {})
        effective.update(p_thresholds)

        # Finally override with explicitly provided thresholds (from CLI or config)
        if thresholds:
            effective.update(thresholds)

        return effective

    def _apply_bloat_penalty(self, score: int, details: List[str], loc: int) -> int:
        """Applies penalty for bloated files (> 200 lines)."""
        if loc > 200:
            bloat_penalty = (loc - 200) // 10
            if bloat_penalty > 0:
                details.append(f"Bloated File: {loc} lines (-{bloat_penalty})")
                return score - bloat_penalty
        return score

    def _apply_token_penalty(
        self, score: int, details: List[str], current: int, limit: int
    ) -> int:
        """Applies penalty if cumulative token budget is exceeded."""
        if current > limit:
            penalty = 15
            details.append(
                f"Cumulative Token Budget Exceeded: {current:,} > {limit:,} (-{penalty})"
            )
            return score - penalty
        return score

    def _apply_acl_penalties(
        self,
        score: int,
        details: List[str],
        metrics: List[FunctionMetric],
        yellow: float,
        red: float,
    ) -> int:
        """Applies penalties for functions exceeding ACL thresholds."""
        red_count = sum(1 for m in metrics if m["acl"] > red)
        yellow_count = sum(1 for m in metrics if yellow < m["acl"] <= red)

        if red_count > 0:
            penalty = red_count * 15
            score -= penalty
            details.append(f"{red_count} Red ACL functions (-{penalty})")

        if yellow_count > 0:
            penalty = yellow_count * 5
            score -= penalty
            details.append(f"{yellow_count} Yellow ACL functions (-{penalty})")
        return score

    def _apply_type_safety_penalty(
        self,
        score: int,
        details: List[str],
        metrics: List[FunctionMetric],
        threshold: float,
    ) -> Tuple[int, float]:
        """Applies penalty for low type safety coverage."""
        typed_count = sum(1 for m in metrics if m["is_typed"])
        index = (typed_count / len(metrics)) * 100

        if index < threshold:
            penalty = 20
            score -= penalty
            details.append(
                f"Type Safety Index {index:.0f}% < {threshold}% (-{penalty})"
            )
        return score, index

    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """Calculates score based on selected profile and spec."""
        thresholds = self._get_effective_thresholds(profile, thresholds)
        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score, details = 100, []
        score = self._apply_bloat_penalty(score, details, loc)

        if not metrics:
            return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

        score = self._apply_token_penalty(
            score, details, cumulative_tokens, thresholds["token_limit"]
        )
        score = self._apply_acl_penalties(
            score, details, metrics, thresholds["acl_yellow"], thresholds["acl_red"]
        )
        score, type_safety_index = self._apply_type_safety_penalty(
            score, details, metrics, thresholds["type_safety"]
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
        """Returns statistics for each function in the file."""
        tree = self._parse_code(filepath)
        if tree is None:
            return []

        complexity_map = self._get_complexity_map(tree)
        return [
            m
            for m in (self._create_function_metric(n, complexity_map) for n in ast.walk(tree))
            if m
        ]

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL).
        """
        return (depth * 2.0) + (complexity * 1.5) + (loc / 50.0)

    def _get_loc(self, filepath: str) -> int:
        """Returns lines of code excluding whitespace/comments."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, FileNotFoundError):
            return 0

        return sum(
            1
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        )

    def get_complexity_score(self, filepath: str) -> float:
        """Returns average cyclomatic complexity for all functions in a file."""
        tree = self._parse_code(filepath)
        if tree is None:
            return 0.0

        complexities = list(self._get_complexity_map(tree).values())
        return sum(complexities) / len(complexities) if complexities else 0.0

    def check_type_hints(self, filepath: str) -> float:
        """Returns type hint coverage percentage for functions."""
        tree = self._parse_code(filepath)
        if tree is None:
            return 0.0

        functions = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not functions:
            return 100.0

        typed = sum(1 for f in functions if self._is_typed(f))
        return (typed / len(functions)) * 100.0

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
