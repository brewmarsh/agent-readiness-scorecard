import logging
from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS

# RESOLUTION: Implement Graceful Degradation and multi-language support from beta
try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_javascript
    import tree_sitter_typescript

    # Initialize languages
    JS_LANGUAGE = Language(tree_sitter_javascript.language())
    TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
    TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


class JavascriptAnalyzer(BaseAnalyzer):
    """
    Analyzes JavaScript and TypeScript files using tree-sitter.
    Calculates ACL: (Depth * 2) + (Complexity * 1.5) + (LOC / 50).
    """

    def __init__(self) -> None:
        super().__init__()
        if not HAS_TREE_SITTER:
            logging.warning(
                "tree-sitter is not installed. JavaScript/TypeScript analysis will be skipped. "
                "Install with: pip install tree-sitter tree-sitter-javascript tree-sitter-typescript"
            )

    @property
    def language(self) -> str:
        # RESOLUTION: Adopted inclusive label from beta
        return "JavaScript/TypeScript"

    def _get_language(self, filepath: str) -> Optional["Language"]:
        if not HAS_TREE_SITTER:
            return None
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
        if not HAS_TREE_SITTER:
            return 100, "Skipped: tree-sitter missing", 0, 0.0, 100.0, []

        p_thresholds = profile.get("thresholds", {})
        if thresholds is None:
            thresholds = self._get_default_thresholds(p_thresholds)

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100.0
        details: List[str] = []

        # Orchestrate penalties using modular private methods
        score, details = self._apply_bloat_penalty(score, details, loc)

        if not metrics:
            return max(int(score), 0), ", ".join(details), loc, 0.0, 100.0, []

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

    # --- Private Penalty Helpers (Modular Refactor) ---

    def _get_default_thresholds(self, p_thresholds: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "acl_yellow": p_thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]),
            "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
            "type_safety": p_thresholds.get("type_safety", DEFAULT_THRESHOLDS["type_safety"]),
            "token_limit": p_thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"]),
        }

    def _apply_bloat_penalty(self, score: float, details: List[str], loc: int) -> Tuple[float, List[str]]:
        if loc > 200:
            bloat_penalty = (loc - 200) // 10
            if bloat_penalty > 0:
                score -= bloat_penalty
                details.append(f"Bloated File: {loc} lines (-{bloat_penalty})")
        return score, details

    def _apply_token_penalty(self, score: float, details: List[str], cumulative_tokens: int, thresholds: Dict[str, Any]) -> Tuple[float, List[str]]:
        token_limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])
        if cumulative_tokens > token_limit:
            penalty = 15
            score -= penalty
            details.append(f"Cumulative Token Budget Exceeded: {cumulative_tokens:,} > {token_limit:,} (-{penalty})")
        return score, details

    def _apply_acl_penalty(self, score: float, details: List[str], metrics: List[FunctionMetric], thresholds: Dict[str, Any]) -> Tuple[float, List[str]]:
        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
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
        return score, details

    def _apply_type_safety_penalty(self, score: float, details: List[str], metrics: List[FunctionMetric], thresholds: Dict[str, Any], filepath: str) -> Tuple[float, List[str], float]:
        typed_count = sum(1 for m in metrics if m["is_typed"])
        is_ts = filepath.endswith(".ts") or filepath.endswith(".tsx")
        type_safety_threshold = thresholds.get("type_safety", DEFAULT_THRESHOLDS["type_safety"])
        type_safety_index = 100.0

        if is_ts:
            type_safety_index = (typed_count / len(metrics)) * 100 if metrics else 100.0
            if type_safety_index < type_safety_threshold:
                penalty = 20
                score -= penalty
                details.append(f"Type Safety Index {type_safety_index:.0f}% < {type_safety_threshold}% (-{penalty})")
        return score, details, type_safety_index

    # --- AST Traversal & Analysis ---

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        if not HAS_TREE_SITTER:
            return []
        try:
            with open(filepath, "rb") as f:
                source_bytes = f.read()
        except FileNotFoundError:
            return []

        language = self._get_language(filepath)
        if not language:
            return []

        parser = Parser(language)
        tree = parser.parse(source_bytes)
        stats: List[FunctionMetric] = []
        visited = set()
        self._visit_tree(tree.root_node, visited, stats, filepath)
        return stats

    def _visit_tree(self, node: Node, visited: set, stats: List[FunctionMetric], filepath: str) -> None:
        if node.id in visited:
            return
        visited.add(node.id)

        if node.type in ("function_declaration", "function_expression", "arrow_function", "method_definition"):
            self._analyze_function(node, stats, filepath)

        for child in node.children:
            self._visit_tree(child, visited, stats, filepath)

    def _analyze_function(self, node: Node, stats: List[FunctionMetric], filepath: str):
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1
        name = self._get_function_name(node)

        complexity = self._calculate_complexity(node)
        depth = self._calculate_nesting_depth(node)
        acl = self.calculate_acl(complexity, loc, depth)
        is_typed = self._check_is_typed(node)

        stats.append({
            "name": name,
            "lineno": start_line,
            "complexity": complexity,
            "loc": loc,
            "acl": acl,
            "is_typed": is_typed,
            "nesting_depth": depth,
        })

    def _get_function_name(self, node: Node) -> str:
        name = "anonymous"
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8")
        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8")
        return name

    def _calculate_complexity(self, node: Node) -> float:
        return 1.0 + self._count_branching_nodes(node)

    def _count_branching_nodes(self, node: Node) -> float:
        count = 0.0
        for child in node.children:
            count += self._visit_complexity(child)
        return count

    def _visit_complexity(self, n: Node) -> float:
        count = 0.0
        if n.type in ("if_statement", "for_statement", "for_in_statement", "while_statement", "do_statement", "switch_case", "catch_clause", "conditional_expression"):
            count += 1.0
        elif n.type == "binary_expression":
            operator = n.child_by_field_name("operator") or (n.child(1) if n.child_count >= 2 else None)
            if operator and operator.text.decode("utf-8") in ("&&", "||"):
                count += 1.0

        for child in n.children:
            if child.type not in ("function_declaration", "function_expression", "arrow_function", "method_definition"):
                count += self._visit_complexity(child)
        return count

    def _calculate_nesting_depth(self, node: Node) -> int:
        body = node.child_by_field_name("body")
        if body:
            return self._visit_depth(body, 0)
        else:
            max_d = 0
            for child in node.children:
                d = self._visit_depth(child, 0)
                if d > max_d:
                    max_d = d
            return max_d

    def _visit_depth(self, n: Node, current_depth: int) -> int:
        max_depth = current_depth
        if n.type in ("if_statement", "for_statement", "for_in_statement", "while_statement", "do_statement", "try_statement", "catch_clause", "switch_statement"):
            next_depth = current_depth + 1
        else:
            next_depth = current_depth

        if next_depth > max_depth:
            max_depth = next_depth

        for child in n.children:
            if child.type not in ("function_declaration", "function_expression", "arrow_function", "method_definition"):
                d = self._visit_depth(child, next_depth)
                if d > max_depth:
                    max_depth = d
        return max_depth

    def _check_is_typed(self, node: Node) -> bool:
        if node.child_by_field_name("return_type"):
            return True
        params = node.child_by_field_name("parameters")
        if params:
            for i in range(params.child_count):
                if self._has_type_annotation(params.child(i)):
                    return True
        return False

    def _has_type_annotation(self, node: Node) -> bool:
        if node.type == "type_annotation":
            return True
        for child in node.children:
            if self._has_type_annotation(child):
                return True
        return False

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        return (depth * 2.0) + (complexity * 1.5) + (loc / 50.0)

    def _get_loc(self, filepath: str) -> int:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except (FileNotFoundError, UnicodeDecodeError):
            return 0