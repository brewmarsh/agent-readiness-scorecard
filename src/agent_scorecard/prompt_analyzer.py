import re
from typing import Dict, Any


class PromptAnalyzer:
    """Analyzes text prompts for LLM best practices."""

    HEURISTICS: Dict[str, Dict[str, Any]] = {
        "role_definition": {
            "pattern": r"(?i)(you are|act as|your role)",
            "improvement": "Add a clear persona (e.g., 'You are a Python Expert') to ground the model's latent space.",
            "critical": True,
            "weight": 25,
        },
        "cognitive_scaffolding": {
            "pattern": r"(?i)(step by step|reasoning|think)",
            "improvement": "Add Chain-of-Thought instructions ('Think step by step') to improve complex reasoning.",
            "critical": False,
            "weight": 25,
        },
        "delimiter_hygiene": {
            "pattern": r"(<[^>]+>|'''|\"\"\"|```|\{\{.*?\}\})",
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
            "pattern": r"(?i)(don't|do not|never)",
            "improvement": "Refactor negative constraints ('Don't do X') into positive instructions ('Do Y instead') for better adherence.",
            "critical": False,
            "penalty": 10,
        },
    }

    def analyze(self, text: str) -> Dict[str, Any]:
        """Evaluates a raw string against five key dimensions."""
        results = {}
        improvements = []
        score = 0

        # Positive heuristics
        for key in [
            "role_definition",
            "cognitive_scaffolding",
            "delimiter_hygiene",
            "few_shot",
        ]:
            h = self.HEURISTICS[key]
            pattern = str(h["pattern"])
            weight = int(h["weight"])
            if re.search(pattern, text):
                results[key] = True
                score += weight
            else:
                results[key] = False
                improvements.append(str(h["improvement"]))

        # Negative constraints (Warning)
        h = self.HEURISTICS["negative_constraints"]
        pattern = str(h["pattern"])
        penalty = int(h["penalty"])
        if re.search(pattern, text):
            results["negative_constraints"] = False  # Flagged as an issue
            score -= penalty
            improvements.append(str(h["improvement"]))
        else:
            results["negative_constraints"] = True

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        return {"score": score, "results": results, "improvements": improvements}
