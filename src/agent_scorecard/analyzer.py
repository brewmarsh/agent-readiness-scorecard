import os
import ast
import mccabe
from collections import Counter

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
            acl = complexity + (loc / 20.0)

            stats.append({
                "name": node.name,
                "lineno": start_line,
                "complexity": complexity,
                "loc": loc,
                "acl": acl
            })
    return stats

def count_directory_files(directory):
    """Returns the number of files in the directory."""
    try:
        return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
    except FileNotFoundError:
        return 0

def analyze_imports(file_list):
    """
    Analyzes imports across the given files to detect potential 'God Modules'.
    Only considers internal modules (heuristically matched against file names).
    Returns a Counter mapping imported module names to import counts.
    """
    import_counts = Counter()

    # Heuristic: Internal modules match filenames (without extension)
    internal_modules = {os.path.splitext(os.path.basename(f))[0] for f in file_list}

    for filepath in file_list:
        try:
            code = open(filepath, "r", encoding="utf-8").read()
            tree = ast.parse(code, filepath)
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_mod = alias.name.split('.')[0]
                    if base_mod in internal_modules:
                        import_counts[base_mod] += 1
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_mod = node.module.split('.')[0]
                    if base_mod in internal_modules:
                        import_counts[base_mod] += 1

    return import_counts

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

    # 2. God Modules
    import_counts = analyze_imports(py_files)
    god_modules = [mod for mod, count in import_counts.items() if count > 50]
    if god_modules:
        msg = f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}"
        penalty += len(god_modules) * 10
        issues.append(msg)

    # 3. Directory Entropy
    if os.path.isdir(path):
        dirs = set(os.path.dirname(f) for f in py_files)
        crowded_dirs = []
        for d in dirs:
            if count_directory_files(d) > 50:
                 crowded_dirs.append(os.path.relpath(d, start=path) if d != path else ".")

        if crowded_dirs:
            msg = f"High Directory Entropy (>50 files): {', '.join(crowded_dirs)}"
            penalty += len(crowded_dirs) * 5
            issues.append(msg)

    return penalty, issues
