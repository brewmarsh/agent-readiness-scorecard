import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.checks import get_loc, analyze_functions, analyze_complexity, analyze_type_hints
from src.agent_scorecard.constants import PROFILES
from src.agent_scorecard.main import cli
from src.agent_scorecard.scoring import score_file
from click.testing import CliRunner

def test_get_loc(tmp_path: Path):
    """Tests that get_loc correctly counts lines, ignoring comments and blank lines."""
    content = "# This is a comment\n\n"
    content += "import os\n" * 10

    py_file = tmp_path / "loc_test.py"
    py_file.write_text(content, encoding="utf-8")

    loc = get_loc(str(py_file))
    assert loc == 10

def test_analyze_functions(tmp_path: Path):
    """Tests that analyze_functions calculates ACL correctly."""
    content = textwrap.dedent("""
    def simple_func(a: int):
        return a + 1

    def complex_func(a, b):
        if a > 0:
            if b > 0:
                return a + b
        return 0
    """)
    py_file = tmp_path / "func_test.py"
    py_file.write_text(content, encoding="utf-8")

    metrics = analyze_functions(str(py_file))
    assert len(metrics) == 2

    simple = next(m for m in metrics if m["name"] == "simple_func")
    complex_fn = next(m for m in metrics if m["name"] == "complex_func")

    assert simple["is_typed"] is True
    assert complex_fn["is_typed"] is False

    # simple_func: CC=1, LOC=2. ACL = 1 + 2/20 = 1.1
    assert simple["complexity"] == 1
    assert simple["loc"] == 2
    assert simple["acl"] == 1.1

    # complex_func: CC=3, LOC=5. ACL = 3 + 5/20 = 3.25
    assert complex_fn["complexity"] == 3
    assert complex_fn["loc"] == 5
    assert complex_fn["acl"] == 3.25

def test_score_file_new_metrics(tmp_path: Path):
    """Tests that score_file uses the new ACL and Type Safety Index."""
    content = textwrap.dedent("""
    def untyped_but_simple(a):
        return a
    """)
    py_file = tmp_path / "score_test.py"
    py_file.write_text(content, encoding="utf-8")

    profile = PROFILES["generic"]
    score, issues, loc, avg_comp, type_cov, metrics = score_file(str(py_file), profile)

    # type_cov should be 0% since untyped_but_simple has no type hints.
    # Penalty for < 90% type safety is -20.
    # ACL is Green (1 + 2/20 = 1.1). No ACL penalty.
    assert type_cov == 0
    assert score == 80
    assert "Type Safety Index 0% < 90%" in issues

def test_advise_command(tmp_path: Path):
    """Tests the advise command."""
    (tmp_path / "test.py").write_text("def f(a: int) -> None: pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["advise", str(tmp_path)])

    assert result.exit_code == 0
    assert "Agent Scorecard Report" in result.output
    assert "Top Refactoring Targets" in result.output
    assert "Type Safety Index" in result.output

def test_score_command_with_report(tmp_path: Path):
    """Tests the score command with the --report option."""
    (tmp_path / "test.py").write_text("def f(a: int) -> None: pass")
    report_path = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_path)])

    assert result.exit_code == 0
    assert report_path.exists()

    report_content = report_path.read_text()
    assert "# Agent Scorecard Report" in report_content
    assert "ACL = Complexity + (Lines of Code / 20)" in report_content
