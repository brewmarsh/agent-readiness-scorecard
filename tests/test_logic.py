import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import get_loc, get_complexity_score, check_type_hints
from src.agent_scorecard.main import PROFILES, cli
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

def test_get_complexity_score(tmp_path: Path):
    """Tests that get_complexity_score calculates complexity correctly."""
    # Create a file with a function that is too complex
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
    avg_complexity = get_complexity_score(str(py_file))
    assert avg_complexity > PROFILES["jules"]["max_complexity"]

def test_check_type_hints(tmp_path: Path):
    """Tests that check_type_hints calculates coverage correctly."""
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

    typed_coverage = check_type_hints(str(typed_file))
    untyped_coverage = check_type_hints(str(untyped_file))

    assert typed_coverage == 100
    assert untyped_coverage == 0

def test_advise_command(tmp_path: Path):
    """Tests the advise command."""
    (tmp_path / "test.py").write_text("def f(a,b,c): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["advise", str(tmp_path)])

    assert result.exit_code == 0
    assert "Agent Scorecard Report" in result.output
    assert "Top Refactoring Targets" in result.output
    assert "Agent Prompts" in result.output
    assert "Documentation Health" in result.output
