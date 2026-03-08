import os
import tiktoken
from typing import Dict, cast, Optional, Any, List
from .types import (
    DirectoryEntropy,
    TokenAnalysis,
    EnvironmentHealth,
    AgenticEcosystem,
)
from .auditor_utils import (
    _collect_directory_stats,
    _get_critical_files_content,
    _get_project_signatures,
    _check_agents_md,
    _check_linter_config,
    _check_lock_file,
    _validate_pyproject,
    get_python_signatures,
    _scan_dependencies,
    _check_context_steering_files,
)


def check_directory_entropy(path: str) -> DirectoryEntropy:
    """
    Calculate directory entropy for a given path.

    Warns if avg files > 15 OR any single directory has > 50 files.
    High entropy makes it difficult for RAG or Agents to find specific files.

    Args:
        path (str): The root directory path to analyze.

    Returns:
        DirectoryEntropy: A dictionary containing average files, warning status,
                        max files in a single dir, and list of crowded directories.
    """
    if not os.path.isdir(path):
        return {"avg_files": 0, "warning": False, "max_files": 0, "crowded_dirs": []}

    total_files, total_folders, max_files, crowded_dirs = _collect_directory_stats(path)

    avg = total_files / total_folders if total_folders > 0 else 0

    return {
        "avg_files": avg,
        "warning": avg > 15 or max_files > 50,
        "max_files": max_files,
        "crowded_dirs": crowded_dirs,
    }


def _is_hidden_path(path: str) -> bool:
    """Helper to check if any part of the path starts with a dot."""
    return any(part.startswith(".") for part in path.split(os.sep))


def _get_rel_path(root: str, base_path: str) -> str:
    """Helper to get relative path or base name if root equals base_path."""
    rel_path = os.path.relpath(root, start=base_path)
    if rel_path == ".":
        return os.path.basename(os.path.abspath(base_path))
    return rel_path


def _collect_crowded_stats(
    root: str, files: List[str], base: str, threshold: int, stats: Dict[str, int]
) -> None:
    """Helper to update stats if directory is crowded and not hidden."""
    if not _is_hidden_path(root) and len(files) > threshold:
        stats[_get_rel_path(root, base)] = len(files)


def get_crowded_directories(root_path: str, threshold: int = 50) -> Dict[str, int]:
    """
    Returns a flat dictionary of directories exceeding the file count threshold.

    Args:
        root_path (str): The root path to start the search.
        threshold (int): The file count threshold (default: 50).

    Returns:
        Dict[str, int]: A dictionary mapping directory paths to their file counts.
    """
    entropy_stats: Dict[str, int] = {}
    if not os.path.isdir(root_path):
        return entropy_stats

    for root, _, files in os.walk(root_path):
        _collect_crowded_stats(root, files, root_path, threshold, entropy_stats)
    return entropy_stats


def count_python_tokens(filepath: str) -> int:
    """
    Calculates the token count of a single Python file using tiktoken.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        int: The number of tokens in the file.
    """
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return len(enc.encode(content))
    except Exception:
        return 0


def _get_token_encoding() -> Optional[Any]:
    """Helper to get tiktoken encoding or None."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def _get_context_signatures(path: str) -> str:
    """Helper to get project or file signatures."""
    if os.path.isdir(path):
        return _get_project_signatures(path)
    if os.path.isfile(path) and path.endswith(".py"):
        return get_python_signatures(path)
    return ""


def check_critical_context_tokens(path: str) -> TokenAnalysis:
    """
    Counts tokens for the project's 'Critical Context'.

    If this exceeds 32k, an Agent will likely lose track of the overall architecture.

    Args:
        path (str): Path to the project or file.

    Returns:
        TokenAnalysis: Dictionary with token count and alert status.
    """
    enc = _get_token_encoding()
    if not enc:
        return {"token_count": 0, "alert": False}

    base_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    total_content = _get_critical_files_content(base_dir)
    total_content += _get_context_signatures(path)

    count = len(enc.encode(total_content))
    return {"token_count": count, "alert": count > 32000}


def check_agentic_ecosystem(base_path: str) -> AgenticEcosystem:
    """
    Detect modern AI tools and structured output frameworks.

    Args:
        base_path (str): Project root directory.

    Returns:
        AgenticEcosystem: Findings about context files and frameworks.
    """
    framework_targets = [
        "baml",
        "instructor",
        "outlines",
        "pydantic-ai",
        "crewai",
        "langfuse",
    ]

    found_files = _check_context_steering_files(base_path)
    found_frameworks = _scan_dependencies(base_path, framework_targets)

    return {
        "has_context_files": len(found_files) > 0,
        "found_files": found_files,
        "has_agent_frameworks": len(found_frameworks) > 0,
        "found_frameworks": found_frameworks,
    }


def check_environment_health(path: str) -> EnvironmentHealth:
    """
    Check for essential agent configuration: AGENTS.md, Linters, and Lock files.

    Args:
        path (str): The root path to check.

    Returns:
        EnvironmentHealth: Dictionary containing the status of various environment checks.
    """
    results = {
        "agents_md": False,
        "linter_config": False,
        "lock_file": False,
        "pyproject_valid": True,
        "agentic_ecosystem": None,
    }

    base_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    if not os.path.exists(base_dir):
        return cast(EnvironmentHealth, results)

    root_files = os.listdir(base_dir)

    results["agents_md"] = _check_agents_md(root_files)
    results["linter_config"] = _check_linter_config(root_files)
    results["lock_file"] = _check_lock_file(root_files)
    results["pyproject_valid"] = _validate_pyproject(base_dir, root_files)
    results["agentic_ecosystem"] = check_agentic_ecosystem(base_dir)

    return cast(EnvironmentHealth, results)
