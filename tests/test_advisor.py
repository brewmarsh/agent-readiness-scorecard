import textwrap
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

# --- Beta Branch Tests (Unit Tests for Metrics) ---


# TODO: Add type hints for Agent clarity
def test_calculate_acl():
    # ACL = CC + (LOC / 20)
    """TODO: Add docstring for AI context."""
    assert calculate_acl(10, 100) == 10 + (100 / 20)  # 15.0
    assert calculate_acl(0, 0) == 0


# TODO: Add type hints for Agent clarity
def test_get_directory_entropy(tmp_path):
    # Create 25 files in tmp_path
    """TODO: Add docstring for AI context."""
    for i in range(25):
        (tmp_path / f"file_{i}.txt").touch()

    # Create subfolder with 5 files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    for i in range(5):
        (subdir / f"sub_{i}.txt").touch()

    # Use Beta threshold (matches resolved code)
    entropy = get_crowded_directories(str(tmp_path), threshold=20)
    base_name = tmp_path.name

    assert base_name in entropy
    assert entropy[base_name] == 25  # only files in root
    assert "subdir" not in entropy


# TODO: Add type hints for Agent clarity
def test_dependency_analysis(tmp_path):
    # main.py imports utils, utils imports shared
    """TODO: Add docstring for AI context."""
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


# TODO: Add type hints for Agent clarity
def test_cycle_detection(tmp_path):
    # a.py <-> b.py
    """TODO: Add docstring for AI context."""
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")

    graph = get_import_graph(str(tmp_path))
    cycles = detect_cycles(graph)

    assert len(cycles) > 0
    flat_cycle = [item for sublist in cycles for item in sublist]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle


# TODO: Add type hints for Agent clarity
def test_generate_advisor_report_standalone():
    """Tests the standalone Advisor Report used in 'agent-score advise' command."""
    stats = [
        {"file": "high_acl.py", "acl": 20.0, "complexity": 10, "loc": 200},
        {"file": "normal.py", "acl": 5.0, "complexity": 2, "loc": 60},
    ]
    dependency_stats = {"god.py": 55, "util.py": 5}
    entropy_stats = {"large_dir": 30}
    cycles = [["a.py", "b.py"]]

    # Test the standalone advisor function
    report_md = generate_advisor_report(stats, dependency_stats, entropy_stats, cycles)

    assert "# 🧠 Agent Advisor Report" in report_md
    assert "high_acl.py" in report_md
    assert "Hallucination Zones" in report_md
    assert "god.py" in report_md
    assert "God Modules" in report_md
    assert "a.py" in report_md
    assert "Circular Dependencies" in report_md
    assert "large_dir" in report_md
    assert "Directory Entropy" in report_md


# --- Advisor Mode Tests (Integration Tests) ---


# TODO: Add type hints for Agent clarity
def test_function_stats_parsing(tmp_path):
    """Tests that we can parse a file and extract function stats correctly."""
    code = textwrap.dedent("""
        def complex_function():
            if True:
                print("yes")
            else:
                print("no")
    """)
    # Pad to ensure LOC > 20
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


# TODO: Add type hints for Agent clarity
def test_unified_score_report_content(tmp_path):
    """Tests the Markdown report generated during the 'score' command."""
    # Setup a project that triggers advisor warnings
    code = "def hallucinate():\n"
    for _ in range(10):
        code += "    if True: pass\n"
    for i in range(120):
        code += f"    x={i}\n"

    (tmp_path / "hallucination.py").write_text(code, encoding="utf-8")

    # Run analysis to get stats
    # Note: We need stats in the format generate_markdown_report expects (list of file dicts for score mode)
    # But wait, generate_markdown_report handles both. Let's pass the list format used by 'score'.

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

    # Check for sections
    assert "Agent Scorecard Report" in report_md
    assert "hallucination.py" in report_md
    # Check if ACL section appeared
    assert "Agent Cognitive Load (ACL)" in report_md
