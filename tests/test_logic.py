import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.checks import get_loc, analyze_complexity, analyze_type_hints
from src.agent_scorecard.constants import PROFILES
from src.agent_scorecard.main import cli
from click.testing import CliRunner

def test_get_loc(tmp_path: Path):
    """Tests that get_loc correctly counts lines, ignoring comments and blank lines."""
    # Create a file with more than 200 lines
    content = "# This is a comment\n\n"
    content += "import os\n" * 210

    py_file = tmp_path / "loc_test.py"
    py_file.write_text(content, encoding="utf-8")

    loc = get_loc(str(py_file))
    assert loc == 210

def test_analyze_complexity(tmp_path: Path):
    """Tests that analyze_complexity measures complexity correctly."""
    # Create a file with a function that is complex
    content = textwrap.dedent("""
    def very_complex_function(a, b, c):
        if a > 0:
            if b > 0:
                if c > 0:
                    for i in range(10):
                        for j in range(10):
                            if i % 2 == 0 and j % 2 == 0:
                                if a + b + c > i + j:
                                    return True
                                elif a * b > c:
                                    return False
        return None
    """)
    py_file = tmp_path / "complexity_test.py"
    py_file.write_text(content, encoding="utf-8")

    # Using the "jules" profile which has a max_complexity of 8
    avg_complexity = analyze_complexity(str(py_file))
    assert avg_complexity > PROFILES["jules"]["max_complexity"]

def test_analyze_type_hints(tmp_path: Path):
    """Tests that analyze_type_hints calculates coverage."""
    # File with 100% type hint coverage
    typed_content = """
def fully_typed_function(a: int, b: str) -> bool:
    return a > 0 and b == "hello"
"""
    typed_file = tmp_path / "typed.py"
    typed_file.write_text(typed_content, encoding="utf-8")

    # File with 0% type hint coverage
    untyped_content = """
def untyped_function(a, b):
    return a > 0 and b == "hello"
"""
    untyped_file = tmp_path / "untyped.py"
    untyped_file.write_text(untyped_content, encoding="utf-8")

    typed_coverage = analyze_type_hints(str(typed_file))
    untyped_coverage = analyze_type_hints(str(untyped_file))

    assert typed_coverage == 100
    assert untyped_coverage == 0

def test_advise_command(tmp_path: Path):
    """Tests the advise command."""
    (tmp_path / "test.py").write_text("def f(a,b,c): pass")
    (tmp_path / "README.md").write_text("# README")

    runner = CliRunner()
    result = runner.invoke(cli, ["advise", str(tmp_path)])

    assert result.exit_code == 0
    assert "Agent Scorecard Report" in result.output
    assert "Top Refactoring Targets" in result.output
    assert "Agent Prompts" in result.output
    assert "Documentation Health" in result.output

def test_score_command_with_report(tmp_path: Path):
    """Tests the score command with the --report option."""
    (tmp_path / "test.py").write_text("def f(a,b,c): pass")
    (tmp_path / "README.md").write_text("# README")
    report_path = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_path)])

    assert result.exit_code == 0
    assert report_path.exists()

    report_content = report_path.read_text()
    assert "# Agent Scorecard Report" in report_content
    assert "Final Score" in report_content
    assert "| File | Score | Issues |" in report_content
