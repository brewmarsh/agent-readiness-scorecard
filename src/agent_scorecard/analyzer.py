import os
import ast
from typing import Dict, Any, List, Optional
from .constants import PROFILES
from .scoring import score_file
from . import auditor

# --- METRICS & GRAPH ANALYSIS ---

# Re-export metrics for backward compatibility
from .metrics import (
    get_loc,
    get_complexity_score,
    check_type_hints,
    calculate_acl,
    get_function_stats,
)

def scan_project_docs(root_path, required_files):
    """Checks for existence of agent-critical markdown files."""
    missing = []
    root_files = [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing

def get_import_graph(root_path):
    """Builds a dependency graph of the project."""
    all_py_files = []
    if os.path.isfile(root_path):
        if root_path.endswith(".py"):
             all_py_files.append(os.path.basename(root_path))
             root_path = os.path.dirname(root_path)
    else:
        for root, _, files in os.walk(root_path):
            parts = root.split(os.sep)
            if any(p.startswith(".") and p != "." for p in parts):
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start=root_path)
                    all_py_files.append(rel_path)

    graph = {f: set() for f in all_py_files}

    for rel_path in all_py_files:
        full_path = os.path.join(root_path, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code, filename=full_path)
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            continue

        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module)
        
        for name in imported_names:
            suffix = name.replace(".", os.sep)
            for candidate in all_py_files:
                if candidate == rel_path:
                    continue
                candidate_no_ext = os.path.splitext(candidate)[0]
                if candidate_no_ext.endswith(suffix):
                    match_len = len(suffix)
                    if len(candidate_no_ext) == match_len or candidate_no_ext[-(match_len+1)] == os.sep:
                        graph[rel_path].add(candidate)
    return graph

def get_inbound_imports(graph):
    """Returns {file: count} of inbound imports."""
    inbound = {node: 0 for node in graph}
    for source, targets in graph.items():
        for target in targets:
            if target in inbound:
                inbound[target] += 1
            else:
                inbound[target] = 1
    return inbound

def detect_cycles(graph):
    """Returns list of cycles (list of nodes in cycle)."""
    cycles = []
    visited_global = set()
    path_set = set()
    nodes = sorted(graph.keys())

    def visit(node, current_path):
        visited_global.add(node)
        path_set.add(node)
        current_path.append(node)
        neighbors = sorted(list(graph.get(node, [])))

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

    unique_cycles = []
    seen_cycle_sets = set()
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

def get_project_issues(path, py_files, profile):
    """Checks for project-level issues."""
    penalty = 0
    issues = []

    missing_docs = scan_project_docs(path, profile.get("required_files", []))
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

    # 3. Directory Entropy
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

def perform_analysis(path: str, agent: str, limit_to_files: Optional[List] = None) -> Dict[str, Any]:
    """Orchestrates the full project analysis."""
    profile = PROFILES[agent]

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

    all_py_files = py_files[:]
    if limit_to_files:
        # Filter 'py_files' (files to score) but keep 'all_files' for graph analysis
        py_files = [f for f in py_files if any(f.endswith(changed) for changed in limit_to_files)]

    file_results = []
    file_scores = []

    for filepath in py_files:
        score, issues, loc, complexity, type_safety, metrics = score_file(filepath, profile)
        file_scores.append(score)

        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        file_results.append({
            "file": rel_path,
            "score": score,
            "issues": issues,
            "loc": loc,
            "complexity": complexity,
            "type_coverage": type_safety,
            "function_metrics": metrics
        })

    # Project Level
    penalty, project_issues = get_project_issues(path, all_py_files, profile)
    project_score = max(0, 100 - penalty)

    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    # Dependency Analysis for main.py
    graph = get_import_graph(path)
    inbound = get_inbound_imports(graph)
    cycles = detect_cycles(graph)
    god_modules = {mod: count for mod, count in inbound.items() if count > 50}

    dep_analysis = {
        "cycles": cycles,
        "god_modules": god_modules
    }

    directory_stats = []
    entropy = auditor.get_crowded_directories(path if os.path.isdir(path) else os.path.dirname(path), threshold=50)
    for p, count in entropy.items():
        directory_stats.append({
            "path": p,
            "file_count": count
        })

    return {
        "file_results": file_results,
        "final_score": final_score,
        "missing_docs": scan_project_docs(path, profile.get("required_files", [])),
        "project_issues": project_issues,
        "dep_analysis": dep_analysis,
        "directory_stats": directory_stats
    }
