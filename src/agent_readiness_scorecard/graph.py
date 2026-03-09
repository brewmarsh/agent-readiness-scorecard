import ast
import os
from typing import Dict, List, Set, Any
import networkx as nx


def _process_import(node: ast.Import, imports: List[Dict[str, Any]]) -> None:
    """Helper to process ast.Import nodes."""
    for n in node.names:
        imports.append({"module": n.name, "level": 0})


def _handle_import_node(node: ast.AST, imports: List[Dict[str, Any]]) -> None:
    """Helper to process ast.Import and ast.ImportFrom nodes."""
    if isinstance(node, ast.Import):
        _process_import(node, imports)
    elif isinstance(node, ast.ImportFrom):
        imports.append({"module": node.module, "level": node.level})


def _extract_imports_from_ast(tree: ast.AST) -> List[Dict[str, Any]]:
    """Walks the AST tree to extract imports."""
    imports: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        _handle_import_node(node, imports)
    return imports


def get_imports(filepath: str) -> List[Dict[str, Any]]:
    """
    Extracts all imports from a python file using AST.

    Args:
        filepath (str): Path to the Python file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'module' and 'level' for each import.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        return _extract_imports_from_ast(tree)
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
        return []


def _resolve_relative_import(
    current_file: str, module_name: str, level: int
) -> str | None:
    """Resolves target directory for relative imports."""
    parts = os.path.dirname(current_file).split(os.sep)
    if level > len(parts):
        return None

    target_dir = os.sep.join(parts[: len(parts) - (level - 1)])
    if not module_name:
        return target_dir

    return os.path.join(target_dir, *module_name.split("."))


def _is_matching_py_file(py_file: str, module_path_part: str) -> bool:
    """Checks if a py_file matches the module path."""
    is_module = py_file.endswith(module_path_part + ".py")
    is_pkg = py_file.endswith(os.path.join(module_path_part, "__init__.py"))
    return is_module or is_pkg


def _find_py_file(module_path_part: str, py_files: Set[str]) -> str | None:
    """Finds a py_file matching the module path part."""
    for py_file in py_files:
        if _is_matching_py_file(py_file, module_path_part):
            return py_file
    return None


def _resolve_absolute_import(module_name: str, py_files: Set[str]) -> str | None:
    """Resolves absolute imports by heuristic matching against py_files."""
    if not module_name:
        return None

    module_path_part = module_name.replace(".", os.sep)
    return _find_py_file(module_path_part, py_files)


def _check_path_existence(target_path: str) -> str | None:
    """Checks if target_path corresponds to a .py file or a package."""
    py_file = target_path + ".py"
    init_file = os.path.join(target_path, "__init__.py")

    if os.path.isfile(py_file):
        return os.path.abspath(py_file)
    if os.path.isdir(target_path) and os.path.isfile(init_file):
        return os.path.abspath(init_file)
    return None


def resolve_module_path(
    base_path: str, current_file: str, module_name: str, level: int, py_files: Set[str]
) -> str | None:
    """
    Resolves a module import to an absolute file path if it exists in py_files.

    Args:
        base_path (str): The project base path.
        current_file (str): Path to the file containing the import.
        module_name (str): The name of the module being imported.
        level (int): The import level (0 for absolute, >0 for relative).
        py_files (Set[str]): Set of all Python files in the project.

    Returns:
        str | None: The resolved absolute path to the module, or None if not found.
    """
    if level > 0:
        target_path = _resolve_relative_import(current_file, module_name, level)
        return _check_path_existence(target_path) if target_path else None

    return _resolve_absolute_import(module_name, py_files)


def _collect_py_file(root: str, file: str, py_files: Set[str]) -> None:
    """Adds absolute path of .py file to py_files."""
    if file.endswith(".py"):
        py_files.add(os.path.abspath(os.path.join(root, file)))


def _walk_and_collect_py_files(abs_root: str, py_files: Set[str]) -> None:
    """Helper to walk directory and collect .py files."""
    for root, _, files in os.walk(abs_root):
        for file in files:
            _collect_py_file(root, file, py_files)


def _collect_all_py_files(abs_root: str) -> Set[str]:
    """Recursively finds all Python files in a directory."""
    py_files = set()
    if os.path.isfile(abs_root) and abs_root.endswith(".py"):
        py_files.add(abs_root)
        return py_files

    _walk_and_collect_py_files(abs_root, py_files)
    return py_files


def _add_file_dependencies_to_graph(
    graph: nx.DiGraph, filepath: str, abs_root: str, py_files: Set[str]
) -> None:
    """Extracts imports from a file and adds edges to the graph."""
    graph.add_node(filepath)
    imports = get_imports(filepath)
    for imp in imports:
        resolved = resolve_module_path(
            abs_root, filepath, imp["module"], imp["level"], py_files
        )
        if resolved and resolved in py_files and resolved != filepath:
            graph.add_edge(filepath, resolved)


def build_dependency_graph(root_path: str) -> nx.DiGraph:
    """
    Builds a Directed Graph of dependencies between Python files.

    Args:
        root_path (str): The project root path to analyze.

    Returns:
        nx.DiGraph: A NetworkX directed graph where nodes are file paths and edges are dependencies.
    """
    graph: nx.DiGraph = nx.DiGraph()
    abs_root = os.path.abspath(root_path)
    py_files = _collect_all_py_files(abs_root)

    for filepath in py_files:
        _add_file_dependencies_to_graph(graph, filepath, abs_root, py_files)

    return graph


def analyze_graph(graph: nx.DiGraph) -> Dict[str, Any]:
    """
    Analyzes the dependency graph for cycles and God Modules.

    Args:
        graph (nx.DiGraph): The project dependency graph.

    Returns:
        Dict[str, Any]: A dictionary containing 'cycles' and 'god_modules' analysis.
    """
    cycles = list(nx.simple_cycles(graph))

    god_modules = []
    for node, in_degree in graph.in_degree():
        if in_degree > 50:
            god_modules.append({"file": node, "in_degree": in_degree})

    return {"cycles": cycles, "god_modules": god_modules}
