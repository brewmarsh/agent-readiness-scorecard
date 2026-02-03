import os
import ast
import mccabe
from typing import List, Dict, Any

def get_loc(filepath: str) -> int:
    """Returns lines of code excluding whitespace/comments roughly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except UnicodeDecodeError:
        return 0

def analyze_functions(filepath: str) -> List[Dict[str, Any]]:
    """Returns a list of metrics for each function in the file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return []

    # Get complexities by visiting the whole tree
    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)
    complexity_map = {g.lineno: g.complexity() for g in visitor.graphs.values()}

    results = []
    lines = code.splitlines()

    for func in functions:
        # LOC
        start = func.lineno
        end = getattr(func, "end_lineno", start)
        func_lines = lines[start-1:end]
        func_loc = sum(1 for line in func_lines if line.strip() and not line.strip().startswith("#"))

        # Complexity
        complexity = complexity_map.get(func.lineno, 1)

        # ACL = Cyclomatic_Complexity + (Lines_of_Code / 20)
        acl = complexity + (func_loc / 20.0)

        # Type hints: explicit type signature check
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        is_typed = has_return or has_args

        results.append({
            "name": func.name,
            "lineno": func.lineno,
            "complexity": complexity,
            "loc": func_loc,
            "acl": acl,
            "is_typed": is_typed
        })

    return results

def analyze_complexity(filepath: str) -> float:
    """Returns average complexity."""
    functions = analyze_functions(filepath)
    if not functions:
        return 0.0
    return sum(f["complexity"] for f in functions) / len(functions)

def analyze_type_hints(filepath: str) -> float:
    """Returns type hint coverage percentage."""
    functions = analyze_functions(filepath)
    if not functions:
        return 100.0
    typed_count = sum(1 for f in functions if f["is_typed"])
    return (typed_count / len(functions)) * 100

def scan_project_docs(root_path: str, required_files: List[str]) -> List[str]:
    """Checks for existence of agent-critical markdown files."""
    missing = []
    # Normalize checking logic to look in the root of the provided path
    root_files = [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing

# Aliases for backward compatibility
get_complexity_score = analyze_complexity
check_type_hints = analyze_type_hints
