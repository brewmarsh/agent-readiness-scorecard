import os
import ast
from typing import List, Tuple, Dict, Any, Union
from rich.console import Console
from .constants import AGENT_CONTEXT_TEMPLATE, INSTRUCTIONS_TEMPLATE
from .metrics import get_function_stats

console = Console()

CRAFT_PROMPTS = {
    "refactor": {
        "context": "You are an Elite DevOps Engineer specializing in Python code quality.",
        "actions": [
            "Read the source code provided.",
            "Identify the specific violation (ACL > 15 or Missing Types).",
            "Apply the fix strictly to the violations.",
            "Verify that the code is syntactically correct."
        ],
        "frame": "Maintain strictly the same functionality. Do not add new features. Do not explain your reasoning; just output code."
    }
}

class LLM:
    """Mock LLM class for code generation."""
    @staticmethod
    def generate(prompt: str) -> str:
        """
        Placeholder for real LLM integration.
        In production, this would call an external API.
        """
        # For now, we extract the source code part from the prompt as a fallback
        if "Source Code:\n" in prompt:
            return prompt.split("Source Code:\n")[-1]
        return ""

def fix_file_issues(filepath: str) -> None:
    """Uses LLM to refactor files with ACL or Type violations."""
    stats = get_function_stats(filepath)
    violations = [s for s in stats if s["acl"] > 15 or not s["is_typed"]]

    if not violations:
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return

    # Construct CRAFT prompt
    prompt_config = CRAFT_PROMPTS["refactor"]
    prompt = f"Context: {prompt_config['context']}\n"
    prompt += "Actions:\n"
    for i, action in enumerate(prompt_config["actions"], 1):
        prompt += f"{i}. {action}\n"
    prompt += f"Frame: {prompt_config['frame']}\n\n"
    prompt += "Source Code:\n"

    # Pass combined prompt and content
    fixed_content = LLM.generate(prompt + content)

    # Simple post-processing to remove potential markdown blocks
    if fixed_content.startswith("```python"):
        fixed_content = fixed_content.split("```python")[1].split("```")[0].strip()
    elif fixed_content.startswith("```"):
        fixed_content = fixed_content.split("```")[1].split("```")[0].strip()

    # Final check: only write if non-empty and syntactically valid
    try:
        ast.parse(fixed_content)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        console.print(f"[bold green][Fixed][/bold green] Applied LLM fixes to {filepath}")
    except SyntaxError:
        console.print(f"[bold red][Error][/bold red] LLM generated invalid syntax for {filepath}. Skipping.")

def apply_fixes(path: str, profile: Dict[str, Any]) -> None:
    """Applies fixes to project files and structure."""

    # 1. Project Docs
    if os.path.isdir(path):
        required = profile.get("required_files", [])
        existing = [f.lower() for f in os.listdir(path)]

        for req in required:
            if req.lower() not in existing:
                filepath = os.path.join(path, req)
                content = ""
                if req.lower() == "agents.md":
                    content = AGENT_CONTEXT_TEMPLATE.format(project_name=os.path.basename(os.path.abspath(path)))
                elif req.lower() == "instructions.md":
                    content = INSTRUCTIONS_TEMPLATE
                elif req.lower() == "readme.md":
                    content = "# Project\n\nAuto-generated README."

                if content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    console.print(f"[bold green][Fixed][/bold green] Created {req}")

    # 2. File Fixes
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    for py_file in py_files:
        fix_file_issues(py_file)
