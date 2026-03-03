import os
import ast
from typing import List, Dict, Set, Tuple


def _is_analyzable_file(filename: str) -> bool:
    """
    Checks if a file is analyzable based on extension or name.
    Supported types: Python, Markdown, JavaScript, TypeScript, Dockerfile, Config.
    """
    return (
        filename.endswith(".py")
        or filename.endswith(".md")
        or filename.endswith(".js")
        or filename.endswith(".jsx")
        or filename.endswith(".ts")
        or filename.endswith(".tsx")
        or filename == "Dockerfile"
        or filename.startswith("Dockerfile.")
        or filename.endswith(".json")
        or filename.endswith(".yaml")
        or filename.endswith(".yml")
        or filename.endswith(".toml")
    )


def _scan_directory(path: str) -> List[str]:
    """
    Recursively scans a directory for analyzable files, 
    ignoring hidden directories, node_modules, and virtual environments.
    """
    analyzable_files = []
    # RESOLUTION: Combined explicit exclusion list with top-down in-place pruning
    excluded_dirs = {"node_modules", "venv", ".venv", ".git"}
    
    for root, dirs, files in os.walk(path, topdown=True):
        # Prune excluded and hidden directories in-place to avoid unnecessary traversal
        dirs[:] = [
            d for d in dirs
            if d not in excluded_dirs and not (d.startswith(".") and d != ".")
        ]

        for file in files:
            if _is_analyzable_file(file):
                analyzable_files.append(os.path.join(root, file))
    return analyzable_files


def collect_python_files(path: str) -> List[str]:
    """
    Collects all analyzable files in the given path.
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
    # RESOLUTION: Added ValueError to catch invalid decimal literals 
    # if a non-Python file somehow slips through.
    except (SyntaxError, ValueError, UnicodeDecodeError, FileNotFoundError):
        return set()


def get_import_graph(root_path: str) -> Dict[str, Set[str]]:
    """
    Builds a dependency graph of the project.
    """
    base_dir, all_py_files = _resolve_initial_paths(root_path)
    graph: Dict[str, Set[str]] = {f: set() for f in all_py_files}

    for rel_path in all_py_files:
        full_path = os.path.join(base_dir, rel_path)
        # RESOLUTION: Strict type guard—Only attempt Python parsing on .py files
        if full_path.endswith(".py"):
            imported_names = parse_imports(full_path)
        else:
            imported_names = set()

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
    Returns list of unique circular dependency paths.
    """
    raw_cycles = _find_raw_cycles(graph)
    return _canonicalize_cycles(raw_cycles)


def _find_raw_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    cycles: List[List[str]] = []
    visited_global: Set[str] = set()
    nodes = sorted(graph.keys())

    for node in nodes:
        if node not in visited_global:
            _dfs_visit_cycle(node, graph, visited_global, set(), [], cycles)
    return cycles


def _dfs_visit_cycle(node, graph, visited_global, path_set, current_path, cycles):
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
            _dfs_visit_cycle(neighbor, graph, visited_global, path_set, current_path, cycles)

    path_set.remove(node)
    current_path.pop()


def _canonicalize_cycles(cycles: List[List[str]]) -> List[List[str]]:
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


def calculate_context_tokens(
    graph: Dict[str, Set[str]], file_tokens: Dict[str, int]
) -> Dict[str, int]:
    """
    Calculates cumulative token counts for files and their transitive dependencies.
    """
    context_tokens: Dict[str, int] = {}
    for file in graph:
        visited = _get_transitive_dependencies(file, graph)
        total_tokens = sum(file_tokens.get(f, 0) for f in visited)
        context_tokens[file] = total_tokens
    return context_tokens


def _get_transitive_dependencies(start_node: str, graph: Dict[str, Set[str]]) -> Set[str]:
    visited: Set[str] = set()
    queue = [start_node]
    visited.add(start_node)
    idx = 0
    while idx < len(queue):
        current = queue[idx]
        idx += 1
        for neighbor in graph.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


def _resolve_initial_paths(root_path: str) -> Tuple[str, List[str]]:
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        all_py_files = [os.path.basename(root_path)]
        return os.path.dirname(root_path), all_py_files
    else:
        full_paths = collect_python_files(root_path)
        return root_path, [os.path.relpath(f, start=root_path) for f in full_paths]