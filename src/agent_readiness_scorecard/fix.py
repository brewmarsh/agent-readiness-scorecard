import os
import ast
import re
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from .constants import AGENT_CONTEXT_TEMPLATE, INSTRUCTIONS_TEMPLATE
from .analyzers.python import PythonAnalyzer
from .llm import LLMClient

console = Console()

CRAFT_PROMPTS = {
    "refactor": {
        "persona": "You are an Elite DevOps Engineer specializing in Python code quality.",
        "actions": [
            "Read the source code provided.",
            "Identify the specific violation (ACL > 15 or Missing Types).",
            "Apply the fix strictly to the violations.",
            "Verify that the code is syntactically correct.",
        ],
        "frame": "Maintain strictly the same functionality. Do not add new features. Do not explain your reasoning; just output code.",
    }
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


def _get_violations(filepath: str) -> List[Dict[str, Any]]:
    """
    Identifies code quality violations in a file.

    Args:
        filepath (str): Path to the Python file to analyze.

    Returns:
        List[Dict[str, Any]]: A list of function stats that violate the threshold.
    """
    try:
        stats = PythonAnalyzer().get_function_stats(filepath)
    except Exception:
        return []

    # Violations: ACL > 15 or missing type hints (is_typed=False)
    return [s for s in stats if s["acl"] > 15 or not s.get("is_typed", True)]


def _process_llm_response(filepath: str, content: str, raw_code: str) -> None:
    """
    Processes and validates LLM response, then writes to file.

    Args:
        filepath (str): Path to the Python file to fix.
        content (str): Original file content.
        raw_code (str): Raw LLM response.
    """
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


def _get_refactor_prompts(content: str) -> Tuple[str, str]:
    """
    Constructs the system and user prompts for refactoring.

    Args:
        content (str): The source code to refactor.

    Returns:
        tuple[str, str]: The system prompt and user prompt.
    """
    config = CRAFT_PROMPTS["refactor"]
    system_prompt = f"{config['persona']}\n\n{config['frame']}"
    action_str = "\n".join([f"- {step}" for step in config["actions"]])
    user_prompt = f"Action Steps:\n{action_str}\n\nSource Code:\n{content}"
    return system_prompt, user_prompt


def _read_file_safe(filepath: str) -> Optional[str]:
    """
    Reads a file and returns its content, or None if it fails.

    Args:
        filepath (str): Path to the file.

    Returns:
        Optional[str]: File content or None.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def fix_file_issues(filepath: str, llm_config: Optional[Dict[str, Any]] = None) -> None:
    """
    Uses CRAFT prompts and LLM to fix code quality violations.

    Args:
        filepath (str): Path to the Python file to fix.
        llm_config (Dict[str, Any], optional): Configuration for the LLM client.

    Returns:
        None
    """
    if not _get_violations(filepath):
        return

    content = _read_file_safe(filepath)
    if content is None:
        return

    system_prompt, user_prompt = _get_refactor_prompts(content)
    llm = LLMClient(config=llm_config)
    raw_code = llm.generate(system_prompt, user_prompt)

    _process_llm_response(filepath, content, raw_code)


def _get_template_content(filename: str, project_root: str) -> str:
    """
    Retrieves template content based on the filename.

    Args:
        filename (str): The name of the file.
        project_root (str): The project root path.

    Returns:
        str: The template content.
    """
    name_lower = filename.lower()
    if name_lower == "agents.md":
        return AGENT_CONTEXT_TEMPLATE.format(
            project_name=os.path.basename(os.path.abspath(project_root))
        )
    if name_lower == "instructions.md":
        return INSTRUCTIONS_TEMPLATE
    if name_lower == "readme.md":
        return "# Project\n\nAuto-generated README."
    return ""


def _create_missing_file(path: str, filename: str) -> None:
    """
    Creates a missing file from template content.

    Args:
        path (str): The project root path.
        filename (str): The name of the file to create.
    """
    content = _get_template_content(filename, path)
    if content:
        filepath = os.path.join(path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[bold green][Fixed][/bold green] Created {filename}")


def _check_and_create_files(path: str, required: List[str]) -> None:
    """
    Checks for missing files and creates them.

    Args:
        path (str): The project root path.
        required (List[str]): List of required filenames.
    """
    existing = [f.lower() for f in os.listdir(path)]
    for req in required:
        if req.lower() not in existing:
            _create_missing_file(path, req)


def _ensure_project_files(path: str, profile: Dict[str, Any]) -> None:
    """
    Ensures that required project files exist.

    Args:
        path (str): The project root path.
        profile (Dict[str, Any]): The agent profile being used.
    """
    if not os.path.isdir(path):
        return

    required: List[str] = profile.get("required_files", [])
    if required:
        _check_and_create_files(path, required)


def _add_python_files_from_list(
    root: str, files: List[str], py_files: List[str]
) -> None:
    """
    Filters Python files from a list and adds them to a target list.

    Args:
        root (str): The root directory of the files.
        files (List[str]): List of filenames to filter.
        py_files (List[str]): The list to append Python file paths to.
    """
    for file in files:
        if file.endswith(".py"):
            py_files.append(os.path.join(root, file))


def _list_python_files(directory_path: str) -> List[str]:
    """
    Recursively lists all Python files in a directory.

    Args:
        directory_path (str): The directory to scan.

    Returns:
        List[str]: A list of paths to Python files.
    """
    py_files: List[str] = []
    for root, _, files in os.walk(directory_path):
        _add_python_files_from_list(root, files, py_files)
    return py_files


def _collect_target_files(path: str) -> List[str]:
    """
    Collects Python files to be fixed.

    Args:
        path (str): The path to scan.

    Returns:
        List[str]: A list of Python file paths.
    """
    if os.path.isfile(path) and path.endswith(".py"):
        return [path]
    if os.path.isdir(path):
        return _list_python_files(path)
    return []


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
