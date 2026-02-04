import os
import ast
from typing import List, Tuple, Dict, Any, Union
from rich.console import Console
from .constants import AGENT_CONTEXT_TEMPLATE, INSTRUCTIONS_TEMPLATE, DOCSTRING_TEXT, TYPE_HINT_STUB

console = Console()

def get_indentation(line: str) -> str:
    """Returns the indentation string of a line."""
    return line[:len(line) - len(line.lstrip())]

def check_missing_docstring(node: Union[ast.FunctionDef, ast.AsyncFunctionDef], lines: List[str], insertions: List[Tuple[int, str]]) -> None:
    """Checks for missing docstring and adds insertion if needed."""
    if not ast.get_docstring(node):
        # Insert after the function definition line (handling decorators)
        # The body starts at node.body[0].lineno.
        # We need to insert *before* the first statement of the body.

        # Ensure body exists (it should for a valid function)
        if not node.body:
            return

        body_start_line = node.body[0].lineno - 1 # 0-indexed

        # Determine indentation from the first line of the body
        if body_start_line < len(lines):
            body_line_content = lines[body_start_line]
            indent_str = get_indentation(body_line_content)

            # Check if it's just 'pass' or '...' on the same line
            if node.body[0].lineno > node.lineno:
                    insertions.append((body_start_line, f"{indent_str}{DOCSTRING_TEXT}\n"))

def check_missing_type_hints(node: Union[ast.FunctionDef, ast.AsyncFunctionDef], lines: List[str], insertions: List[Tuple[int, str]]) -> None:
    """Checks for missing type hints and adds insertion if needed."""
    has_return = node.returns is not None
    has_args = any(arg.annotation is not None for arg in node.args.args)
    if not has_return and not has_args:
        # Insert comment above function definition
        start_line = node.lineno - 1
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno - 1

        # Check idempotency: peek at line before start_line
        prev_line_idx = start_line - 1
        if prev_line_idx >= 0 and TYPE_HINT_STUB in lines[prev_line_idx]:
            return

        # Determine function indentation
        if node.lineno - 1 < len(lines):
            func_line_content = lines[node.lineno-1]
            indent_str = get_indentation(func_line_content)
            insertions.append((start_line, f"{indent_str}{TYPE_HINT_STUB}\n"))

def fix_file_issues(filepath: str) -> None:
    """Injects docstrings and type hint TODOs where missing."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        code = "".join(lines)
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return

    insertions: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            check_missing_docstring(node, lines, insertions)
            check_missing_type_hints(node, lines, insertions)

    if not insertions:
        return

    # Sort insertions by line number descending to keep indices valid
    insertions.sort(key=lambda x: x[0], reverse=True)

    for line_idx, text in insertions:
        lines.insert(line_idx, text)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    console.print(f"[bold green][Fixed][/bold green] Injected issues in {filepath}")

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
