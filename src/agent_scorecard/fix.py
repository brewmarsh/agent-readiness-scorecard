import os
import ast
import re
from typing import Dict, Any, List, Optional
from rich.console import Console
from .constants import AGENT_CONTEXT_TEMPLATE, INSTRUCTIONS_TEMPLATE
from .metrics import get_function_stats
from .llm import LLMClient

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


def _clean_code(code: str) -> str:
    """
    Cleans up the LLM response by removing Markdown code fences.

    Args:
        code (str): The raw LLM response.

    Returns:
        str: The cleaned Python code.
    """
    # Remove ```python ... ``` or ``` ... ```
    pattern = r"```(?:python)?\s*(.*?)\s*```"
    match = re.search(pattern, code, re.DOTALL)
    if match:
        return match.group(1).strip()
    return code.strip()


def fix_file_issues(
    filepath: str, llm_config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Uses CRAFT prompts and LLM to fix code quality violations.

    Args:
        filepath (str): Path to the Python file to fix.
        llm_config (Dict[str, Any], optional): Configuration for the LLM client.

    Returns:
        None
    """
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

    llm = LLMClient(config=llm_config)
    raw_code = llm.generate(system_prompt, user_prompt)
    fixed_code = _clean_code(raw_code)

    if not fixed_code or fixed_code == content.strip():
        return

    try:
        ast.parse(fixed_code)
    except SyntaxError:
        console.print(
            f"[bold red]LLM returned invalid syntax for {filepath}. Skipping.[/bold red]"
        )
        return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(fixed_code)
    console.print(f"[bold green][Fixed][/bold green] Applied LLM fixes to {filepath}")


def _ensure_project_files(path: str, profile: Dict[str, Any]) -> None:
    """
    Ensures that required project files exist.

    Args:
        path (str): The project root path.
        profile (Dict[str, Any]): The agent profile being used.
    """
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


def _collect_target_files(path: str) -> List[str]:
    """
    Collects Python files to be fixed.

    Args:
        path (str): The path to scan.

    Returns:
        List[str]: A list of Python file paths.
    """
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
    return py_files


def apply_fixes(
    path: str, profile: Dict[str, Any], llm_config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Applies fixes to project files and structure.

    Args:
        path (str): The path to the project or file.
        profile (Dict[str, Any]): The agent profile being used.
        llm_config (Dict[str, Any], optional): Configuration for the LLM client.

    Returns:
        None
    """
    # 1. Project Docs
    _ensure_project_files(path, profile)

    # 2. File Fixes
    py_files = _collect_target_files(path)

    for py_file in py_files:
        fix_file_issues(py_file, llm_config=llm_config)
