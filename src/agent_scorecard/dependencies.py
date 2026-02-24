import os
import ast
from typing import List, Dict, Set, Tuple


def _scan_directory(path: str) -> List[str]:
    """
    Recursively scans a directory for analyzable files (Python, Markdown),
    ignoring hidden directories.

    Args:
        path (str): The directory to scan.

    Returns:
        List[str]: List of absolute paths to analyzable files.
    """
    analyzable_files = []
    for root, _, files in os.walk(path):
        parts = root.split(os.sep)
        if any(p.startswith(".") and p != "." for p in parts):
            continue
        for file in files:
            if (
                file.endswith(".py")
                or file.endswith(".md")
                or file.endswith(".js")
                or file.endswith(".jsx")
                or file.endswith(".ts")
                or file.endswith(".tsx")
                or file.endswith(".java")
                or file == "Dockerfile"
                or file.startswith("Dockerfile.")
            ):
                analyzable_files.append(os.path.join(root, file))
    return analyzable_files


def collect_python_files(path: str) -> List[str]:
    """
    Collects all analyzable files in the given path, ignoring hidden directories.
    Note: Kept as collect_python_files for backward compatibility but now includes .md and Dockerfiles.

    Args:
        path (str): The path to scan.

    Returns:
        List[str]: A list of absolute paths to analyzable files.
    """
    if os.path.isfile(path) and (
        path.endswith(".py")
        or path.endswith(".md")
        or path.endswith(".js")
        or path.endswith(".jsx")
        or path.endswith(".ts")
        or path.endswith(".tsx")
        or path.endswith(".java")
        or os.path.basename(path) == "Dockerfile"
        or os.path.basename(path).startswith("Dockerfile.")
    ):
        return [path]
    elif os.path.isdir(path):
        return _scan_directory(path)
    return []


def _extract_imports_from_ast(tree: ast.AST) -> Set[str]:
    """
    Walks the AST tree to extract imported module names.

    Args:
        tree (ast.AST): The AST tree.

    Returns:
        Set[str]: Set of imported module names.
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

    Args:
        filepath (str): Path to the Python file.

    Returns:
        Set[str]: A set of unique module names imported in the file.
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
    Resolves the base directory and list of relative python files.
    """
    if os.path.isfile(root_path) and root_path.endswith(".py"):
        all_py_files = [os.path.basename(root_path)]
        root_path_dir = os.path.dirname(root_path)
        return root_path_dir, all_py_files
    else:
        full_paths = collect_python_files(root_path)
        all_py_files = [os.path.relpath(f, start=root_path) for f in full_paths]
        return root_path, all_py_files


def _is_match(candidate_no_ext: str, suffix: str) -> bool:
    """
    Checks if a candidate path matches an import suffix.
    """
    if candidate_no_ext.endswith(suffix):
        match_len = len(suffix)
        if (
            len(candidate_no_ext) == match_len
            or candidate_no_ext[-(match_len + 1)] == os.sep
        ):
            return True
    return False


def _find_imported_files(
    imported_name: str, rel_path: str, all_py_files: List[str]
) -> Set[str]:
    """
    Finds files that match the imported name.
    """
    matches = set()
    suffix = imported_name.replace(".", os.sep)
    for candidate in all_py_files:
        if candidate == rel_path:
            continue
        candidate_no_ext = os.path.splitext(candidate)[0]
        if _is_match(candidate_no_ext, suffix):
            matches.add(candidate)
    return matches


def get_import_graph(root_path: str) -> Dict[str, Set[str]]:
    """
    Builds a dependency graph of the project.

    Args:
        root_path (str): The root path to analyze.

    Returns:
        Dict[str, Set[str]]: A mapping of file relative paths to their dependencies.
    """
    base_dir, all_py_files = _resolve_initial_paths(root_path)
    graph: Dict[str, Set[str]] = {f: set() for f in all_py_files}

    for rel_path in all_py_files:
        full_path = os.path.join(base_dir, rel_path)
        imported_names = parse_imports(full_path)

        for name in imported_names:
            matches = _find_imported_files(name, rel_path, all_py_files)
            graph[rel_path].update(matches)

    return graph


def get_inbound_imports(graph: Dict[str, Set[str]]) -> Dict[str, int]:
    """
    Returns {file: count} of inbound imports to identify 'God Modules'.

    Args:
        graph (Dict[str, Set[str]]): The project's dependency graph.

    Returns:
        Dict[str, int]: A mapping of file paths to their inbound import counts.
    """
    inbound: Dict[str, int] = {node: 0 for node in graph}
    for source, targets in graph.items():
        for target in targets:
            if target in inbound:
                inbound[target] += 1
            else:
                inbound[target] = 1
    return inbound


def _dfs_visit_cycle(
    node: str,
    graph: Dict[str, Set[str]],
    visited_global: Set[str],
    path_set: Set[str],
    current_path: List[str],
    cycles: List[List[str]],
) -> None:
    """
    Helper function for DFS traversal to find cycles.
    """
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
            _dfs_visit_cycle(
                neighbor, graph, visited_global, path_set, current_path, cycles
            )

    path_set.remove(node)
    current_path.pop()


def _find_raw_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Finds all cycles in the graph using DFS.

    Args:
        graph (Dict[str, Set[str]]): The project's dependency graph.

    Returns:
        List[List[str]]: A list of raw cycles (paths).
    """
    cycles: List[List[str]] = []
    visited_global: Set[str] = set()
    path_set: Set[str] = set()
    nodes = sorted(graph.keys())

    for node in nodes:
        if node not in visited_global:
            _dfs_visit_cycle(node, graph, visited_global, path_set, [], cycles)

    return cycles


def _canonicalize_cycles(cycles: List[List[str]]) -> List[List[str]]:
    """
    Canonicalizes cycles to remove duplicates.

    Args:
        cycles (List[List[str]]): A list of raw cycles.

    Returns:
        List[List[str]]: A list of unique, canonicalized cycles.
    """
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


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Returns list of unique cycles using DFS and canonicalization.

    Args:
        graph (Dict[str, Set[str]]): The project's dependency graph.

    Returns:
        List[List[str]]: A list of unique circular dependency paths.
    """
    raw_cycles = _find_raw_cycles(graph)
    return _canonicalize_cycles(raw_cycles)


def _get_transitive_dependencies(
    start_node: str, graph: Dict[str, Set[str]]
) -> Set[str]:
    """
    Calculates transitive dependencies using BFS.

    Args:
        start_node (str): The starting node.
        graph (Dict[str, Set[str]]): The dependency graph.

    Returns:
        Set[str]: Set of all transitive dependencies (excluding start_node unless cyclic).
    """
    visited: Set[str] = set()
    queue: List[str] = [start_node]
    visited.add(start_node)

    idx = 0
    while idx < len(queue):
        current = queue[idx]
        idx += 1

        neighbors = graph.get(current, set())
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


def calculate_context_tokens(
    graph: Dict[str, Set[str]], file_tokens: Dict[str, int]
) -> Dict[str, int]:
    """
    Calculates the cumulative token count for each file by summing the tokens of the file
    and all its transitive dependencies.

    Args:
        graph (Dict[str, Set[str]]): The dependency graph (file -> set of dependencies).
        file_tokens (Dict[str, int]): Map of file paths to their token counts.

    Returns:
        Dict[str, int]: Map of file paths to their cumulative context token counts.
    """
    context_tokens: Dict[str, int] = {}

    for file in graph:
        visited = _get_transitive_dependencies(file, graph)
        total_tokens = sum(file_tokens.get(f, 0) for f in visited)
        context_tokens[file] = total_tokens

    return context_tokens
