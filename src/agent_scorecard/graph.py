import ast
import os

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
            suffix = name.replace(".", os.sep)
            for candidate in all_py_files:
                if candidate == rel_path: continue
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
    """Returns list of cycles."""
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
