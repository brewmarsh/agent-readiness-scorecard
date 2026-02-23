import os
import ast
from typing import List, Dict, Any, Tuple, Set, Optional, cast
from .constants import PROFILES
from .scoring import score_file
from . import auditor
from .types import FileAnalysisResult, AnalysisResult

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


def _collect_python_files(path: str) -> List[str]:
    """
    Collects all Python files in the given path, ignoring hidden directories.
    """
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
    """
    Parses a Python file and returns a set of imported module names.
    """
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


def get_import_graph(root_path: str) -> Tuple[Dict[str, Set[str]], Dict[str, int]]:
    """
    Builds a dependency graph and calculates individual token counts.
    """
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        all_py_files = [os.path.basename(root_path)]
        root_path = os.path.dirname(root_path)
    else:
        full_paths = _collect_python_files(root_path)
        all_py_files = [os.path.relpath(f, start=root_path) for f in full_paths]

    graph: Dict[str, Set[str]] = {f: set() for f in all_py_files}
    token_counts: Dict[str, int] = {}

    for rel_path in all_py_files:
        full_path = os.path.join(root_path, rel_path)
        token_counts[rel_path] = auditor.count_python_tokens(full_path)
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
    return graph, token_counts


def get_inbound_imports(graph: Dict[str, Set[str]]) -> Dict[str, int]:
    """
    Returns {file: count} of inbound imports to identify 'God Modules'.
    """
    inbound: Dict[str, int] = {node: 0 for node in graph}
    for source, targets in graph.items():
        for target in targets:
            if target in inbound:
                inbound[target] += 1
    return inbound


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Returns list of unique cycles using DFS.
    """
    cycles: List[List[str]] = []
    visited_global: Set[str] = set()
    path_set: Set[str] = set()
    nodes = sorted(graph.keys())

    def visit(node: str, current_path: List[str]) -> None:
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

    # Canonicalize
    unique_cycles = []
    seen = set()
    for cycle in cycles:
        if len(cycle) < 2:
            continue
        min_node = min(cycle)
        idx = cycle.index(min_node)
        canonical = tuple(cycle[idx:] + cycle[:idx])
        if canonical not in seen:
            seen.add(canonical)
            unique_cycles.append(list(canonical))
    return unique_cycles


def _calculate_cumulative_tokens(
    graph: Dict[str, Set[str]], file_tokens: Dict[str, int]
) -> Dict[str, int]:
    """
    Calculates the cumulative token budget including all unique reachable local dependencies.
    """
    cumulative_map: Dict[str, int] = {}
    for start_node in graph:
        reachable: Set[str] = set()
        stack = [start_node]
        while stack:
            current = stack.pop()
            if current not in reachable:
                reachable.add(current)
                for neighbor in graph.get(current, set()):
                    stack.append(neighbor)
        cumulative_map[start_node] = sum(file_tokens.get(f, 0) for f in reachable)
    return cumulative_map


def get_project_issues(
    path: str, py_files: List[str], profile: Dict[str, Any]
) -> Tuple[int, List[str]]:
    """
    Analyzes global project health: docs, environment, god modules, and entropy.
    """
    penalty = 0
    issues: List[str] = []

    missing_docs = scan_project_docs(path, cast(List[str], profile.get("required_files", [])))
    if missing_docs:
        penalty += len(missing_docs) * 15
        issues.append(f"Missing Critical Agent Docs: {', '.join(missing_docs)}")

    health = auditor.check_environment_health(path)
    if not health.get("pyproject_valid", True):
        penalty += 20
        issues.append("Malformed pyproject.toml detected")

    graph, _ = get_import_graph(path)
    inbound = get_inbound_imports(graph)
    god_modules = [mod for mod, count in inbound.items() if count > 50]
    if god_modules:
        penalty += len(god_modules) * 10
        issues.append(f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}")

    entropy_stats = auditor.get_crowded_directories(path, threshold=50)
    if entropy_stats:
        penalty += len(entropy_stats) * 5
        issues.append(f"High Directory Entropy (>50 files): {', '.join(entropy_stats.keys())}")

    cycles = detect_cycles(graph)
    if cycles:
        penalty += len(cycles) * 5
        issues.append(f"Circular Dependencies Detected: {len(cycles)}")

    return penalty, issues


def perform_analysis(
    path: str,
    agent: str = "generic",
    limit_to_files: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """
    Orchestrates the full project analysis pipeline with Context Economics.
    """
    if profile is None:
        profile = PROFILES.get(agent, PROFILES["generic"])

    project_root = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    py_files = _collect_python_files(path)
    all_py_files = py_files[:]

    # Build graph and calculate cumulative tokens (Context Economics)
    graph, individual_tokens = get_import_graph(path)
    cumulative_tokens_map = _calculate_cumulative_tokens(graph, individual_tokens)

    if limit_to_files:
        py_files = [f for f in py_files if any(f.endswith(changed) for changed in limit_to_files)]

    file_results: List[FileAnalysisResult] = []
    file_scores: List[int] = []

    for filepath in py_files:
        rel_path = os.path.relpath(filepath, start=project_root)
        cum_tokens = cumulative_tokens_map.get(rel_path, 0)

        score, issues, loc, complexity, type_safety, metrics_data = score_file(
            filepath, profile, thresholds=thresholds, cumulative_tokens=cum_tokens
        )
        file_scores.append(score)

        file_results.append({
            "file": rel_path,
            "score": score,
            "issues": issues,
            "loc": loc,
            "complexity": complexity,
            "type_coverage": type_safety,
            "function_metrics": metrics_data,
            "tokens": individual_tokens.get(rel_path, auditor.count_python_tokens(filepath)),
            "cumulative_tokens": cum_tokens,
            "acl": max([m["acl"] for m in metrics_data]) if metrics_data else 0.0,
        })

    penalty, project_issues = get_project_issues(project_root, all_py_files, profile)
    project_score = max(0, 100 - penalty)
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    return {
        "file_results": file_results,
        "final_score": final_score,
        "missing_docs": scan_project_docs(project_root, cast(List[str], profile.get("required_files", []))),
        "project_issues": project_issues,
        "dep_analysis": {"cycles": detect_cycles(graph), "god_modules": {m: c for m, c in get_inbound_imports(graph).items() if c > 50}},
        "directory_stats": [{"path": p, "file_count": c} for p, c in auditor.get_crowded_directories(path, threshold=50).items()],
    }