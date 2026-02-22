import textwrap
from pathlib import Path
from agent_scorecard import analyzer, report
from agent_scorecard.constants import PROFILES
from agent_scorecard.analyzer import (
    calculate_acl,
    get_import_graph,
    get_inbound_imports,
    detect_cycles,
)
from agent_scorecard.auditor import get_crowded_directories
from agent_scorecard.report import generate_advisor_report

# --- Core Metric Tests ---

def test_calculate_acl() -> None:
    """
    Tests the Agent Cognitive Load (ACL) calculation formula.
    Formula: ACL = Cyclomatic Complexity + (Lines of Code / 20)

    Returns:
        None
    """
    assert calculate_acl(10, 100) == 10 + (100 / 20)  # 15.0
    assert calculate_acl(0, 0) == 0


def test_get_directory_entropy(tmp_path: Path) -> None:
    """
    Tests the directory entropy calculation by simulating high file counts.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Create 25 files in tmp_path to trigger the threshold
    for i in range(25):
        (tmp_path / f"file_{i}.txt").touch()

    # Create subfolder with 5 files (should stay under threshold)
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    for i in range(5):
        (subdir / f"sub_{i}.txt").touch()

    # Use Beta threshold of 20 to verify the "crowded" flag logic
    entropy = get_crowded_directories(str(tmp_path), threshold=20)
    base_name = tmp_path.name

    assert base_name in entropy
    assert entropy[base_name] == 25  # Only files in root counted for this node
    assert "subdir" not in entropy


def test_dependency_analysis(tmp_path: Path) -> None:
    """
    Tests the project dependency analysis and inbound import counting.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Simulation: main -> utils -> shared
    (tmp_path / "main.py").write_text("import utils", encoding="utf-8")
    (tmp_path / "utils.py").write_text("import shared", encoding="utf-8")
    (tmp_path / "shared.py").write_text("# no imports", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))

    assert "main.py" in graph
    assert "utils.py" in graph["main.py"]
    assert "shared.py" in graph["utils.py"]

    inbound = get_inbound_imports(graph)
    assert inbound.get("utils.py") == 1
    assert inbound.get("shared.py") == 1
    assert inbound.get("main.py") == 0


def test_cycle_detection(tmp_path: Path) -> None:
    """
    Tests circular dependency detection between project modules.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Simulation: a <-> b (Circular dependency)
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))
    cycles = detect_cycles(graph)

    assert len(cycles) > 0
    flat_cycle = [item for sublist in cycles for item in sublist]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle


def test_generate_advisor_report_standalone() -> None:
    """
    Tests the standalone Advisor Report used in the 'agent-score advise' command.

    Returns:
        None
    """
    stats = [
        {"file": "high_acl.py", "acl": 20.0, "complexity": 10, "loc": 200},
        {"file": "normal.py", "acl": 5.0, "complexity": 2, "loc": 60},
    ]
    dependency_stats = {"god.py": 55, "util.py": 5}
    entropy_stats = {"large_dir": 30}
    cycles = [["a.py", "b.py"]]

    report_md = generate_advisor_report(stats, dependency_stats, entropy_stats, cycles)

    assert "# 🧠 Agent Advisor Report" in report_md
    assert "high_acl.py" in report_md
    assert "Hallucination Zones" in report_md
    assert "god.py" in report_md
    assert "God Modules" in report_md
    assert "Circular Dependencies" in report_md
    assert "Directory Entropy" in report_md


# --- Integration Tests ---

def test_function_stats_parsing(tmp_path: Path) -> None:
    """
    Tests that we can parse a file and extract function metrics correctly.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    code = textwrap.dedent("""
        def complex_function():
            if True:
                print("yes")
            else:
                print("no")
    """)
    # Pad with comments to trigger the LOC density metric
    for _ in range(20):
        code += "    # padding\n"
    code += "    return 0\n"

    p = tmp_path / "test_acl.py"
    p.write_text(code, encoding="utf-8")

    stats = analyzer.get_function_stats(str(p))
    assert len(stats) == 1
    func = stats[0]
    assert func["name"] == "complex_function"
    assert func["complexity"] >= 2
    assert func["loc"] >= 20
    assert func["acl"] > 2


def test_unified_score_report_content(tmp_path: Path) -> None:
    """
    Tests the detailed Markdown report generated during the 'score' command.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Setup a file that specifically triggers high ACL warnings
    code = "def hallucinate():\n"
    for _ in range(10):
        code += "    if True: pass\n"
    for i in range(120):
        code += f"    x={i}\n"

    (tmp_path / "hallucination.py").write_text(code, encoding="utf-8")

    func_stats = analyzer.get_function_stats(str(tmp_path / "hallucination.py"))
    acl_violations = [f for f in func_stats if f["acl"] > 15]

    stats = [
        {
            "file": "hallucination.py",
            "score": 50,
            "issues": "Yellow ACL functions (-5)",
            "loc": 130,
            "complexity": 11,
            "type_coverage": 0,
            "acl_violations": acl_violations,
        }
    ]

    report_md = report.generate_markdown_report(
        stats, 50, str(tmp_path), PROFILES["generic"]
    )

    assert "Agent Scorecard Report" in report_md
    assert "hallucination.py" in report_md
    assert "Agent Cognitive Load (ACL)" in report_md