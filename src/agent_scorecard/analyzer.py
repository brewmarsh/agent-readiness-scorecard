import os
import ast
import mccabe
import collections
from typing import List, Dict, Any, Tuple

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

# --- Advisor Mode Metrics ---

def count_tokens(filepath: str) -> int:
    """Estimates the number of tokens in a file (approx 4 chars/token)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return len(content) // 4
    except UnicodeDecodeError:
        return 0

def get_imports(filepath: str) -> List[str]:
    """Parses AST to find all imported modules."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def get_function_stats(filepath: str) -> List[Dict[str, Any]]:
    """Returns detailed stats per function: complexity, LOC, ACL."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    # Map lineno to FunctionDef/AsyncFunctionDef node
    lineno_to_node = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lineno_to_node[node.lineno] = node

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    stats = []
    for graph in visitor.graphs.values():
        name = graph.name
        if ": '" in name:
            try:
                name = name.split("'")[1]
            except IndexError:
                pass

        complexity = graph.complexity()

        # Estimate LOC of function using mapped node
        loc = 0
        if graph.lineno in lineno_to_node:
            node = lineno_to_node[graph.lineno]
            # Ensure we have end_lineno (Python 3.8+)
            end_line = getattr(node, 'end_lineno', node.lineno)
            loc = max(0, end_line - node.lineno)

        acl = complexity + (loc / 20.0)

        stats.append({
            "name": name,
            "complexity": complexity,
            "loc": loc,
            "acl": acl
        })
    return stats

def analyze_dependency_graph(file_paths: List[str], root_path: str) -> Dict[str, Any]:
    """Builds dependency graph and detects circular deps and God modules."""

    # Map from relative file path to list of imported modules
    graph = {}
    # Map from module name to file path (heuristic)
    module_to_file = {}

    rel_paths = []
    for fp in file_paths:
        rel = os.path.relpath(fp, root_path)
        # Assuming python files. module name is path without extension, replacing sep with dot
        module_name = os.path.splitext(rel)[0].replace(os.path.sep, ".")
        module_to_file[module_name] = rel
        rel_paths.append(rel)

    for fp in file_paths:
        rel = os.path.relpath(fp, root_path)
        imports = get_imports(fp)
        resolved_imports = []
        for imp in imports:
            # Try to resolve import to a local file
            # Simple resolution: Exact match
            if imp in module_to_file:
                resolved_imports.append(module_to_file[imp])
            else:
                # Try partial match for submodules e.g. from . import x
                # This is hard without full resolution logic, so we'll stick to simple logic for now
                # Check if import starts with any known module
                for mod, f in module_to_file.items():
                    if imp == mod or imp.startswith(mod + "."):
                        resolved_imports.append(f)
                        # Avoid duplicates if multiple matches (shouldn't happen with exact prefixes)
                        break

        graph[rel] = set(resolved_imports)

    # Inbound counts (God Modules)
    inbound_counts = collections.defaultdict(int)
    for src, targets in graph.items():
        for target in targets:
            inbound_counts[target] += 1

    god_modules = {f: count for f, count in inbound_counts.items() if count > 50}

    # Circular Dependencies
    cycles = []
    visited = set()
    path = []

    def dfs(node, current_path):
        if node in current_path:
            cycle = current_path[current_path.index(node):]
            # Normalize cycle to avoid duplicates (e.g. A->B->A and B->A->B)
            if cycle:
                # Create a canonical representation
                min_node = min(cycle)
                start_idx = cycle.index(min_node)
                canonical_cycle = tuple(cycle[start_idx:] + cycle[:start_idx])
                cycles.append(canonical_cycle)
            return

        if node in visited:
            return

        visited.add(node)
        current_path.append(node)

        for neighbor in graph.get(node, []):
            dfs(neighbor, current_path)

        current_path.pop()

    for node in graph:
        if node not in visited:
            dfs(node, [])

    unique_cycles = sorted(list(set(cycles)))

    return {
        "graph": {k: list(v) for k, v in graph.items()},
        "inbound_counts": dict(inbound_counts),
        "god_modules": god_modules,
        "cycles": unique_cycles
    }

def check_directory_entropy(root_path: str) -> List[Dict[str, Any]]:
    """Checks for directories with too many files."""
    results = []
    for root, dirs, files in os.walk(root_path):
        if ".git" in root:
            continue
        if len(files) > 0:
            results.append({
                "path": os.path.relpath(root, root_path),
                "file_count": len(files)
            })
    return results

def analyze_project(root_path: str) -> Dict[str, Any]:
    """Orchestrates the full project analysis."""

    py_files = []
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        py_files = [root_path]
    elif os.path.isdir(root_path):
        for root, _, files in os.walk(root_path):
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

    dependency_stats = analyze_dependency_graph(py_files, root_path if os.path.isdir(root_path) else os.path.dirname(root_path))
    directory_stats = check_directory_entropy(root_path if os.path.isdir(root_path) else os.path.dirname(root_path))

    return {
        "files": file_stats,
        "dependencies": dependency_stats,
        "directories": directory_stats
    }
