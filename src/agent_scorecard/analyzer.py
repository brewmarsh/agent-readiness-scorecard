import os
import ast
import mccabe

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

def get_acl_score(loc, complexity):
    """Calculates Agent Cognitive Load (ACL).
    Formula: ACL = CC + (LLOC / 20)
    """
    return complexity + (loc / 20.0)

def calculate_acl(complexity, loc):
    """Calculates Agent Cognitive Load (ACL).
    Formula: ACL = CC + (LLOC / 20)
    DEPRECATED: Use get_acl_score instead for consistency with other metrics.
    """
    return get_acl_score(loc, complexity)

def get_directory_entropy(root_path, threshold=20):
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
                # We could handle relative imports here, but let's stick to simple module matching first

        # Try to match imported names to files
        for name in imported_names:
            # name e.g. "agent_scorecard.analyzer"
            # We look for files that "end with" this module path structure

            # Convert module dots to path separators
            suffix = name.replace(".", os.sep)

            for candidate in all_py_files:
                if candidate == rel_path: continue

                # Check if candidate ends with suffix + ".py"
                # But we need to be careful. "analyzer" shouldn't match "some_analyzer.py" unless it's an exact component match.
                # e.g. "os.path.join" -> "analyzer.py" matches "agent_scorecard/analyzer.py"

                # Let's strip extension
                candidate_no_ext = os.path.splitext(candidate)[0]
                # candidate_no_ext: src/agent_scorecard/analyzer

                # if candidate_no_ext ends with suffix, it's a potential match
                # e.g. "src/agent_scorecard/analyzer".endswith("agent_scorecard/analyzer") -> True

                # Check boundary: previous char must be sep or nothing
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
                # Might be a target not in our scanned list
                inbound[target] = 1
    return inbound

def detect_cycles(graph):
    """Returns list of cycles (list of nodes in cycle)."""
    cycles = []
    visited_global = set()
    path_set = set()

    # Sort nodes to make cycle detection deterministic
    nodes = sorted(graph.keys())

    def visit(node, current_path):
        visited_global.add(node)
        path_set.add(node)
        current_path.append(node)

        # Sort neighbors for determinism
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
