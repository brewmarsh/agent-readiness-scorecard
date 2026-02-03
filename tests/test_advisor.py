import pytest
from pathlib import Path
import textwrap
import os
from src.agent_scorecard.checks import calculate_acl
from src.agent_scorecard.auditor import check_directory_entropy
from src.agent_scorecard.graph import get_import_graph, get_inbound_imports, detect_cycles
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

    # check_directory_entropy returns {avg_files, warning}
    entropy = check_directory_entropy(str(tmp_path))

    # 30 files, 2 folders (root + subdir) -> 15 avg
    assert entropy["avg_files"] == 15.0

def test_dependency_analysis(tmp_path):
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
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))
    cycles = detect_cycles(graph)

    assert len(cycles) > 0
    flat_cycle = [item for sublist in cycles for item in sublist]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle

def test_generate_advisor_report():
    results = {
        "file_results": [
            {"file": "high_acl.py", "acl": 20.0, "complexity": 10, "loc": 200},
            {"file": "normal.py", "acl": 5.0, "complexity": 2, "loc": 60}
        ],
        "inbound": {"god.py": 55, "util.py": 5},
        "entropy": {"avg_files": 30.0, "warning": True},
        "tokens": {"token_count": 1000, "alert": False},
        "cycles": [["a.py", "b.py"]]
    }

    report = generate_advisor_report(results)

    assert "# 🧠 Agent Advisor Report" in report
    assert "high_acl.py" in report
    assert "Hallucination Zones" in report
    assert "god.py" in report
    assert "God Modules" in report
    assert "a.py" in report
    assert "Circular Dependencies" in report
    assert "Directory Entropy" in report
