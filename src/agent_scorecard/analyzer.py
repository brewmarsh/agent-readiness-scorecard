import os
import ast
from typing import List, Dict, Any, Tuple, Set, Optional, cast
from .constants import PROFILES
from .scoring import score_file
from . import auditor
from .types import FileAnalysisResult, DepAnalysis, DirectoryStat, AnalysisResult
from .dependencies import (
    get_import_graph,
    get_inbound_imports,
    detect_cycles,
    calculate_context_tokens,
    _collect_python_files,
)

# Re-export metrics for backward compatibility
from .metrics import (  # noqa: F401
    calculate_acl,
    get_loc,
    get_complexity_score,
    get_function_stats,
    check_type_hints,
    count_tokens,
    NestingDepthVisitor,
    calculate_max_depth,
)


# --- METRICS & GRAPH ANALYSIS ---


def scan_project_docs(root_path: str, required_files: List[str]) -> List[str]:
    """
    Checks for existence of agent-critical markdown files.

    Args:
        root_path (str): The root path of the project.
        required_files (List[str]): List of filenames required for the agent.

    Returns:
        List[str]: List of missing required files.
    """
    missing = []
    root_files = (
        [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []
    )

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing


def get_project_issues(
    path: str, py_files: List[str], profile: Dict[str, Any]
) -> Tuple[int, List[str]]:
    """
    Analyzes global project health: docs, environment, god modules, and entropy.

    Args:
        path (str): Project root path.
        py_files (List[str]): List of Python files in the project.
        profile (Dict[str, Any]): The agent profile being used.

    Returns:
        Tuple[int, List[str]]: A tuple of (total penalty, list of issue descriptions).
    """
    penalty = 0
    issues: List[str] = []

    # 1. Documentation Check
    missing_docs = scan_project_docs(
        path, cast(List[str], profile.get("required_files", []))
    )
    if missing_docs:
        msg = f"Missing Critical Agent Docs: {', '.join(missing_docs)}"
        penalty += len(missing_docs) * 15
        issues.append(msg)

    # 1a. Environment Health (malformed config logic)
    health = auditor.check_environment_health(path)
    if not health.get("pyproject_valid", True):
        msg = "Malformed pyproject.toml detected"
        penalty += 20
        issues.append(msg)

    # 2. Dependency Analysis
    graph = get_import_graph(path)
    inbound = get_inbound_imports(graph)
    god_modules = [mod for mod, count in inbound.items() if count > 50]
    if god_modules:
        msg = f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}"
        penalty += len(god_modules) * 10
        issues.append(msg)

    # 3. Directory Entropy
    entropy_stats = auditor.get_crowded_directories(path, threshold=50)
    crowded_dirs = list(entropy_stats.keys())
    if crowded_dirs:
        msg = f"High Directory Entropy (>50 files): {', '.join(crowded_dirs)}"
        penalty += len(crowded_dirs) * 5
        issues.append(msg)

    # 4. Circular Dependencies
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = ["->".join(c) for c in cycles]
        msg = f"Circular Dependencies Detected: {', '.join(cycle_strs)}"
        penalty += len(cycles) * 5
        issues.append(msg)

    return penalty, issues


def perform_analysis(
    path: str,
    agent: str = "generic",
    limit_to_files: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """
    Orchestrates the full project analysis pipeline.

    Args:
        path (str): The project path to analyze.
        agent (str): The agent profile name (default: "generic").
        limit_to_files (Optional[List[str]]): Optional list of files to limit analysis to.
        profile (Optional[Dict[str, Any]]): Optional override for agent profile.
        thresholds (Optional[Dict[str, Any]]): Optional override for scoring thresholds.

    Returns:
        AnalysisResult: The comprehensive analysis result.
    """
    if profile is None:
        profile = PROFILES.get(agent, PROFILES["generic"])

    py_files = _collect_python_files(path)
    all_py_files = py_files[:]

    # Calculate tokens for ALL files to enable context economics calculation
    # We need a map of relative_path -> tokens
    file_token_map: Dict[str, int] = {}

    project_root = (
        path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    )

    for filepath in all_py_files:
         rel_path = os.path.relpath(filepath, start=project_root)
         file_token_map[rel_path] = count_tokens(filepath)

    # Build graph and calculate context tokens
    graph = get_import_graph(path)
    context_tokens_map = calculate_context_tokens(graph, file_token_map)


    if limit_to_files:
        py_files = [
            f
            for f in py_files
            if any(f.endswith(changed) for changed in limit_to_files)
        ]

    file_results: List[FileAnalysisResult] = []
    file_scores: List[int] = []

    for filepath in py_files:
        # Pass thresholds to allow pyproject.toml overrides per file
        score, issues, loc, complexity, type_safety, metrics_data = score_file(
            filepath, profile, thresholds=thresholds
        )
        file_scores.append(score)

        rel_path = os.path.relpath(filepath, start=project_root)

        file_results.append(
            {
                "file": rel_path,
                "score": score,
                "issues": issues,
                "loc": loc,
                "complexity": complexity,
                "type_coverage": type_safety,
                "function_metrics": metrics_data,
                "tokens": file_token_map.get(rel_path, 0),
                "context_tokens": context_tokens_map.get(rel_path, 0),
                "acl": max([m["acl"] for m in metrics_data]) if metrics_data else 0.0,
            }
        )

    penalty, project_issues = get_project_issues(project_root, all_py_files, profile)
    project_score = max(0, 100 - penalty)

    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    inbound = get_inbound_imports(graph)
    cycles = detect_cycles(graph)
    god_modules = {mod: count for mod, count in inbound.items() if count > 50}

    dep_analysis_val: DepAnalysis = {"cycles": cycles, "god_modules": god_modules}

    directory_stats: List[DirectoryStat] = []
    entropy = auditor.get_crowded_directories(
        path if os.path.isdir(path) else os.path.dirname(path), threshold=50
    )
    for p, count in entropy.items():
        directory_stats.append({"path": p, "file_count": count})

    return {
        "file_results": file_results,
        "final_score": final_score,
        "missing_docs": scan_project_docs(
            project_root, cast(List[str], profile.get("required_files", []))
        ),
        "project_issues": project_issues,
        "dep_analysis": dep_analysis_val,
        "directory_stats": directory_stats,
    }
