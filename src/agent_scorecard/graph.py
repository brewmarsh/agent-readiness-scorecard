import ast
import os
from typing import Dict, List, Set, Any
import networkx as nx

def get_imports(filepath: str) -> List[Dict[str, Any]]:
    """Extracts all imports from a python file using AST."""
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append({"module": n.name, "level": 0})
        elif isinstance(node, ast.ImportFrom):
            imports.append({"module": node.module, "level": node.level})
    return imports

def resolve_module_path(base_path: str, current_file: str, module_name: str, level: int, py_files: Set[str]) -> str | None:
    """Resolves a module import to an absolute file path if it exists in py_files."""
    if level > 0:
        # Relative import
        parts = os.path.dirname(current_file).split(os.sep)
        # level 1 = current dir, level 2 = parent, etc.
        if level > len(parts):
            return None

        target_dir = os.sep.join(parts[:len(parts) - (level - 1)])

        if module_name:
            module_parts = module_name.split('.')
            target_path = os.path.join(target_dir, *module_parts)
        else:
            target_path = target_dir

    else:
        # Absolute import - this is harder.
        # We try to match it against our known py_files by checking suffixes.
        if not module_name:
            return None

        module_path_part = module_name.replace('.', os.sep)

        # Check if any of our py_files ends with this module path
        # This is a heuristic.
        for py_file in py_files:
            if py_file.endswith(module_path_part + ".py") or py_file.endswith(os.path.join(module_path_part, "__init__.py")):
                return py_file
        return None

    # Check for .py or /__init__.py
    if os.path.isfile(target_path + ".py"):
        return os.path.abspath(target_path + ".py")
    if os.path.isdir(target_path) and os.path.isfile(os.path.join(target_path, "__init__.py")):
        return os.path.abspath(os.path.join(target_path, "__init__.py"))

    return None

def build_dependency_graph(root_path: str) -> nx.DiGraph:
    """Builds a Directed Graph of dependencies between Python files."""
    graph = nx.DiGraph()
    py_files = set()

    abs_root = os.path.abspath(root_path)

    if os.path.isfile(abs_root):
        if abs_root.endswith(".py"):
            py_files.add(abs_root)
    else:
        for root, _, files in os.walk(abs_root):
            for file in files:
                if file.endswith(".py"):
                    py_files.add(os.path.abspath(os.path.join(root, file)))

    for filepath in py_files:
        graph.add_node(filepath)
        imports = get_imports(filepath)
        for imp in imports:
            resolved = resolve_module_path(abs_root, filepath, imp["module"], imp["level"], py_files)
            if resolved and resolved in py_files and resolved != filepath:
                graph.add_edge(filepath, resolved)

    return graph

def analyze_graph(graph: nx.DiGraph) -> Dict[str, Any]:
    """Analyzes the dependency graph for cycles and God Modules."""
    cycles = list(nx.simple_cycles(graph))

    god_modules = []
    for node, in_degree in graph.in_degree():
        if in_degree > 50:
            god_modules.append({
                "file": node,
                "in_degree": in_degree
            })

    return {
        "cycles": cycles,
        "god_modules": god_modules
    }
