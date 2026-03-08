import os
import ast
from typing import List, Optional, Tuple


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


def _validate_pyproject(base_dir: str, root_files: List[str]) -> bool:
    """
    Validates pyproject.toml if it exists.

    Args:
        base_dir (str): The base directory path.
        root_files (List[str]): List of files in the root directory.

    Returns:
        bool: True if pyproject.toml is valid or doesn't exist, False if invalid.
    """
    if "pyproject.toml" in root_files:
        filepath = os.path.join(base_dir, "pyproject.toml")
        try:
            # Use toml_tool alias to unify tomllib and tomli
            try:
                import tomllib as toml_tool  # type: ignore
            except ImportError:
                import tomli as toml_tool  # type: ignore

            with open(filepath, "rb") as f:
                toml_tool.load(f)
            return True
        except Exception:
            return False
    return True


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
        # Python 3.9+ logic: Replace body with 'pass' to get just the signature
        orig_body = getattr(node, "body", [])
        setattr(node, "body", [ast.Pass()])
        try:
            unparsed = ast.unparse(node)
            lines = unparsed.splitlines()
            if lines:
                sig = "\n".join(lines[:-1]).strip()
                if not sig:
                    sig = lines[0]
                return sig
        except Exception:
            pass
        finally:
            setattr(node, "body", orig_body)
    else:
        # Fallback for older Python versions
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
    return None


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

    signatures: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            sig = _extract_signature_from_node(node)
            if sig:
                signatures.append(sig)

    return "\n".join(signatures)


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
        cf_path = os.path.join(base_dir, cf)
        if os.path.exists(cf_path):
            try:
                with open(cf_path, "r", encoding="utf-8", errors="ignore") as f:
                    total_content += f.read() + "\n"
            except Exception:
                pass
    return total_content


def _get_project_signatures(path: str) -> str:
    """
    Walks the directory tree and extracts signatures from all Python files.

    Args:
        path (str): The root path to search.

    Returns:
        str: Concatenated signatures of all Python files.
    """
    total_signatures = ""
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for file in files:
            if file.endswith(".py"):
                total_signatures += (
                    get_python_signatures(os.path.join(root, file)) + "\n"
                )
    return total_signatures


def _scan_dependencies(base_path: str, targets: List[str]) -> List[str]:
    """
    Scans pyproject.toml and requirements.txt for specified frameworks.

    Args:
        base_path (str): The project root path.
        targets (List[str]): List of framework names to search for.

    Returns:
        List[str]: Found frameworks.
    """
    found = []
    dep_files = ["pyproject.toml", "requirements.txt"]

    for dep_file in dep_files:
        filepath = os.path.join(base_path, dep_file)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for target in targets:
                        if target.lower() in content.lower() and target not in found:
                            found.append(target)
            except Exception:
                pass
    return found


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
