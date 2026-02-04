import re
from typing import List, Dict, Any

class PromptAnalyzer:
    """Analyzes text prompts for LLM best practices using structural heuristics."""

    # Centralized heuristics dictionary for easier maintenance and testing
    HEURISTICS = {
        "role_definition": {
            "pattern": r"(?i)(you are|act as|your role)",
            "improvement": "Add a clear persona (e.g., 'You are a Python Expert') to ground the model's latent space.",
            "critical": True,
            "weight": 25
        },
        "cognitive_scaffolding": {
            "pattern": r"(?i)(step[- ]by[- ]step|think carefully|reasoning|stepwise)",
            "improvement": "Add Chain-of-Thought instructions ('Think step by step') to improve complex reasoning.",
            "critical": False,
            "weight": 25
        },
        "delimiter_hygiene": {
            "pattern": r"(```|---|===|<[^>]+>)",
            "improvement": "Use delimiters (like XML tags or triple quotes) to separate instructions from input data.",
            "critical": False,
            "weight": 25
        },
        "few_shot": {
            "pattern": r"(?i)(\bexample\b|input:.*?output:|user:|assistant:)",
            "improvement": "Include 1-3 examples (Few-Shot) to guide the model on format and style.",
            "critical": False,
            "weight": 25
        },
        "negative_constraints": {
            "pattern": r"(?i)\b(do not|don't|never|avoid)\b",
            "improvement": "Refactor negative constraints ('Don't do X') into positive instructions ('Do Y instead') for better adherence.",
            "critical": False,
            "penalty": 10
        }
    }

    def analyze(self, text: str) -> Dict[str, Any]:
        """Evaluates a raw string against key prompt engineering dimensions."""
        results = {}
        improvements = []
        score = 0

        if not text or not text.strip():
            return {
                "score": 0,
                "results": {},
                "improvements": ["Prompt is empty."]
            }

        # 1. Process Positive Heuristics
        positive_keys = ["role_definition", "cognitive_scaffolding", "delimiter_hygiene", "few_shot"]
        for key in positive_keys:
            h = self.HEURISTICS[key]
            if re.search(h["pattern"], text):
                results[key] = True
                score += h["weight"]
            else:
                results[key] = False
                improvements.append(h["improvement"])

        # 2. Process Negative Constraints (Penalties)
        h_neg = self.HEURISTICS["negative_constraints"]
        if re.search(h_neg["pattern"], text):
            results["negative_constraints"] = False  # Flagged as an issue
            score -= h_neg["penalty"]
            improvements.append(h_neg["improvement"])
        else:
            results["negative_constraints"] = True

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        return {
            "score": score,
            "results": results,
            "improvements": improvements
        }