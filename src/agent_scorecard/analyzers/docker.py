from typing import Dict, Any, List, Tuple, Optional
from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS


class DockerAnalyzer(BaseAnalyzer):
    """
    Docker-specific implementation of the BaseAnalyzer.
    Evaluates Agent Cognitive Load (ACL) based on instruction complexity.
    """

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

        # Dockerfile bloat penalty: > 100 lines
        if loc > 100:
            bloat_penalty = (loc - 100) // 10
            if bloat_penalty > 0:
                score -= bloat_penalty
                details.append(f"Bloated Dockerfile: {loc} lines (-{bloat_penalty})")

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
            details.append(f"{red_count} Red ACL instructions detected (-{penalty})")

        if yellow_count > 0:
            penalty = yellow_count * 5
            score -= penalty
            details.append(f"{yellow_count} Yellow ACL instructions detected (-{penalty})")

        # "Type Safety" acts as "Best Practices Compliance"
        typed_count = sum(1 for m in metrics if m["is_typed"])
        type_safety_index = (typed_count / len(metrics)) * 100

        if type_safety_index < 90.0:
            penalty = 20
            score -= penalty
            details.append(
                f"Best Practices Compliance {type_safety_index:.0f}% < 90% (-{penalty})"
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
        Returns statistics for each instruction in the Dockerfile.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return []

        instructions = self._parse_instructions(content)
        stats: List[FunctionMetric] = []

        for instr in instructions:
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

        return stats

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
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(
                    1 for line in f if line.strip() and not line.strip().startswith("#")
                )
        except (UnicodeDecodeError, FileNotFoundError):
            return 0

    def _parse_instructions(self, content: str) -> List[Dict[str, Any]]:
        """
        Parses Dockerfile content into a list of instructions, handling line continuations.
        """
        lines = content.splitlines()
        instructions = []
        current_instruction = []
        start_lineno = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            if not current_instruction:
                start_lineno = i + 1

            current_instruction.append(line)

            # Check for line continuation (backslash at the end)
            # Note: Comments can be inside multi-line instructions if escaped,
            # but standard Dockerfile comments (#) end the line logic usually unless inside quotes?
            # Actually, Docker treats # as comment only at the start of a line (or processed line).
            # But line continuation with \ extends the line.
            # We'll use a simple heuristic: if it ends with \, continue.

            if stripped.endswith("\\"):
                # It continues
                pass
            else:
                # End of instruction
                full_text = "\n".join(current_instruction)
                # Extract instruction name (first word)
                parts = full_text.split(None, 1)
                instr_name = parts[0].upper() if parts else "UNKNOWN"

                instructions.append(
                    {
                        "instruction": instr_name,
                        "content": full_text,
                        "lineno": start_lineno,
                        "end_lineno": i + 1,
                    }
                )
                current_instruction = []

            i += 1

        return instructions

    def _check_best_practices(self, instruction: str, content: str) -> bool:
        """
        Checks for Docker best practices.
        Returns True if compliant, False otherwise.
        """
        instruction = instruction.upper()

        if instruction == "FROM":
            # Check for latest tag
            parts = content.split()
            if len(parts) > 1:
                # FROM <image> [AS <name>]
                # FROM <image>[:<tag>] [AS <name>]
                image_part = parts[1]
                # handle platform flag if present? FROM --platform=...
                # Assuming simple case for now or complex regex.
                # Let's check if parts[1] is NOT --something
                if image_part.startswith("--"):
                    if len(parts) > 2:
                        image_part = parts[2]
                    else:
                        return True  # weird parsing

                if image_part.lower() != "scratch":
                    if ":" not in image_part or image_part.endswith(":latest"):
                        return False

        if instruction == "ADD":
            # Prefer COPY over ADD
            return False

        if instruction == "RUN":
            if "sudo " in content:
                return False
            if "apt-get upgrade" in content:
                return False

        return True
