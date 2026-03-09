from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS


class DockerAnalyzer(BaseAnalyzer):
    """
    Docker-specific implementation of the BaseAnalyzer.
    Evaluates Agent Cognitive Load (ACL) based on instruction complexity.
    """

    @property
    def language(self) -> str:
        return "Docker"

    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """
        Calculates score based on the selected profile and Agent Readiness spec for Dockerfiles.
        """
        p_thresholds = profile.get("thresholds", {})
        thresholds = thresholds or self._get_default_thresholds(p_thresholds)

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100
        details: List[str] = []

        score = self._apply_bloat_penalty(score, details, loc)

        if not metrics:
            return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

        token_limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])
        score = self._apply_token_penalty(score, details, cumulative_tokens, token_limit)

        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
        score = self._apply_acl_penalties(score, details, metrics, acl_yellow, acl_red)

        score, type_safety_index = self._apply_type_safety_penalty(
            score, details, metrics
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

    def _get_default_thresholds(self, p_thresholds: Dict[str, Any]) -> Dict[str, Any]:
        """Returns default thresholds merged with profile overrides."""
        return {
            "acl_yellow": p_thresholds.get(
                "acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]
            ),
            "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
            "token_limit": p_thresholds.get(
                "token_limit", DEFAULT_THRESHOLDS["token_limit"]
            ),
        }

    def _apply_bloat_penalty(self, score: int, details: List[str], loc: int) -> int:
        """Applies penalty for bloated Dockerfiles (> 100 lines)."""
        if loc > 100:
            bloat_penalty = (loc - 100) // 10
            if bloat_penalty > 0:
                score -= bloat_penalty
                details.append(f"Bloated Dockerfile: {loc} lines (-{bloat_penalty})")
        return score

    def _apply_token_penalty(
        self, score: int, details: List[str], cumulative_tokens: int, token_limit: int
    ) -> int:
        """Applies penalty for exceeding token budget."""
        if cumulative_tokens > token_limit:
            penalty = 15
            score -= penalty
            details.append(
                f"Cumulative Token Budget Exceeded: {cumulative_tokens:,} > {token_limit:,} (-{penalty})"
            )
        return score

    def _apply_acl_penalties(
        self,
        score: int,
        details: List[str],
        metrics: List[FunctionMetric],
        acl_yellow: float,
        acl_red: float,
    ) -> int:
        """Applies penalties for instructions with high ACL."""
        red_count = sum(1 for m in metrics if m["acl"] > acl_red)
        yellow_count = sum(1 for m in metrics if acl_yellow < m["acl"] <= acl_red)

        if red_count > 0:
            penalty = red_count * 15
            score -= penalty
            details.append(f"{red_count} Red ACL instructions detected (-{penalty})")

        if yellow_count > 0:
            penalty = yellow_count * 5
            score -= penalty
            details.append(
                f"{yellow_count} Yellow ACL instructions detected (-{penalty})"
            )
        return score

    def _apply_type_safety_penalty(
        self, score: int, details: List[str], metrics: List[FunctionMetric]
    ) -> Tuple[int, float]:
        """Applies penalty for low best practice compliance (type safety)."""
        typed_count = sum(1 for m in metrics if m["is_typed"])
        type_safety_index = (typed_count / len(metrics)) * 100

        if type_safety_index < 90.0:
            penalty = 20
            score -= penalty
            details.append(
                f"Best Practices Compliance {type_safety_index:.0f}% < 90% (-{penalty})"
            )
        return score, type_safety_index

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        """
        Returns statistics for each instruction in the Dockerfile.
        """
        content = self._read_file_safe(filepath)
        if content is None:
            return []

        instructions = self._parse_instructions(content)
        stats: List[FunctionMetric] = []

        for instr in instructions:
            self._process_instruction_metrics(stats, instr)

        return stats

    def _process_instruction_metrics(
        self, stats: List[FunctionMetric], instr: Dict[str, Any]
    ) -> None:
        """Helper to process metrics for a single instruction."""
        name = instr["instruction"]
        full_content = instr["content"]
        lineno = instr["lineno"]

        # Lines in the instruction
        loc = instr["end_lineno"] - lineno + 1

        # Count chained commands (&&, ;)
        chained_commands = full_content.count("&&") + full_content.count(";")

        # Complexity = chained commands + 1 (base complexity)
        complexity = float(chained_commands + 1)

        # Nesting Depth (0 for now, could be 1 for FROM stages if we wanted)
        nesting_depth = 0

        acl = self.calculate_acl(complexity, loc, nesting_depth)

        # Best Practices Check
        is_compliant = self._check_best_practices(name, full_content)

        stats.append(
            {
                "name": name,
                "lineno": lineno,
                "complexity": complexity,
                "loc": loc,
                "acl": acl,
                "is_typed": is_compliant,
                "nesting_depth": nesting_depth,
            }
        )

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL) for Dockerfile instructions.
        Formula: (Chained Commands * 1.5) + (Lines * 0.5)
        Note: complexity argument passes (chained_commands + 1).
        """
        chained_commands = max(0, complexity - 1.0)
        return (chained_commands * 1.5) + (loc * 0.5)

    def _get_loc(self, filepath: str) -> int:
        """
        Returns lines of code excluding empty lines and comments.
        """
        content = self._read_file_safe(filepath)
        if content is None:
            return 0
        return sum(1 for line in content.splitlines() if self._is_code_line(line))

    def _is_code_line(self, line: str) -> bool:
        """Checks if a line is a code line (not empty and not a comment)."""
        stripped = line.strip()
        return bool(stripped and not stripped.startswith("#"))

    def _read_file_safe(self, filepath: str) -> Optional[str]:
        """Safely reads file content, returning None on error."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return None

    def _parse_instructions(self, content: str) -> List[Dict[str, Any]]:
        """
        Parses Dockerfile content into a list of instructions, handling line continuations.
        """
        instructions: List[Dict[str, Any]] = []
        current_instruction: List[str] = []
        start_lineno = 0

        for i, line in enumerate(content.splitlines()):
            start_lineno = self._process_parsing_line(
                i, line, instructions, current_instruction, start_lineno
            )

        return instructions

    def _process_parsing_line(
        self,
        i: int,
        line: str,
        instructions: List[Dict[str, Any]],
        current_instruction: List[str],
        start_lineno: int,
    ) -> int:
        """Processes a single line for instruction parsing."""
        stripped = line.strip()
        if self._is_ignorable_line(stripped):
            return start_lineno

        if not current_instruction:
            start_lineno = i + 1

        current_instruction.append(line)

        if not stripped.endswith("\\"):
            self._finalize_instruction(
                instructions, current_instruction, start_lineno, i + 1
            )
            current_instruction.clear()

        return start_lineno

    def _is_ignorable_line(self, stripped: str) -> bool:
        """Determines if a line should be ignored during parsing."""
        return not stripped or stripped.startswith("#")

    def _finalize_instruction(
        self,
        instructions: List[Dict[str, Any]],
        current_instruction: List[str],
        start_lineno: int,
        end_lineno: int,
    ) -> None:
        """Helper to finalize an instruction and add it to the list."""
        full_text = "\n".join(current_instruction)
        # Extract instruction name (first word)
        parts = full_text.split(None, 1)
        instr_name = parts[0].upper() if parts else "UNKNOWN"

        instructions.append(
            {
                "instruction": instr_name,
                "content": full_text,
                "lineno": start_lineno,
                "end_lineno": end_lineno,
            }
        )

    def _check_best_practices(self, instruction: str, content: str) -> bool:
        """
        Checks for Docker best practices.
        Returns True if compliant, False otherwise.
        """
        instr = instruction.upper()
        if instr == "FROM":
            return self._check_from_instruction(content)
        if instr == "ADD":
            return self._check_add_instruction()
        if instr == "RUN":
            return self._check_run_instruction(content)
        return True

    def _check_from_instruction(self, content: str) -> bool:
        """Check FROM instruction for best practices (e.g., no :latest tag)."""
        parts = content.split()
        if len(parts) <= 1:
            return True

        image_part = parts[1]
        # Handle FROM --platform=... image
        if image_part.startswith("--") and len(parts) > 2:
            image_part = parts[2]

        if image_part.lower() == "scratch":
            return True

        if ":" not in image_part or image_part.endswith(":latest"):
            return False
        return True

    def _check_add_instruction(self) -> bool:
        """Check ADD instruction (prefer COPY)."""
        return False

    def _check_run_instruction(self, content: str) -> bool:
        """Check RUN instruction for best practices."""
        if "sudo " in content:
            return False
        if "apt-get upgrade" in content:
            return False
        return True
