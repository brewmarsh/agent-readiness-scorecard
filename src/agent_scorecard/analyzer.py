import os
import ast
import click
import mccabe
from .constants import PROFILES
from .checks import scan_project_docs
from .scoring import score_file

class DefaultGroup(click.Group):
    """Click group that defaults to 'score' if no subcommand is provided."""
    def __init__(self, *args, **kwargs):
        self.default_command = 'score'
        super().__init__(*args, **kwargs)

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and not args[0].startswith('-'):
                args.insert(0, self.default_command)
            elif not args:
                args.insert(0, self.default_command)
            return super().resolve_command(ctx, args)

def perform_analysis(path, agent_name):
    """Core analysis logic that returns data for presentation."""
    if agent_name not in PROFILES:
        agent_name = "generic"
    profile = PROFILES[agent_name]

    # 1. Project Level Check
    missing_docs = scan_project_docs(path, profile.get("required_files", []))

    # NEW: Get other project issues from beta features
    # Gather all python files for graph analysis
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

    penalty, project_issues = get_project_issues(path, py_files, profile)
    project_score = max(0, 100 - penalty)

    # 2. File Level Check
    file_results = []
    for filepath in py_files:
        score, issues, loc, complexity, type_cov, func_metrics = score_file(filepath, profile)
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        file_results.append({
            "file": rel_path,
            "score": score,
            "issues": issues,
            "loc": loc,
            "complexity": complexity,
            "type_coverage": type_cov,
            "function_metrics": func_metrics
        })

    # 3. Aggregation
    avg_file_score = sum(f["score"] for f in file_results) / len(file_results) if file_results else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    return {
        "agent": agent_name,
        "profile": profile,
        "final_score": final_score,
        "project_score": project_score,
        "missing_docs": missing_docs,
        "project_issues": project_issues,
        "file_results": file_results
    }

# --- METRICS & GRAPH ANALYSIS (Resolved from Beta) ---

def calculate_acl(complexity, loc):
    """Calculates Agent Cognitive Load (ACL).
    Formula: ACL = CC + (LLOC / 20)
    """
    return complexity + (loc / 20.0)

def get_directory_entropy(root_path, threshold=50):
    """Returns directories with file count > threshold."""
    entropy_stats = {}
    if os.path.isfile(root_path):
        return entropy_stats

    for root, dirs, files in os.walk(root_path):
        # Ignore hidden directories like .git
        parts = root.split(os.sep)
        if any(p.startswith(".") and p != "." for p in parts):
            continue

        count = len(files)
        if count > threshold:
            rel_path = os.path.relpath(root, start=root_path)
            if rel_path == ".":
                rel_path = os.path.basename(os.path.abspath(root_path))
            entropy_stats[rel_path] = count
    return entropy_stats

def get_import_graph(root_path):
    """
    Builds a dependency graph of the project.
    Returns: { file_path: { set of imported_file_paths } }
    """
    all_py_files = []
    if os.path.isfile(root_path):
        if root_path.endswith(".py"):
             all_py_files.append(os.path.basename(root_path))
             root_path = os.path.dirname(root_path) # Adjust root for single file
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

        # Try to match imported names to files
        for name in imported_names:
            # Convert module dots to path separators
            suffix = name.replace(".", os.sep)

            for candidate in all_py_files:
                if candidate == rel_path: continue

                # Let's strip extension
                candidate_no_ext = os.path.splitext(candidate)[0]

                # if candidate_no_ext ends with suffix, it's a potential match
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
        if len(cycle) < 2: continue

        min_node = min(cycle)
        min_idx = cycle.index(min_node)
        canonical = tuple(cycle[min_idx:] + cycle[:min_idx])

        if canonical not in seen_cycle_sets:
            seen_cycle_sets.add(canonical)
            unique_cycles.append(list(canonical))

    return unique_cycles

def get_function_stats(filepath):
    """
    Returns a list of statistics for each function in the file.
    Each item is a dict: {name, lineno, complexity, loc, acl}
    ACL = CC + (LOC / 20)
    """
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    # Get complexities from mccabe
    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    # Map (lineno) -> complexity
    complexity_map = {}
    for graph in visitor.graphs.values():
        complexity_map[graph.lineno] = graph.complexity()

    stats = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line) # Python 3.8+
            loc = end_line - start_line + 1

            complexity = complexity_map.get(start_line, 1) # Default to 1 if not found
            acl = calculate_acl(complexity, loc)

            stats.append({
                "name": node.name,
                "lineno": start_line,
                "complexity": complexity,
                "loc": loc,
                "acl": acl
            })
    return stats

def get_project_issues(path, py_files, profile):
    """
    Checks for project-level issues: Missing Docs, God Modules, Directory Entropy.
    Returns (penalty_score, issues_list).
    """
    penalty = 0
    issues = []

    # 1. Missing Docs
    missing_docs = scan_project_docs(path, profile.get("required_files", []))
    if missing_docs:
        msg = f"Missing Critical Agent Docs: {', '.join(missing_docs)}"
        penalty += len(missing_docs) * 15
        issues.append(msg)

    # 2. God Modules (using beta's graph analysis)
    graph = get_import_graph(path)
    inbound = get_inbound_imports(graph)

    god_modules = [mod for mod, count in inbound.items() if count > 50]
    if god_modules:
        msg = f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}"
        penalty += len(god_modules) * 10
        issues.append(msg)

    # 3. Directory Entropy
    entropy_stats = get_directory_entropy(path, threshold=50)
    crowded_dirs = list(entropy_stats.keys())

    if crowded_dirs:
        msg = f"High Directory Entropy (>50 files): {', '.join(crowded_dirs)}"
        penalty += len(crowded_dirs) * 5
        issues.append(msg)

    # 4. Circular Dependencies (Bonus from beta)
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = ["->".join(c) for c in cycles]
        msg = f"Circular Dependencies Detected: {', '.join(cycle_strs)}"
        penalty += len(cycles) * 5
        issues.append(msg)

    return penalty, issues
