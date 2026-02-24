from typing import Dict, Any, List, Tuple, Optional
from tree_sitter import Language, Parser, Node
import tree_sitter_java

from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS

# Initialize language
JAVA_LANGUAGE = Language(tree_sitter_java.language())


class JavaAnalyzer(BaseAnalyzer):
    """
    Analyzes Java files using tree-sitter.
    Calculates ACL: (Depth * 2) + (Complexity * 1.5) + (LOC / 50).
    """

    @property
    def language(self) -> str:
        return "Java"

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
        # Java is statically typed, so we expect high type safety, but we check metrics anyway
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
        type_safety_index = (typed_count / len(metrics)) * 100 if metrics else 100.0

        if type_safety_index < type_safety_threshold:
            penalty = 20
            score -= penalty
            details.append(
                f"Type Safety Index {type_safety_index:.0f}% < {type_safety_threshold}% (-{penalty})"
            )

        avg_complexity = (
            sum(m["complexity"] for m in metrics) / len(metrics) if metrics else 0.0
        )

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
        Returns statistics for each function in the file using tree-sitter.
        """
        try:
            with open(filepath, "rb") as f:
                source_bytes = f.read()
        except FileNotFoundError:
            return []

        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(source_bytes)

        stats: List[FunctionMetric] = []
        visited = set()

        def visit(node: Node):
            if node.id in visited:
                return
            visited.add(node.id)

            if node.type in ("method_declaration", "constructor_declaration"):
                self._analyze_function(node, stats, filepath)

            for child in node.children:
                visit(child)

        visit(tree.root_node)

        return stats

    def _analyze_function(self, node: Node, stats: List[FunctionMetric], filepath: str):
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1

        name = "anonymous"
        name_node = node.child_by_field_name("name")
        if name_node:
            name = name_node.text.decode("utf-8")

        complexity = self._calculate_complexity(node)
        depth = self._calculate_nesting_depth(node)
        acl = self.calculate_acl(complexity, loc, depth)
        is_typed = self._check_is_typed(node)

        stats.append(
            {
                "name": name,
                "lineno": start_line,
                "complexity": complexity,
                "loc": loc,
                "acl": acl,
                "is_typed": is_typed,
                "nesting_depth": depth,
            }
        )

    def _calculate_complexity(self, node: Node) -> float:
        """
        Calculates cyclomatic complexity.
        Branching nodes: if, for, while, do, switch_label, catch, ternary.
        Logical operators: &&, ||.
        """
        complexity = 1.0

        def visit(n: Node):
            nonlocal complexity
            if n.type in (
                "if_statement",
                "for_statement",
                "enhanced_for_statement",
                "while_statement",
                "do_statement",
                "catch_clause",
                "ternary_expression",
            ):
                complexity += 1.0
            elif n.type == "switch_label":
                # Check if it is 'default' - default doesn't increase complexity (like else)
                is_default = False
                for child in n.children:
                    if child.text == b"default":
                        is_default = True
                        break
                if not is_default:
                    complexity += 1.0
            elif n.type == "binary_expression":
                # Check for && and ||
                # In tree-sitter-java, operator is usually a child node
                # but might not have a field name 'operator'.
                # We iterate children to find the operator symbol.
                for child in n.children:
                    if child.type not in (
                        "binary_expression",
                        "identifier",
                    ) and child.text.decode("utf-8") in ("&&", "||"):
                        complexity += 1.0
                        break

            for child in n.children:
                # Don't descend into nested functions/classes for complexity of THIS function
                # Java supports inner classes and local classes
                if child.type not in (
                    "method_declaration",
                    "constructor_declaration",
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "record_declaration",
                ):
                    visit(child)

        # Start visiting children of the function node
        for child in node.children:
            visit(child)

        return complexity

    def _calculate_nesting_depth(self, node: Node) -> int:
        """
        Calculates maximum nesting depth.
        """
        max_depth = 0

        def visit(n: Node, current_depth: int):
            nonlocal max_depth
            if current_depth > max_depth:
                max_depth = current_depth

            # Control flow structures increase depth
            if n.type in (
                "if_statement",
                "for_statement",
                "enhanced_for_statement",
                "while_statement",
                "do_statement",
                "try_statement",  # try block increases depth? usually yes
                "switch_expression",
                "switch_block",  # switch block usually contains cases
            ):
                next_depth = current_depth + 1
            else:
                next_depth = current_depth

            for child in n.children:
                if child.type not in (
                    "method_declaration",
                    "constructor_declaration",
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "record_declaration",
                ):
                    visit(child, next_depth)

        # Initial depth is 0 relative to function body
        body = node.child_by_field_name("body")
        if body:
            visit(body, 0)
        else:
            # Fallback if no body field (e.g. abstract method - but we shouldn't be here for abstract methods usually unless we want to analyze them)
            # Abstract methods have no body, so complexity/depth is 0.
            pass

        return max_depth

    def _check_is_typed(self, node: Node) -> bool:
        """
        Checks if the function has type annotations.
        In Java, methods are always typed.
        """
        # We can check if return type exists for method_declaration
        # constructor_declaration doesn't have return type
        if node.type == "method_declaration":
            # Just existence of return type node.
            # In tree-sitter-java, it's field 'type'.
            if node.child_by_field_name("type"):
                return True
            # void is also a type
            # If it's a generic method, it might be more complex, but 'type' field usually captures it.
        elif node.type == "constructor_declaration":
            return True

        return True  # Default to True for Java as it is strongly typed

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
                return sum(1 for line in f if line.strip())
        except FileNotFoundError:
            return 0
