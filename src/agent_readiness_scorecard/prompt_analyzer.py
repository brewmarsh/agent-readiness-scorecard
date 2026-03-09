import re
from typing import List, Dict, TypedDict, cast


class HeuristicConfig(TypedDict, total=False):
    pattern: str
    improvement: str
    critical: bool
    weight: int
    penalty: int


class PromptAnalysisResult(TypedDict):
    score: int
    results: Dict[str, bool]
    improvements: List[str]


class PromptAnalyzer:
    """Analyzes text prompts for LLM best practices using structural heuristics."""

    # Centralized heuristics dictionary for easier maintenance and testing
    HEURISTICS: Dict[str, HeuristicConfig] = {
        "role_definition": {
            "pattern": r"(?i)(you are|act as|your role)",
            "improvement": "Add a clear persona (e.g., 'You are a Python Expert') to ground the model's latent space.",
            "critical": True,
            "weight": 25,
        },
        "cognitive_scaffolding": {
            "pattern": r"(?i)(step by step|reasoning|think|plan|step \d+|phase \d+)",
            "improvement": "Add Chain-of-Thought instructions ('Think step by step') to improve complex reasoning.",
            "critical": False,
            "weight": 25,
        },
        "delimiter_hygiene": {
            "pattern": r"(?i)(<[^>]+>|'''|\"\"\"|```|\{\{.*?\}\})",
            "improvement": "Use delimiters (like XML tags or triple quotes) to separate instructions from input data.",
            "critical": False,
            "weight": 25,
        },
        "few_shot": {
            "pattern": r"(?i)(example:|input:.*?output:)",
            "improvement": "Include 1-3 examples (Few-Shot) to guide the model on format and style.",
            "critical": False,
            "weight": 25,
        },
        "negative_constraints": {
            "pattern": r"(?i)(not|don't|do not|never)",
            "improvement": "Refactor negative constraints ('Don't do X') into positive instructions ('Do Y instead') for better adherence.",
            "critical": False,
            "penalty": 10,
        },
    }

    def analyze(self, text: str) -> PromptAnalysisResult:
        """
        Evaluates a raw string against key prompt engineering dimensions.

        Args:
            text (str): The prompt text to analyze.

        Returns:
            PromptAnalysisResult: A dictionary containing the score, results, and improvements.
        """
        if not text or not text.strip():
            return {"score": 0, "results": {}, "improvements": ["Prompt is empty."]}

        # 1. Standard heuristics (Simple Regex)
        score, results, improvements = self._evaluate_standard_heuristics(text)

        # 2. Context-Aware heuristics (Few-Shot & Negative Constraints)
        score = self._evaluate_contextual_heuristics(text, results, improvements, score)

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        return {"score": score, "results": results, "improvements": improvements}

    def _evaluate_standard_heuristics(
        self, text: str
    ) -> tuple[int, Dict[str, bool], List[str]]:
        """Evaluates standard regex-based heuristics."""
        results: Dict[str, bool] = {}
        improvements: List[str] = []
        score = 0

        for key in ["role_definition", "cognitive_scaffolding", "delimiter_hygiene"]:
            h = cast(HeuristicConfig, self.HEURISTICS[key])
            pattern = cast(str, h["pattern"])
            if re.search(pattern, text):
                results[key] = True
                score += cast(int, h["weight"])
            else:
                results[key] = False
                improvements.append(cast(str, h["improvement"]))

        return score, results, improvements

    def _evaluate_contextual_heuristics(
        self, text: str, results: Dict[str, bool], improvements: List[str], score: int
    ) -> int:
        """Evaluates heuristics that require context awareness (Few-Shot and Negative Constraints)."""
        # Few-Shot Detection
        if self._check_few_shot(text):
            results["few_shot"] = True
            score += cast(int, self.HEURISTICS["few_shot"]["weight"])
        else:
            results["few_shot"] = False
            improvements.append(cast(str, self.HEURISTICS["few_shot"]["improvement"]))

        # Negative Constraint Detection
        if self._check_negative_constraints(text):
            results["negative_constraints"] = False  # Issue found
            score -= cast(int, self.HEURISTICS["negative_constraints"]["penalty"])
            improvements.append(
                cast(str, self.HEURISTICS["negative_constraints"]["improvement"])
            )
        else:
            results["negative_constraints"] = True  # No issue

        return score

    def _check_few_shot(self, text: str) -> bool:
        """
        Heuristic for detecting few-shot examples with context awareness.

        Args:
            text (str): The prompt text to check.

        Returns:
            bool: True if few-shot examples are likely present.
        """
        h = cast(HeuristicConfig, self.HEURISTICS["few_shot"])
        pattern = cast(str, h["pattern"])

        # 1. Standard patterns (Example: or Input/Output)
        if re.search(pattern, text, re.DOTALL):
            return True

        # 2. Markdown Header with "Example" or "Examples"
        if re.search(r"(?m)^#+.*(Example|Examples)", text, re.IGNORECASE):
            return True

        # 3. Markdown code blocks preceded by lines containing "example" or "sample"
        return self._has_example_code_blocks(text)

    def _has_example_code_blocks(self, text: str) -> bool:
        """Detects markdown code blocks preceded by lines containing 'example' or 'sample'."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"(?i)(example|sample)", line):
                if self._has_code_block_after_example(lines, i):
                    return True
        return False

    def _has_code_block_after_example(self, lines: List[str], index: int) -> bool:
        """Checks if a code block starts within the next two lines of a given index."""
        for j in range(index + 1, min(index + 3, len(lines))):
            if lines[j].strip().startswith("```"):
                return True
        return False

    def _check_negative_constraints(self, text: str) -> bool:
        """
        Heuristic for detecting negative constraints with context awareness.

        Args:
            text (str): The prompt text to check.

        Returns:
            bool: True if a penalty-worthy violation is found.
        """
        h = cast(HeuristicConfig, self.HEURISTICS["negative_constraints"])
        pattern = cast(str, h["pattern"])
        threshold_20 = len(text) * 0.2

        for match in re.finditer(pattern, text):
            if self._is_penalty_worthy_negative_constraint(text, match, threshold_20):
                return True

        return False

    def _is_penalty_worthy_negative_constraint(
        self, text: str, match: re.Match, threshold_20: float
    ) -> bool:
        """Evaluates if a specific regex match represents a penalty-worthy negative constraint."""
        # Rule 1: Ignore negative words in the first 20% (Context setting phase)
        if match.start() < threshold_20:
            return False

        line_content = self._get_line_at_match(text, match)

        # Rule 2: Ignore standard "anti-pattern" descriptions (e.g., "Currently, it does not work")
        if re.search(r"(?i)currently.*not", line_content):
            return False

        # Rule 3: Only flag if they appear in imperative instruction sections (lists/numbers)
        return bool(re.match(r"^(\*|\-|\d+\.)", line_content))

    def _get_line_at_match(self, text: str, match: re.Match) -> str:
        """Retrieves the full line content containing the given regex match."""
        start_of_line = text.rfind("\n", 0, match.start()) + 1
        end_of_line = text.find("\n", match.end())
        if end_of_line == -1:
            end_of_line = len(text)
        return text[start_of_line:end_of_line].strip()
