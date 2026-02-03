#agent_scorecard/analyzer.py
import pytest
import textwrap
import os
from pathlib import Path

# Imports from both branches
from src.agent_scorecard import analyzer, report
from src.agent_scorecard.constants import PROFILES
from src.agent_scorecard.analyzer import (
    calculate_acl, 
    get_directory_entropy, 
    get_import_graph, 
    get_inbound_imports, 
    detect_cycles
)
from src.agent_scorecard.report import generate_advisor_report

# ==========================================
# BETA BRANCH TESTS (Unit Tests)
# ==========================================

def test_calculate_acl():
    """Unit test for the ACL math."""
    # ACL = CC + (LOC / 20)
    assert calculate_acl(10, 100) == 10 + (100 / 20) # 15.0
    assert calculate_acl(0, 0) == 0

def test_get_directory_entropy(tmp_path):
    """Unit test for directory entropy threshold."""
    # Create 25 files in tmp_path
    for i in range(25):
        (tmp_path / f"file_{i}.txt").touch()

    # Create subfolder with 5 files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    for i in range(5):
        (subdir / f"sub_{i}.txt").touch()

    # Use Beta threshold
    entropy = get_directory_entropy(str(tmp_path), threshold=20)
    base_name = tmp_path.name

    assert base_name in entropy
    assert entropy[base_name] == 25 # only files in root
    assert "subdir" not in entropy

def test_dependency_analysis(tmp_path):
    """Unit test for graph building."""
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
    """Unit test for cycle detection logic."""
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))
    cycles = detect_cycles(graph)

    assert len(cycles) > 0
    flat_cycle = [item for sublist in cycles for item in sublist]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle

def test_generate_advisor_report_standalone():
    """Unit test for the qualitative report generator."""
    stats = [
        {"file": "high_acl.py", "acl": 20.0, "complexity": 10, "loc": 200},
        {"file": "normal.py", "acl": 5.0, "complexity": 2, "loc": 60}
    ]
    dependency_stats = {"god.py": 55, "util.py": 5}
    entropy_stats = {"large_dir": 30}
    cycles = [["a.py", "b.py"]]

    report_md = generate_advisor_report(stats, dependency_stats, entropy_stats, cycles)

    assert "# 🧠 Agent Advisor Report" in report_md
    assert "high_acl.py" in report_md
    assert "Hallucination Zones" in report_md
    assert "god.py" in report_md
    assert "Circular Dependencies" in report_md

# ==========================================
# ADVISOR MODE TESTS (Integration Tests)
# ==========================================

def test_acl_file_integration(tmp_path):
    """Integration test: parsing a file to get ACL stats."""
    code = textwrap.dedent("""
        def complex_function():
            if True:
                print("yes")
            else:
                print("no")
            # padding lines to ensure LOC > 20
            return 0
    """)
    code += "\n" * 20

    p = tmp_path / "test_acl.py"
    p.write_text(code, encoding="utf-8")

    stats = analyzer.get_function_stats(str(p))
    assert len(stats) == 1
    func = stats[0]
    assert func["name"] == "complex_function"
    assert func["complexity"] >= 2
    assert func["loc"] >= 20
    assert func["acl"] > 2

def test_circular_dependency_integration(tmp_path):
    """Integration test: detecting cycles via analyze_project."""
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import c", encoding="utf-8")
    (tmp_path / "c.py").write_text("import a", encoding="utf-8")

    # Use the monolithic analyzer function
    stats = analyzer.analyze_project(str(tmp_path))
    deps = stats["dependencies"]
    cycles = deps["cycles"]

    assert len(cycles) > 0

    found = False
    for cycle in cycles:
        if set(cycle) == {"a.py", "b.py", "c.py"}:
            found = True
            break
    assert found

def test_advisor_full_flow(tmp_path):
    """Integration test: Full flow from file creation to report."""
    # Setup a project that triggers advisor warnings
    code = "def hallucinate():\n"
    for _ in range(10):
        code += "    if True: pass\n"
    for i in range(120):
        code += f"    x={i}\n"

    (tmp_path / "hallucination.py").write_text(code, encoding="utf-8")

    stats = analyzer.analyze_project(str(tmp_path))
    
    # We test the score-based report generation here
    report_md = report.generate_markdown_report(stats, 50, str(tmp_path), PROFILES["generic"])

    assert "Agent Scorecard Report" in report_md
    # Check if our new sections appear
    assert "hallucinate" in report_md