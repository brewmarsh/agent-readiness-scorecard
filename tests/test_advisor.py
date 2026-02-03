import pytest
from pathlib import Path
import textwrap
import os
from src.agent_scorecard.analyzer import calculate_acl, get_directory_entropy, get_import_graph, get_inbound_imports, detect_cycles
from src.agent_scorecard.report import generate_advisor_report

def test_calculate_acl():
    # ACL = CC + (LOC / 20)
    assert calculate_acl(10, 100) == 10 + (100 / 20) # 15.0
    assert calculate_acl(0, 0) == 0

def test_get_directory_entropy(tmp_path):
    # Create 25 files in tmp_path
    for i in range(25):
        (tmp_path / f"file_{i}.txt").touch()

    # Create subfolder with 5 files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    for i in range(5):
        (subdir / f"sub_{i}.txt").touch()

    entropy = get_directory_entropy(str(tmp_path), threshold=20)

    # Check if root is flagged (rel path is usually base dir name or ".")
    # The function returns basename of root if rel_path is "."
    base_name = tmp_path.name

    # Depending on implementation, it might return '.' or basename.
    # My implementation: if rel_path == ".": rel_path = basename

    assert base_name in entropy
    assert entropy[base_name] == 25 # only files in root
    assert "subdir" not in entropy

def test_dependency_analysis(tmp_path):
    # Create files
    # main.py imports utils
    # utils.py imports shared
    # shared.py

    (tmp_path / "main.py").write_text("import utils", encoding="utf-8")
    (tmp_path / "utils.py").write_text("import shared", encoding="utf-8")
    (tmp_path / "shared.py").write_text("# no imports", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))

    assert "main.py" in graph
    assert "utils.py" in graph["main.py"]
    assert "utils.py" in graph
    assert "shared.py" in graph["utils.py"]

    inbound = get_inbound_imports(graph)
    assert inbound.get("utils.py") == 1
    assert inbound.get("shared.py") == 1
    assert inbound.get("main.py") == 0

def test_cycle_detection(tmp_path):
    # a.py imports b
    # b.py imports a

    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))
    cycles = detect_cycles(graph)

    assert len(cycles) > 0
    # Cycle should involve a.py and b.py
    flat_cycle = [item for sublist in cycles for item in sublist]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle

def test_generate_advisor_report():
    stats = [
        {"file": "high_acl.py", "acl": 20.0, "complexity": 10, "loc": 200},
        {"file": "normal.py", "acl": 5.0, "complexity": 2, "loc": 60}
    ]
    dependency_stats = {"god.py": 55, "util.py": 5}
    entropy_stats = {"large_dir": 30}
    cycles = [["a.py", "b.py"]]

    report = generate_advisor_report(stats, dependency_stats, entropy_stats, cycles)

    assert "# 🧠 Agent Advisor Report" in report
    assert "high_acl.py" in report
    assert "Hallucination Zones" in report
    assert "god.py" in report
    assert "God Modules" in report
    assert "a.py" in report
    assert "Circular Dependencies" in report
    assert "large_dir" in report
    assert "Directory Entropy" in report
