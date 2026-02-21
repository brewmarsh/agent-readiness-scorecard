import textwrap
from pathlib import Path
from click.testing import CliRunner

# RESOLUTION: Import from the correct modules (analyzer/scoring) not deleted 'checks'
from agent_scorecard import analyzer
from agent_scorecard.constants import PROFILES
from agent_scorecard.main import cli
from agent_scorecard.scoring import score_file


def test_get_loc(tmp_path: Path) -> None:
    """
    Tests that get_loc correctly counts lines, ignoring comments and blank lines.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    content = "# This is a comment\n\n"
    content += "import os\n" * 10

    py_file = tmp_path / "loc_test.py"
    py_file.write_text(content, encoding="utf-8")

    loc = analyzer.get_loc(str(py_file))
    assert loc == 10


def test_get_function_stats(tmp_path: Path) -> None:
    """
    Tests that get_function_stats calculates ACL correctly.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
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

    # RESOLUTION: Use analyzer.get_function_stats instead of analyze_functions
    metrics = analyzer.get_function_stats(str(py_file))
    assert len(metrics) == 2

    simple = next(m for m in metrics if m["name"] == "simple_func")
    complex_fn = next(m for m in metrics if m["name"] == "complex_func")

    # simple_func: CC=1, LOC=2. ACL = 1 + 2/20 = 1.1
    assert simple["complexity"] == 1
    assert simple["loc"] == 2
    assert simple["acl"] == 1.1

    # complex_func: CC=3, LOC=5. ACL = 3 + 5/20 = 3.25
    assert complex_fn["complexity"] == 3
    assert complex_fn["loc"] == 5
    assert complex_fn["acl"] == 3.25


def test_check_type_hints(tmp_path: Path) -> None:
    """
    Tests that check_type_hints calculates coverage.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
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

    # RESOLUTION: Use analyzer.check_type_hints
    typed_coverage = analyzer.check_type_hints(str(typed_file))
    untyped_coverage = analyzer.check_type_hints(str(untyped_file))

    assert typed_coverage == 100
    assert untyped_coverage == 0


def test_score_file_logic(tmp_path: Path) -> None:
    """
    Tests scoring logic, including penalties for low type safety.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    content = textwrap.dedent("""
    def untyped_but_simple(a):
        return a
    """)
    py_file = tmp_path / "score_test.py"
    py_file.write_text(content, encoding="utf-8")

    profile = PROFILES["generic"]

    # RESOLUTION: score_file returns (score, details_string, ...) in Upgrade branch
    score, issues, loc, complexity, type_safety, metrics = score_file(
        str(py_file), profile
    )

    # Check metrics manually to verify why score is what it is
    type_cov = analyzer.check_type_hints(str(py_file))

    # type_cov should be 0% -> Penalty -20
    # ACL is Green -> No penalty
    # Base 100 - 20 = 80
    assert type_cov == 0
    assert score == 80
    # The scoring string format comes from the resolved scoring.py
    assert "Type Safety Index 0% < 90%" in issues


def test_advise_command(tmp_path: Path) -> None:
    """
    Tests the advise command.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    (tmp_path / "test.py").write_text("def f(a,b,c): pass")
    # Add README to prevent missing doc noise (though advice doesn't check docs usually)
    (tmp_path / "README.md").write_text("# README")

    runner = CliRunner()
    result = runner.invoke(cli, ["advise", str(tmp_path)])

    assert result.exit_code == 0
    # RESOLUTION: Expect the Upgrade branch's specific Advisor Report header
    assert "Agent Advisor Report" in result.output
    assert "Agent Cognitive Load" in result.output


def test_score_command_with_report(tmp_path: Path) -> None:
    """
    Tests the score command with the --report option.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    (tmp_path / "test.py").write_text("def f(a,b,c): pass")
    (tmp_path / "README.md").write_text("# README")
    report_path = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_path)])

    assert result.exit_code == 0
    assert report_path.exists()

    report_content = report_path.read_text(encoding="utf-8")

    assert "# Agent Scorecard Report" in report_content
    assert "Overall Score" in report_content
    # Check for the combined sections from our resolved report.py
    assert "Type Safety Index" in report_content
