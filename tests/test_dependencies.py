from pathlib import Path
from typing import Dict, Set
from agent_readiness_scorecard.dependencies import (
    get_import_graph,
    detect_cycles,
    calculate_context_tokens,
    collect_python_files,
)


def test_collect_python_files(tmp_path: Path) -> None:
    """
    Tests the collection of Python files in a directory.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "file1.py").write_text("print('hello')")
    (d / "file2.txt").write_text("not python")
    (tmp_path / "root.py").write_text("print('root')")

    files = collect_python_files(str(tmp_path))
    assert len(files) == 2
    assert any(f.endswith("file1.py") for f in files)
    assert any(f.endswith("root.py") for f in files)


def test_collect_files_pruning(tmp_path: Path) -> None:
    """
    Tests that node_modules, .venv, etc. are pruned.
    """
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.py").write_text("print('no')")

    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "bad2.py").write_text("print('no')")

    (tmp_path / "good.py").write_text("print('yes')")

    files = collect_python_files(str(tmp_path))
    assert len(files) == 1
    assert files[0].endswith("good.py")


def test_import_graph_and_cycles(tmp_path: Path) -> None:
    """
    Tests import graph generation and cycle detection.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # A -> B -> C -> A (cycle)
    # D -> B

    (tmp_path / "a.py").write_text("import b")
    (tmp_path / "b.py").write_text("import c")
    (tmp_path / "c.py").write_text("import a")
    (tmp_path / "d.py").write_text("import b")

    graph: Dict[str, Set[str]] = get_import_graph(str(tmp_path))

    assert "a.py" in graph
    assert "b.py" in graph["a.py"]
    assert "c.py" in graph["b.py"]
    assert "a.py" in graph["c.py"]
    assert "b.py" in graph["d.py"]

    cycles = detect_cycles(graph)
    assert len(cycles) == 1
    cycle = cycles[0]
    # Canonical cycle should start with min element
    assert cycle == ["a.py", "b.py", "c.py"]


def test_calculate_context_tokens(tmp_path: Path) -> None:
    """
    Tests context token calculation for simple dependencies.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # A -> B
    # B has 10 tokens
    # A has 20 tokens
    # Context(B) = 10
    # Context(A) = 20 + 10 = 30

    graph: Dict[str, Set[str]] = {"a.py": {"b.py"}, "b.py": set()}

    file_tokens: Dict[str, int] = {"a.py": 20, "b.py": 10}

    context = calculate_context_tokens(graph, file_tokens)

    assert context["b.py"] == 10
    assert context["a.py"] == 30


def test_calculate_context_tokens_with_cycle(tmp_path: Path) -> None:
    """
    Tests context token calculation with dependency cycles.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # A -> B -> A
    # A: 10, B: 20
    # Context(A) = 10 + 20 = 30
    # Context(B) = 20 + 10 = 30

    graph: Dict[str, Set[str]] = {"a.py": {"b.py"}, "b.py": {"a.py"}}

    file_tokens: Dict[str, int] = {"a.py": 10, "b.py": 20}

    context = calculate_context_tokens(graph, file_tokens)

    assert context["a.py"] == 30
    assert context["b.py"] == 30


def test_calculate_context_tokens_complex(tmp_path: Path) -> None:
    """
    Tests context token calculation with complex dependencies.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # A -> B, C
    # B -> D
    # C -> D
    # D -> E
    # E -> D (cycle)

    # Tokens: All 10

    graph: Dict[str, Set[str]] = {
        "a.py": {"b.py", "c.py"},
        "b.py": {"d.py"},
        "c.py": {"d.py"},
        "d.py": {"e.py"},
        "e.py": {"d.py"},
    }

    file_tokens: Dict[str, int] = {f: 10 for f in graph}

    context = calculate_context_tokens(graph, file_tokens)

    # E -> D -> E. Deps: D, E. Total 20.
    assert context["e.py"] == 20
    assert context["d.py"] == 20

    # B -> D -> E -> D. Deps: B, D, E. Total 30.
    assert context["b.py"] == 30

    # C -> D -> E -> D. Deps: C, D, E. Total 30.
    assert context["c.py"] == 30

    # A -> B, C. And B->D,E. C->D,E.
    # Transitive deps of A: B, C, D, E.
    # Total: A, B, C, D, E = 50.
    assert context["a.py"] == 50
