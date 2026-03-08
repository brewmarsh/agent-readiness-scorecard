import os
import ast
from typing import List, Optional, Tuple, Any


def _collect_directory_stats(path: str) -> Tuple[int, int, int, List[str]]:
    """
    Helper to walk the directory and collect file/folder counts.

    Args:
        path (str): The root path to walk.

    Returns:
        Tuple[int, int, int, List[str]]:
            - total_files
            - total_folders
            - max_files
            - crowded_dirs
    """
    total_files = 0
    total_folders = 0
    max_files = 0
    crowded_dirs = []

    for root, dirs, files in os.walk(path):
        # Filter out hidden directories and __pycache__ to avoid noise
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

        total_folders += 1
        num_files = len(files)
        total_files += num_files

        if num_files > max_files:
            max_files = num_files

        if num_files > 50:
            crowded_dirs.append(root)

    return total_files, total_folders, max_files, crowded_dirs


def _check_agents_md(root_files: List[str]) -> bool:
    """
    Checks if AGENTS.md exists in the root files.

    Args:
        root_files (List[str]): List of files in the root directory.

    Returns:
        bool: True if AGENTS.md exists, False otherwise.
    """
    return any(f.lower() == "agents.md" for f in root_files)


def _check_linter_config(root_files: List[str]) -> bool:
    """
    Checks if any linter configuration file exists in the root files.

    Args:
        root_files (List[str]): List of files in the root directory.

    Returns:
        bool: True if a linter config exists, False otherwise.
    """
    linter_files = ["ruff.toml", ".flake8", ".eslintrc", "pyproject.toml"]
    return any(f in root_files for f in linter_files)


def _check_lock_file(root_files: List[str]) -> bool:
    """
    Checks if any lock file exists in the root files.

    Args:
        root_files (List[str]): List of files in the root directory.

    Returns:
        bool: True if a lock file exists, False otherwise.
    """
    lock_files = ["package-lock.json", "poetry.lock", "uv.lock", "requirements.txt"]
    return any(f in root_files for f in lock_files)


def _get_toml_tool() -> Any:
    """Helper to unify tomllib and tomli."""
    try:
        import tomllib as toml_tool  # type: ignore

        return toml_tool
    except ImportError:
        import tomli as toml_tool  # type: ignore

        return toml_tool


def _validate_pyproject(base_dir: str, root_files: List[str]) -> bool:
    """
    Validates pyproject.toml if it exists.

    Args:
        base_dir (str): The base directory path.
        root_files (List[str]): List of files in the root directory.

    Returns:
        bool: True if pyproject.toml is valid or doesn't exist, False if invalid.
    """
    if "pyproject.toml" not in root_files:
        return True

    filepath = os.path.join(base_dir, "pyproject.toml")
    try:
        toml_tool = _get_toml_tool()
        with open(filepath, "rb") as f:
            toml_tool.load(f)
        return True
    except Exception:
        return False


def _unparse_signature(node: ast.AST) -> Optional[str]:
    """Helper to unparse a signature with body replaced by pass (Python 3.9+)."""
    orig_body = getattr(node, "body", [])
    setattr(node, "body", [ast.Pass()])
    try:
        unparsed = ast.unparse(node)
        lines = unparsed.splitlines()
        if not lines:
            return None
        sig = "\n".join(lines[:-1]).strip()
        return sig if sig else lines[0]
    except Exception:
        return None
    finally:
        setattr(node, "body", orig_body)


def _fallback_signature(node: ast.AST) -> Optional[str]:
    """Fallback signature extraction for older Python versions."""
    deco_list = [
        f"@{deco.id}" if isinstance(deco, ast.Name) else "@decorator"
        for deco in getattr(node, "decorator_list", [])
    ]

    if isinstance(node, ast.ClassDef):
        sig = f"class {node.name}:"
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        sig = f"{prefix} {node.name}(...):"
    else:
        return None

    return "\n".join(deco_list + [sig]) if deco_list else sig


def _extract_signature_from_node(node: ast.AST) -> Optional[str]:
    """
    Extracts function/class signatures from an AST node.

    This provides the 'skeleton' of the code for token counting.

    Args:
        node (ast.AST): The AST node to extract the signature from.

    Returns:
        Optional[str]: The extracted signature string, or None if not applicable.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None

    if hasattr(ast, "unparse"):
        return _unparse_signature(node)
    return _fallback_signature(node)


def get_python_signatures(filepath: str) -> str:
    """
    Extracts all top-level function and class signatures from a file.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        str: A concatenated string of all signatures found.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return ""

    nodes = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    signatures = [s for s in (_extract_signature_from_node(n) for n in nodes) if s]
    return "\n".join(signatures)


def _read_file_safe(filepath: str) -> str:
    """Reads a file safely, returning empty string on failure."""
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read() + "\n"
    except Exception:
        return ""


def _get_critical_files_content(base_dir: str) -> str:
    """
    Reads the content of critical context files (README.md, AGENTS.md).

    Args:
        base_dir (str): The base directory to search.

    Returns:
        str: Concatenated content of critical files.
    """
    total_content = ""
    critical_files = ["README.md", "AGENTS.md"]

    for cf in critical_files:
        total_content += _read_file_safe(os.path.join(base_dir, cf))
    return total_content


def _get_python_files_in_tree(path: str) -> List[str]:
    """Helper to collect Python files in directory tree."""
    python_files = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        python_files.extend(os.path.join(root, f) for f in files if f.endswith(".py"))
    return python_files


def _get_project_signatures(path: str) -> str:
    """
    Walks the directory tree and extracts signatures from all Python files.

    Args:
        path (str): The root path to search.

    Returns:
        str: Concatenated signatures of all Python files.
    """
    files = _get_python_files_in_tree(path)
    return "\n".join(get_python_signatures(f) for f in files)


def _scan_file_content(filepath: str, targets: List[str]) -> List[str]:
    """Helper to read and scan file content."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
    except Exception:
        return []
    return [t for t in targets if t.lower() in content]


def _scan_file_for_frameworks(filepath: str, targets: List[str]) -> List[str]:
    """
    Helper to scan a single file for framework substrings.

    Args:
        filepath (str): Path to the file.
        targets (List[str]): Frameworks to search for.

    Returns:
        List[str]: Found frameworks in this file.
    """
    return _scan_file_content(filepath, targets)


def _scan_dependencies(base_path: str, targets: List[str]) -> List[str]:
    """
    Scans pyproject.toml and requirements.txt for specified frameworks.

    Args:
        base_path (str): The project root path.
        targets (List[str]): List of framework names to search for.

    Returns:
        List[str]: Found frameworks.
    """
    found_set = set()
    dep_files = ["pyproject.toml", "requirements.txt"]

    for dep_file in dep_files:
        filepath = os.path.join(base_path, dep_file)
        if os.path.exists(filepath):
            found_set.update(_scan_file_for_frameworks(filepath, targets))

    return sorted(list(found_set))


def _check_context_steering_files(base_path: str) -> List[str]:
    """
    Checks for the existence of context steering files and directories.

    Args:
        base_path (str): The project root path.

    Returns:
        List[str]: Found steering files/directories.
    """
    found = []
    targets = [
        ".cursorrules",
        ".windsurfrules",
        "cline_docs",
        os.path.join(".github", "copilot-instructions.md"),
    ]

    for target in targets:
        full_path = os.path.join(base_path, target)
        if os.path.exists(full_path):
            found.append(target)

    return found
