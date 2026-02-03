import os
import ast
import mccabe
from collections import Counter
from typing import List, Dict, Any, Tuple

# --- Basic Metrics ---

def get_loc(filepath):
    """Returns lines of code excluding whitespace/comments roughly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except UnicodeDecodeError:
        return 0

def get_complexity_score(filepath):
    """Returns average cyclomatic complexity."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0

    return sum(complexities) / len(complexities)

def check_type_hints(filepath):
    """Returns type hint coverage percentage."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return 100

    typed_functions = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        if has_return or has_args:
            typed_functions += 1

    return (typed_functions / len(functions)) * 100

def scan_project_docs(root_path, required_files):
    """Checks for existence of agent-critical markdown files."""
    missing = []
    # Normalize checking logic to look in the root of the provided path
    root_files = [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing

# --- METRICS & GRAPH ANALYSIS ---

def calculate_acl(complexity, loc):
    """Calculates Agent Cognitive Load (ACL).
    Formula: ACL = CC + (LLOC / 20)
    """
    return complexity + (loc / 20.0)

def count_tokens(filepath: str) -> int:
    """Estimates the number of tokens in a file (approx 4 chars/token)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return len(content) // 4
    except UnicodeDecodeError:
        return 0

def get_directory_entropy(root_path, threshold=50):
    """Returns directories with file count > threshold."""
    entropy_stats = {}
    if os.path.isfile(root_path):
        return entropy_stats

    for root, dirs, files in os.walk(root_path):
        # Ignore hidden directories like .git
        if any(part.startswith(".") for part in root.split(os.sep)):
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
            if any(part.startswith(".") for part in root.split(os.sep)):
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
                
                # Check if candidate ends with suffix + ".py" (or matches module path)
                candidate_no_ext = os.path.splitext(candidate)[0]
                
                if candidate_no_ext.endswith(suffix):
                    match_len = len(suffix)
                    # Check boundary to avoid partial matches
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
                # Cycle found
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
        
        # Canonical representation
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
    
    # 2. God Modules (using graph analysis)
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

    # 4. Circular Dependencies
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = ["->".join(c) for c in cycles]
        msg = f"Circular Dependencies Detected: {', '.join(cycle_strs)}"
        penalty += len(cycles) * 5
        issues.append(msg)
        
    return penalty, issues

def analyze_project(root_path: str) -> Dict[str, Any]:
    """Orchestrates the full project analysis (Advisor Mode)."""

    py_files = []
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        py_files = [root_path]
    elif os.path.isdir(root_path):
        for root, _, files in os.walk(root_path):
            if any(part.startswith(".") for part in root.split(os.sep)):
                continue
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    file_stats = []
    for fp in py_files:
        rel_path = os.path.relpath(fp, start=root_path if os.path.isdir(root_path) else os.path.dirname(root_path))
        file_stats.append({
            "file": rel_path,
            "loc": get_loc(fp),
            "complexity": get_complexity_score(fp),
            "type_coverage": check_type_hints(fp),
            "tokens": count_tokens(fp),
            "functions": get_function_stats(fp)
        })

    # Use Helper functions
    graph = get_import_graph(root_path if os.path.isdir(root_path) else os.path.dirname(root_path))
    inbound_counts = get_inbound_imports(graph)
    cycles = detect_cycles(graph)

    god_modules = {f: count for f, count in inbound_counts.items() if count > 50}

    dependency_stats = {
        "graph": {k: list(v) for k, v in graph.items()},
        "inbound_counts": inbound_counts,
        "god_modules": god_modules,
        "cycles": cycles
    }

    directory_stats = []
    entropy = get_directory_entropy(root_path if os.path.isdir(root_path) else os.path.dirname(root_path), threshold=50)
    for path, count in entropy.items():
        directory_stats.append({
            "path": path,
            "file_count": count
        })

    return {
        "files": file_stats,
        "dependencies": dependency_stats,
        "directories": directory_stats
    }