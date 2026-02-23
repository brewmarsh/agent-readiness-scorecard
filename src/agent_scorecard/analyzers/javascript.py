import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Node
from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS

# Initialize languages
JS_LANGUAGE = Language(tsjs.language())
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())


class JavascriptAnalyzer(BaseAnalyzer):
    """
    JavaScript and TypeScript specific implementation of the BaseAnalyzer using tree-sitter.
    """

    def __init__(self) -> None:
        """Initialize the analyzer with tree-sitter parser."""
        self.parser: Optional[Parser] = None

    def _get_language(self, filepath: str) -> Language:
        """Return the appropriate tree-sitter language for the given file extension."""
        if filepath.endswith((".ts", ".tsx")):
            if filepath.endswith(".tsx"):
                return TSX_LANGUAGE
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
            with open(filepath, "rb") as f:
                content = f.read()

            language = self._get_language(filepath)
            self.parser = Parser(language)
            tree = self.parser.parse(content)
        except Exception:
            return []

        stats: List[FunctionMetric] = []

        function_nodes = [
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        ]

        def traverse(node: Node) -> None:
            if node.type in function_nodes:
                name = "anonymous"
                if node.type in ["function_declaration", "method_definition"]:
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        name = content[
                            name_node.start_byte : name_node.end_byte
                        ].decode("utf8")
                elif node.type in ["function_expression", "arrow_function"]:
                    # Try to find name from variable declaration
                    parent = node.parent
                    if parent and parent.type == "variable_declarator":
                        name_node = parent.child_by_field_name("name")
                        if name_node:
                            name = content[
                                name_node.start_byte : name_node.end_byte
                            ].decode("utf8")

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                f_loc = end_line - start_line + 1

                complexity = self._calculate_complexity(node)
                nesting_depth = self._calculate_nesting_depth(node)
                acl = self.calculate_acl(float(complexity), f_loc, nesting_depth)
                is_typed = self._check_is_typed(node, filepath)

                stats.append(
                    {
                        "name": name,
                        "lineno": start_line,
                        "complexity": float(complexity),
                        "loc": f_loc,
                        "acl": acl,
                        "is_typed": is_typed,
                        "nesting_depth": nesting_depth,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return stats

    def _calculate_complexity(self, node: Node) -> int:
        """Calculates cyclomatic complexity for a function node."""
        complexity = 1
        branching_nodes = [
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_case",
            "catch_clause",
            "ternary_expression",
        ]

        function_nodes = [
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        ]

        def count_branches(n: Node) -> None:
            nonlocal complexity
            if n.type in branching_nodes:
                complexity += 1

            # Handle logical expressions with && or ||
            if n.type == "binary_expression":
                # Find operator child
                for child in n.children:
                    if child.type in ["&&", "||"]:
                        complexity += 1
                        break

            for child in n.children:
                # Don't recurse into nested functions
                if child.type not in function_nodes:
                    count_branches(child)

        # Start counting from body or children
        body = node.child_by_field_name("body")
        if body:
            count_branches(body)
        else:
            for child in node.children:
                if child.type not in ["parameters", "type_annotation"]:
                    count_branches(child)

        return complexity

    def _calculate_nesting_depth(self, node: Node) -> int:
        """Calculates maximum nesting depth for a function node."""
        nesting_nodes = [
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_statement",
            "catch_clause",
            "try_statement",
        ]

        function_nodes = [
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        ]

        def get_max_depth(n: Node, current_depth: int) -> int:
            max_d = current_depth

            for child in n.children:
                # Don't recurse into nested functions
                if child.type in function_nodes:
                    continue

                new_depth = current_depth
                if child.type in nesting_nodes:
                    new_depth += 1

                max_d = max(max_d, get_max_depth(child, new_depth))

            return max_d

        body = node.child_by_field_name("body")
        if body:
            return get_max_depth(body, 0)

        return 0

    def _check_is_typed(self, node: Node, filepath: str) -> bool:
        """Checks if a function has type hints (TypeScript only)."""
        if not filepath.endswith((".ts", ".tsx")):
            return False

        # Check return type annotation
        if any(c.type == "type_annotation" for c in node.children):
            return True

        # Check parameter type annotations
        params = node.child_by_field_name("parameters")
        if not params:
            # Maybe it's formal_parameters (different TS versions/parsers)
            for child in node.children:
                if child.type == "formal_parameters":
                    params = child
                    break

        if params:
            for param in params.children:
                if param.type in [
                    "required_parameter",
                    "optional_parameter",
                    "parameter",
                ]:
                    if any(c.type == "type_annotation" for c in param.children):
                        return True

        return False

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
                count = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(("//", "/*", "*")):
                        continue
                    count += 1
                return count
        except (UnicodeDecodeError, FileNotFoundError):
            return 0
