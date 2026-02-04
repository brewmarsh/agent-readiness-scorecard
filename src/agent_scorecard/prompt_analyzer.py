import re
from typing import Dict, List, Any

class PromptAnalyzer:
    """Analyzes prompts for LLM best practices."""

    def __init__(self):
        self.heuristics = [
            {
                "name": "Persona Adoption",
                "pattern": r"(?i)\b(you are a|you are an|act as|your role is|you're a|you're an)\b",
                "score": 25,
                "description": "Assigns a specific role to the AI."
            },
            {
                "name": "Clear Delimiters",
                "pattern": r"(```|---|===|<[^>]+>)",
                "score": 25,
                "description": "Uses delimiters to separate sections."
            },
            {
                "name": "Few-Shot Examples",
                "pattern": r"(?i)(\bexample\b|input:|output:|user:|assistant:)",
                "score": 25,
                "description": "Provides examples to guide the model."
            },
            {
                "name": "Chain of Thought",
                "pattern": r"(?i)(step[- ]by[- ]step|think carefully|reasoning|stepwise)",
                "score": 25,
                "description": "Encourages reasoning before answering."
            },
             {
                "name": "Structured Output",
                "pattern": r"(?i)\b(json|csv|markdown|xml|yaml|format)\b",
                "score": 25,
                "description": "Specifies the desired output format."
            }
        ]
        self.negative_constraints = [
             {
                "name": "Negative Constraints",
                "pattern": r"(?i)\b(do not|don't|never|avoid)\b",
                "penalty": -10,
                "description": "Avoid negative constraints; use positive instructions instead."
            }
        ]

    def analyze(self, prompt_text: str) -> Dict[str, Any]:
        """
        Analyzes the prompt text and returns a score, matches, and suggestions.
        """
        score = 0
        matches = []
        suggestions = []

        if not prompt_text:
             return {
                "score": 0,
                "matches": [],
                "suggestions": ["Prompt is empty."]
            }

        # Check positive heuristics
        for h in self.heuristics:
            if re.search(h["pattern"], prompt_text):
                score += h["score"]
                matches.append(h["name"])
            else:
                suggestions.append(f"Missing {h['name']}: {h['description']}")

        # Check negative constraints
        for h in self.negative_constraints:
            found = re.findall(h["pattern"], prompt_text)
            if found:
                # Deduct points for presence (once per type for now to avoid massive penalties)
                score += h["penalty"]
                # We mention the specific words found to be helpful
                unique_found = set(f.lower() for f in found)
                found_str = ", ".join(f"'{w}'" for w in unique_found)
                suggestions.append(f"Found {h['name']} ({found_str}). Try positive framing.")

        return {
            "score": score,
            "matches": matches,
            "suggestions": suggestions
        }
