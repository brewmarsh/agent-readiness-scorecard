import os
import ast
import mccabe
from collections import Counter
from typing import List, Dict, Any, Tuple, Set, Optional, TypedDict, cast
from .constants import PROFILES
from .scoring import score_file
from . import auditor
from .types import FunctionMetric, FileAnalysisResult, DepAnalysis, DirectoryStat, AnalysisResult

# Re-export metrics for backward compatibility
from .metrics import (  # noqa: F401
    calculate_acl,
    get_loc,
    get_complexity_score,
    get_function_stats,
    check_type_hints,
    count_tokens,
)

# --- METRICS & GRAPH ANALYSIS ---


def scan_project_docs(root_path: str, required_files: List[str]) -> List[str]:
    """Checks for existence of agent-critical markdown files."""
    missing = []
    root_files = (
        [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []
    )

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing


def _collect_python_files(path: str) -> List[str]:
    """Collects all Python files in the given path, ignoring hidden directories."""
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            parts = root.split(os.sep)
            if any(p.startswith(".") and p != "." for p in parts):
                continue
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
    return py_files


def _parse_imports(filepath: str) -> Set[str]:
    """Parses a Python file and returns a set of imported module names."""
    imported_names: Set[str] = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filename=filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return imported_names

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module)
    return imported_names


def get_import_graph(root_path: str) -> Dict[str, Set[str]]:
    """Builds a dependency graph of the project."""
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        all_py_files = [os.path.basename(root_path)]
        root_path = os.path.dirname(root_path)
    else:
        full_paths = _collect_python_files(root_path)
        all_py_files = [os.path.relpath(f, start=root_path) for f in full_paths]

    graph: Dict[str, Set[str]] = {f: set() for f in all_py_files}

    for rel_path in all_py_files:
        full_path = os.path.join(root_path, rel_path)
        imported_names = _parse_imports(full_path)

        for name in imported_names:
            suffix = name.replace(".", os.sep)
            for candidate in all_py_files:
                if candidate == rel_path:
                    continue
                candidate_no_ext = os.path.splitext(candidate)[0]
                if candidate_no_ext.endswith(suffix):
                    match_len = len(suffix)
                    if (
                        len(candidate_no_ext) == match_len
                        or candidate_no_ext[-(match_len + 1)] == os.sep
                    ):
                        graph[rel_path].add(candidate)
    return graph


def get_inbound_imports(graph: Dict[str, Set[str]]) -> Dict[str, int]:
    """Returns {file: count} of inbound imports to identify 'God Modules'."""
    inbound: Dict[str, int] = {node: 0 for node in graph}
    for source, targets in graph.items():
        for target in targets:
            if target in inbound:
                inbound[target] += 1
            else:
                inbound[target] = 1
    return inbound


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Returns list of unique cycles using DFS and canonicalization."""
    cycles: List[List[str]] = []
    visited_global: Set[str] = set()
    path_set: Set[str] = set()
    nodes = sorted(graph.keys())

    def visit(node: str, current_path: List[str]) -> None:
        """Recursively visits nodes to find import cycles."""
        visited_global.add(node)
        path_set.add(node)
        current_path.append(node)
        neighbors = sorted(list(graph.get(node, set())))

        for neighbor in neighbors:
            if neighbor in path_set:
                try:
                    idx = current_path.index(neighbor)
                    cycle = current_path[idx:]
                    if cycle not in cycles:
                        cycles.append(cycle[:])
                except ValueError:
                    pass
            elif neighbor not in visited_global:
                visit(neighbor, current_path)

        path_set.remove(node)
        current_path.pop()

    for node in nodes:
        if node not in visited_global:
            visit(node, [])

    # Canonicalize cycles to remove duplicates (e.g., A-B-A and B-A-B)
    unique_cycles: List[List[str]] = []
    seen_cycle_sets: Set[Tuple[str, ...]] = set()
    for cycle in cycles:
        if len(cycle) < 2:
            continue
        min_node = min(cycle)
        min_idx = cycle.index(min_node)
        canonical = tuple(cycle[min_idx:] + cycle[:min_idx])
        if canonical not in seen_cycle_sets:
            seen_cycle_sets.add(canonical)
            unique_cycles.append(list(canonical))
    return unique_cycles


def get_project_issues(
    path: str, py_files: List[str], profile: Dict[str, Any]
) -> Tuple[int, List[str]]:
    """Analyzes global project health: docs, god modules, and entropy."""
    penalty = 0
    issues: List[str] = []

    # 1. Documentation Check
    missing_docs = scan_project_docs(path, cast(List[str], profile.get("required_files", [])))
    if missing_docs:
        msg = f"Missing Critical Agent Docs: {', '.join(missing_docs)}"
        penalty += len(missing_docs) * 15
        issues.append(msg)

    graph = get_import_graph(path)
    inbound = get_inbound_imports(graph)
    god_modules = [mod for mod, count in inbound.items() if count > 50]
    if god_modules:
        msg = f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}"
        penalty += len(god_modules) * 10
        issues.append(msg)

    entropy_stats = auditor.get_crowded_directories(path, threshold=50)
    crowded_dirs = list(entropy_stats.keys())
    if crowded_dirs:
        msg = f"High Directory Entropy (>50 files): {', '.join(crowded_dirs)}"
        penalty += len(crowded_dirs) * 5
        issues.append(msg)

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
    """Orchestrates the full project analysis pipeline."""
    if profile is None:
        profile = PROFILES.get(agent, PROFILES["generic"])

    py_files = _collect_python_files(path)
    all_py_files = py_files[:]

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

        rel_path = os.path.relpath(
            filepath, start=path if os.path.isdir(path) else os.path.dirname(path)
        )
        file_results.append(
            {
                "file": rel_path,
                "score": score,
                "issues": issues,
                "loc": loc,
                "complexity": complexity,
                "type_coverage": type_safety,
                "function_metrics": metrics_data,
                "tokens": count_tokens(filepath),
                "acl": max([m["acl"] for m in metrics_data]) if metrics_data else 0.0,
            }
        )

    penalty, project_issues = get_project_issues(path, all_py_files, profile)
    project_score = max(0, 100 - penalty)

    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    graph = get_import_graph(path)
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
        "missing_docs": scan_project_docs(path, cast(List[str], profile.get("required_files", []))),
        "project_issues": project_issues,
        "dep_analysis": dep_analysis_val,
        "directory_stats": directory_stats,
    }