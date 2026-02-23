import tiktoken
from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS


class MarkdownAnalyzer(BaseAnalyzer):
    """
    Markdown-specific implementation of the BaseAnalyzer.
    Evaluates Agent Cognitive Load (ACL) based on header depth and token density.
    """

    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """
        Calculates score based on the selected profile and Agent Readiness spec for Markdown.
        """
        p_thresholds = profile.get("thresholds", {})

        if thresholds is None:
            thresholds = {
                "acl_yellow": p_thresholds.get(
                    "acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]
                ),
                "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
                "token_limit": p_thresholds.get(
                    "token_limit", DEFAULT_THRESHOLDS["token_limit"]
                ),
            }

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100
        details = []

        # Markdown bloat penalty: > 500 lines
        if loc > 500:
            bloat_penalty = (loc - 500) // 25
            if bloat_penalty > 0:
                score -= bloat_penalty
                details.append(f"Bloated Documentation: {loc} lines (-{bloat_penalty})")

        if not metrics:
            return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
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
            details.append(
                f"{red_count} Red ACL sections detected. Ensure headers group content logically (-{penalty})"
            )

        if yellow_count > 0:
            penalty = yellow_count * 5
            score -= penalty
            details.append(
                f"{yellow_count} Yellow ACL sections detected. Consider breaking down large documentation chunks (-{penalty})"
            )

        # Markdown is always "typed" in this context
        type_safety_index = 100.0
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
        Returns statistics for each header section in the markdown file.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, FileNotFoundError):
            return []

        stats: List[FunctionMetric] = []
        enc = tiktoken.get_encoding("cl100k_base")

        sections = []
        current_header = None
        current_content = []
        header_lineno = 0

        for i, line in enumerate(lines):
            if line.startswith("#"):
                if current_header is not None:
                    sections.append((current_header, header_lineno, current_content))

                current_header = line.strip()
                header_lineno = i + 1
                current_content = [line]
            else:
                if current_header is not None:
                    current_content.append(line)
                else:
                    # Content before the first header
                    # We'll treat it as an implicit "Introduction" section
                    current_header = "# Introduction"
                    header_lineno = 1
                    current_content = [line]

        if current_header is not None:
            sections.append((current_header, header_lineno, current_content))

        for header, lineno, content_lines in sections:
            content = "".join(content_lines)
            tokens = len(enc.encode(content))

            # Nesting depth is the number of # symbols
            nesting_depth = 0
            for char in header:
                if char == "#":
                    nesting_depth += 1
                else:
                    break

            loc = len(content_lines)
            # ACL = (Header Depth * 1.5) + (Tokens in Section / 100)
            acl = self.calculate_acl(float(tokens), loc, nesting_depth)

            stats.append({
                "name": header,
                "lineno": lineno,
                "complexity": tokens / 100.0, # Use token density as complexity for reporting
                "loc": loc,
                "acl": acl,
                "is_typed": True,
                "nesting_depth": nesting_depth,
            })

        return stats

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL) for Markdown.
        Formula: (Header Depth * 1.5) + (Tokens in Section / 100)
        Note: complexity argument is used to pass token count.
        """
        return (depth * 1.5) + (complexity / 100.0)

    def _get_loc(self, filepath: str) -> int:
        """
        Returns lines of code excluding empty lines.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except (UnicodeDecodeError, FileNotFoundError):
            return 0
