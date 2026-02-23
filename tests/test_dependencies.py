from src.agent_scorecard.dependencies import (
    get_import_graph,
    detect_cycles,
    calculate_context_tokens,
    _collect_python_files,
)

def test_collect_python_files(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "file1.py").write_text("print('hello')")
    (d / "file2.txt").write_text("not python")
    (tmp_path / "root.py").write_text("print('root')")

    files = _collect_python_files(str(tmp_path))
    assert len(files) == 2
    assert any(f.endswith("file1.py") for f in files)
    assert any(f.endswith("root.py") for f in files)

def test_import_graph_and_cycles(tmp_path):
    # A -> B -> C -> A (cycle)
    # D -> B

    (tmp_path / "a.py").write_text("import b")
    (tmp_path / "b.py").write_text("import c")
    (tmp_path / "c.py").write_text("import a")
    (tmp_path / "d.py").write_text("import b")

    graph = get_import_graph(str(tmp_path))

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

def test_calculate_context_tokens(tmp_path):
    # A -> B
    # B has 10 tokens
    # A has 20 tokens
    # Context(B) = 10
    # Context(A) = 20 + 10 = 30

    graph = {
        "a.py": {"b.py"},
        "b.py": set()
    }

    file_tokens = {
        "a.py": 20,
        "b.py": 10
    }

    context = calculate_context_tokens(graph, file_tokens)

    assert context["b.py"] == 10
    assert context["a.py"] == 30

def test_calculate_context_tokens_with_cycle(tmp_path):
    # A -> B -> A
    # A: 10, B: 20
    # Context(A) = 10 + 20 = 30
    # Context(B) = 20 + 10 = 30

    graph = {
        "a.py": {"b.py"},
        "b.py": {"a.py"}
    }

    file_tokens = {
        "a.py": 10,
        "b.py": 20
    }

    context = calculate_context_tokens(graph, file_tokens)

    assert context["a.py"] == 30
    assert context["b.py"] == 30

def test_calculate_context_tokens_complex(tmp_path):
    # A -> B, C
    # B -> D
    # C -> D
    # D -> E
    # E -> D (cycle)

    # Tokens: All 10

    graph = {
        "a.py": {"b.py", "c.py"},
        "b.py": {"d.py"},
        "c.py": {"d.py"},
        "d.py": {"e.py"},
        "e.py": {"d.py"}
    }

    file_tokens = {f: 10 for f in graph}

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
