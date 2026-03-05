from typing import Dict, Any, List, Tuple, Optional

try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_javascript
    import tree_sitter_typescript

    HAS_TREESITTER = True
except ImportError:
    HAS_TREESITTER = False
    # Stubs for type hinting and to prevent NameErrors when dependencies are missing
    Language = Any  # type: ignore
    Parser = Any    # type: ignore
    class Node: pass # type: ignore

from rich.console import Console
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS

# Initialize languages if the binary grammars are present
if HAS_TREESITTER:
    JS_LANGUAGE = Language(tree_sitter_javascript.language())
    TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
    TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
else:
    JS_LANGUAGE = None
    TS_LANGUAGE = None
    TSX_LANGUAGE = None

# Global flag to ensure we only warn the user once per execution
WARN_TREESITTER = False


class JavascriptAnalyzer(BaseAnalyzer):
    """
    Analyzes JavaScript and TypeScript files using tree-sitter.
    Calculates ACL: (Depth * 2) + (Complexity * 1.5) + (LOC / 50).
    """

    @property
    def language(self) -> str:
        return "JavaScript"

    def _get_language(self, filepath: str) -> Language:
        if filepath.endswith(".tsx"):
            return TSX_LANGUAGE
        if filepath.endswith(".ts"):
            return TS_LANGUAGE
        return JS_LANGUAGE

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
        loc = self._get_loc(filepath)
        
        # Guard clause for missing optional dependencies
        if not HAS_TREESITTER:
            global WARN_TREESITTER
            if not WARN_TREESITTER:
                console = Console()
                console.print(
                    "[yellow]Warning: tree-sitter not found. JS/TS analysis will be skipped.[/yellow]"
                )
                console.print(
                    "[yellow]Hint: Install the 'treesitter' extra: pip install agent-readiness-scorecard[treesitter][/yellow]"
                )
                WARN_TREESITTER = True
            
            return (0, "Missing dependencies: Install [treesitter] extra", loc, 0.0, 100.0, [])

        p_thresholds = profile.get("thresholds", {})
        if thresholds is None:
            thresholds = self._get_default_thresholds(p_thresholds)

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100.0
        details: List[str] = []

        # 1. Apply File Bloat Penalty
        score, details = self._apply_bloat_penalty(score, details, loc)

        if not metrics:
            return max(int(score), 0), ", ".join(details), loc, 0.0, 100.0, []

        # 2. Apply Physics-based Penalties
        score, details = self._apply_token_penalty(
            score, details, cumulative_tokens, thresholds
        )
        score, details = self._apply_acl_penalty(score, details, metrics, thresholds)
        score, details, type_safety_index = self._apply_type_safety_penalty(
            score, details, metrics, thresholds, filepath
        )

        avg_complexity = (
            sum(m["complexity"] for m in metrics) / len(metrics) if metrics else 0.0
        )

        return (
            max(int(score), 0),
            ", ".join(details),
            loc,
            avg_complexity,
            type_safety_index,
            metrics,
        )

    def _get_default_thresholds(self, p_thresholds: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "acl_yellow": p_thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]),
            "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
            "type_safety": p_thresholds.get("type_safety", DEFAULT_THRESHOLDS["type_safety"]),
            "token_limit": p_thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"]),
        }

    def _apply_bloat_penalty(self, score: float, details: List[str], loc: int) -> Tuple[float, List[str]]:
        if loc > 200:
            penalty = (loc - 200) // 10
            if penalty > 0:
                score -= penalty
                details.append(f"Bloated File: {loc} lines (-{penalty})")
        return score, details

    def _apply_token_penalty(self, score: float, details: List[str], tokens: int, thresholds: Dict) -> Tuple[float, List[str]]:
        limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])
        if tokens > limit:
            penalty = 15
            score -= penalty
            details.append(f"Token Budget Exceeded: {tokens:,} > {limit:,} (-{penalty})")
        return score, details

    def _apply_acl_penalty(self, score: float, details: List[str], metrics: List[FunctionMetric], thresholds: Dict) -> Tuple[float, List[str]]:
        yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
        red_cnt = sum(1 for m in metrics if m["acl"] > red)
        yel_cnt = sum(1 for m in metrics if yellow < m["acl"] <= red)

        if red_cnt > 0:
            p = red_cnt * 15
            score -= p
            details.append(f"{red_cnt} Red ACL functions (-{p})")
        if yel_cnt > 0:
            p = yel_cnt * 5
            score -= p
            details.append(f"{yel_cnt} Yellow ACL functions (-{p})")
        return score, details

    def _apply_type_safety_penalty(self, score: float, details: List[str], metrics: List[FunctionMetric], thresholds: Dict, path: str) -> Tuple[float, List[str], float]:
        is_ts = path.endswith(".ts") or path.endswith(".tsx")
        target = thresholds.get("type_safety", DEFAULT_THRESHOLDS["type_safety"])
        
        typed_cnt = sum(1 for m in metrics if m["is_typed"])
        index = (typed_cnt / len(metrics)) * 100 if metrics else 100.0

        if is_ts and index < target:
            penalty = 20
            score -= penalty
            details.append(f"Type Safety Index {index:.0f}% < {target}% (-{penalty})")
        return score, details, index

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        if not HAS_TREESITTER: return []
        try:
            with open(filepath, "rb") as f:
                source = f.read()
        except FileNotFoundError: return []

        language = self._get_language(filepath)
        parser = Parser(language)
        tree = parser.parse(source)

        stats: List[FunctionMetric] = []
        visited: set[int] = set()
        self._visit_tree(tree.root_node, visited, stats, filepath)
        return stats

    def _visit_tree(self, node: Node, visited: set[int], stats: List[FunctionMetric], path: str) -> None:
        if node.id in visited: return
        visited.add(node.id)

        if node.type in ("function_declaration", "function_expression", "arrow_function", "method_definition"):
            self._analyze_function(node, stats, path)
        
        for child in node.children:
            self._visit_tree(child, visited, stats, path)

    def _analyze_function(self, node: Node, stats: List[FunctionMetric], path: str):
        start = node.start_point[0] + 1
        loc = (node.end_point[0] + 1) - start + 1
        complexity = 1.0 + self._visit_complexity(node)
        depth = self._calculate_nesting_depth(node)
        
        # High-Fidelity ACL Formula
        acl = (depth * 2.0) + (complexity * 1.5) + (loc / 50.0)

        stats.append({
            "name": self._get_function_name(node),
            "lineno": start,
            "complexity": complexity,
            "loc": loc,
            "acl": acl,
            "is_typed": self._check_is_typed(node),
            "nesting_depth": depth,
        })

    def _get_function_name(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        if name_node and name_node.text:
            return name_node.text.decode("utf-8")
        return "anonymous"

    def _visit_complexity(self, n: Node) -> float:
        count = 0.0
        if n.type in ("if_statement", "for_statement", "while_statement", "switch_case", "catch_clause", "conditional_expression"):
            count += 1.0
        
        for child in n.children:
            if "function" not in child.type and "method" not in child.type:
                count += self._visit_complexity(child)
        return count

    def _calculate_nesting_depth(self, node: Node) -> int:
        body = node.child_by_field_name("body")
        return self._visit_depth(body, 0) if body else 0

    def _visit_depth(self, n: Node, current: int) -> int:
        max_d = current
        if n.type in ("if_statement", "for_statement", "while_statement", "switch_statement"):
            current += 1
        
        for child in n.children:
            if "function" not in child.type:
                d = self._visit_depth(child, current)
                if d > max_d: max_d = d
        return max_d

    def _check_is_typed(self, node: Node) -> bool:
        if node.child_by_field_name("return_type"): return True
        params = node.child_by_field_name("parameters")
        if params:
            for i in range(params.child_count):
                if "type" in params.child(i).type: return True
        return False

    def _get_loc(self, filepath: str) -> int:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except: return 0