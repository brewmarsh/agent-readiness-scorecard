import os
import ast
from typing import List, Dict, Set, Tuple


def _is_analyzable_file(filename: str) -> bool:
    """
    Checks if a file is analyzable based on extension or name.
    Supported types: Python, Markdown, JavaScript, TypeScript, Java, Dockerfile.
    """
    return (
        filename.endswith(".py")
        or filename.endswith(".md")
        or filename.endswith(".js")
        or filename.endswith(".jsx")
        or filename.endswith(".ts")
        or filename.endswith(".tsx")
        or filename.endswith(".java")
        or filename == "Dockerfile"
        or filename.startswith("Dockerfile.")
    )


def _scan_directory(path: str) -> List[str]:
    """
    Recursively scans a directory for analyzable files, ignoring hidden directories.

    Args:
        path (str): The directory to scan.

    Returns:
        List[str]: List of absolute paths to analyzable files.
    """
    analyzable_files = []
    for root, _, files in os.walk(path):
        parts = root.split(os.sep)
        # Skip hidden directories (e.g., .git, .venv, .pytest_cache)
        if any(p.startswith(".") and p != "." for p in parts):
            continue
        for file in files:
            if _is_analyzable_file(file):
                analyzable_files.append(os.path.join(root, file))
    return analyzable_files


def collect_python_files(path: str) -> List[str]:
    """
    Collects all analyzable files in the given path, ignoring hidden directories.
    Note: Kept as collect_python_files for backward compatibility.

    Args:
        path (str): The path to scan.

    Returns:
        List[str]: A list of absolute paths to analyzable files.
    """
    if os.path.isfile(path) and _is_analyzable_file(os.path.basename(path)):
        return [path]
    elif os.path.isdir(path):
        return _scan_directory(path)
    return []


def _extract_imports_from_ast(tree: ast.AST) -> Set[str]:
    """
    Walks the AST tree to extract imported module names.
    """
    imported_names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module)
    return imported_names


def parse_imports(filepath: str) -> Set[str]:
    """
    Parses a Python file and returns a set of imported module names.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filename=filepath)
        return _extract_imports_from_ast(tree)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return set()


def _resolve_initial_paths(root_path: str) -> Tuple[str, List[str]]:
    """
    Resolves the base directory and list of relative file paths for analysis.
    """
    if os.path.isfile(root_path) and _is_analyzable_file(os.path.basename(root_path)):
        all_files = [os.path.basename(root_path)]
        root_path_dir = os.path.dirname(root_path)
        return root_path_dir, all_files
    else:
        full_paths = collect_python_files(root_path)
        all_files = [os.path.relpath(f, start=root_path) for f in full_paths]
        return root_path, all_files


def get_import_graph(root_path: str) -> Dict[str, Set[str]]:
    """
    Builds a dependency graph of the project (Python only for AST parsing).
    """
    base_dir, all_files = _resolve_initial_paths(root_path)
    graph: Dict[str, Set[str]] = {f: set() for f in all_files}

    for rel_path in all_files:
        if not rel_path.endswith(".py"):
            continue
            
        full_path = os.path.join(base_dir, rel_path)
        imported_names = parse_imports(full_path)

        for name in imported_names:
            suffix = name.replace(".", os.sep)
            for candidate in all_files:
                if candidate == rel_path:
                    continue
                candidate_no_ext = os.path.splitext(candidate)[0]
                # Match if candidate matches the import suffix
                if candidate_no_ext.endswith(suffix):
                    match_len = len(suffix)
                    if len(candidate_no_ext) == match_len or candidate_no_ext[-(match_len + 1)] == os.sep:
                        graph[rel_path].add(candidate)

    return graph


def get_inbound_imports(graph: Dict[str, Set[str]]) -> Dict[str, int]:
    """
    Returns {file: count} of inbound imports to identify 'God Modules'.
    """
    inbound: Dict[str, int] = {node: 0 for node in graph}
    for targets in graph.values():
        for target in targets:
            if target in inbound:
                inbound[target] += 1
    return inbound


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Returns list of unique circular dependency paths using DFS and canonicalization.
    """
    cycles: List[List[str]] = []
    visited_global: Set[str] = set()
    
    nodes = sorted(graph.keys())
    for node in nodes:
        if node not in visited_global:
            _find_cycles_dfs(node, graph, visited_global, set(), [], cycles)
            
    return _canonicalize_cycles(cycles)


def _find_cycles_dfs(node, graph, visited_global, path_set, current_path, cycles):
    visited_global.add(node)
    path_set.add(node)
    current_path.append(node)

    neighbors = sorted(list(graph.get(node, set())))
    for neighbor in neighbors:
        if neighbor in path_set:
            idx = current_path.index(neighbor)
            cycle = current_path[idx:]
            cycles.append(cycle[:])
        elif neighbor not in visited_global:
            _find_cycles_dfs(neighbor, graph, visited_global, path_set, current_path, cycles)

    path_set.remove(node)
    current_path.pop()


def _canonicalize_cycles(cycles: List[List[str]]) -> List[List[str]]:
    unique_cycles = []
    seen = set()
    for cycle in cycles:
        if len(cycle) < 2: continue
        min_node = min(cycle)
        min_idx = cycle.index(min_node)
        canonical = tuple(cycle[min_idx:] + cycle[:min_idx])
        if canonical not in seen:
            seen.add(canonical)
            unique_cycles.append(list(canonical))
    return unique_cycles


def calculate_context_tokens(graph: Dict[str, Set[str]], file_tokens: Dict[str, int]) -> Dict[str, int]:
    """
    Calculates cumulative tokens for a file and all its transitive dependencies.
    """
    context_tokens = {}
    for file in graph:
        visited = set()
        stack = [file]
        while stack:
            curr = stack.pop()
            if curr not in visited:
                visited.add(curr)
                stack.extend(graph.get(curr, set()))
        
        context_tokens[file] = sum(file_tokens.get(f, 0) for f in visited)
    return context_tokens