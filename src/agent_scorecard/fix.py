import os
from typing import Dict, Any
from rich.console import Console
from .constants import AGENT_CONTEXT_TEMPLATE, INSTRUCTIONS_TEMPLATE
from .metrics import get_function_stats
from .utils import collect_python_files

console = Console()

CRAFT_PROMPTS = {
    "persona": "You are an Elite DevOps Engineer specializing in Python code quality.",
    "action_steps": [
        "Read the source code provided.",
        "Identify the specific violation (ACL > 15 or Missing Types).",
        "Apply the fix strictly to the violations.",
        "Verify that the code is syntactically correct.",
    ],
    "frame": "Maintain strictly the same functionality. Do not add new features. Do not explain your reasoning; just output code.",
}


class LLM:
    """Standard interface for LLM interaction."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates fixed code using an LLM.
        Note: This is a placeholder for real LLM integration.
        """
        # In a real implementation, this would call OpenAI/Anthropic etc.
        # For now, we return the original code (simulating no changes).
        if "Source Code:\n" in user_prompt:
            return user_prompt.split("Source Code:\n")[-1]
        return ""


def fix_file_issues(filepath: str) -> None:
    """Uses CRAFT prompts and LLM to fix code quality violations."""
    try:
        stats = get_function_stats(filepath)
    except Exception:
        return

    # Violations: ACL > 15 or missing type hints (is_typed=False)
    violations = [s for s in stats if s["acl"] > 15 or not s.get("is_typed", True)]

    if not violations:
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return

    system_prompt = f"{CRAFT_PROMPTS['persona']}\n\n{CRAFT_PROMPTS['frame']}"
    action_str = "\n".join([f"- {step}" for step in CRAFT_PROMPTS["action_steps"]])
    user_prompt = f"Action Steps:\n{action_str}\n\nSource Code:\n{content}"

    llm = LLM()
    fixed_code = llm.generate(system_prompt, user_prompt)

    if fixed_code and fixed_code.strip() != content.strip():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_code)
        console.print(
            f"[bold green][Fixed][/bold green] Applied LLM fixes to {filepath}"
        )


def _ensure_project_docs(path: str, profile: Dict[str, Any]) -> None:
    """Ensures that required project documentation files exist."""
    if not os.path.isdir(path):
        return

    required = profile.get("required_files", [])
    existing = [f.lower() for f in os.listdir(path)]

    for req in required:
        if req.lower() not in existing:
            filepath = os.path.join(path, req)
            content = ""
            if req.lower() == "agents.md":
                content = AGENT_CONTEXT_TEMPLATE.format(
                    project_name=os.path.basename(os.path.abspath(path))
                )
            elif req.lower() == "instructions.md":
                content = INSTRUCTIONS_TEMPLATE
            elif req.lower() == "readme.md":
                content = "# Project\n\nAuto-generated README."

            if content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                console.print(f"[bold green][Fixed][/bold green] Created {req}")


def apply_fixes(path: str, profile: Dict[str, Any]) -> None:
    """Applies fixes to project files and structure."""

    # 1. Project Docs
    _ensure_project_docs(path, profile)

    # 2. File Fixes
    py_files = collect_python_files(path)

    for py_file in py_files:
        fix_file_issues(py_file)
