import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.main import get_loc, get_complexity_score, check_type_hints, PROFILES

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
    """Tests that get_complexity_score penalizes overly complex functions."""
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
    avg_complexity, penalty = get_complexity_score(str(py_file), PROFILES["jules"]["max_complexity"])
    assert penalty > 0
    assert avg_complexity > PROFILES["jules"]["max_complexity"]

def test_check_type_hints(tmp_path: Path):
    """Tests that check_type_hints penalizes files with low type hint coverage."""
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

    # Using "jules" profile which requires 80% coverage
    profile = PROFILES["jules"]

    typed_coverage, typed_penalty = check_type_hints(str(typed_file), profile["min_type_coverage"])
    untyped_coverage, untyped_penalty = check_type_hints(str(untyped_file), profile["min_type_coverage"])

    assert typed_coverage == 100
    assert typed_penalty == 0

    assert untyped_coverage == 0
    assert untyped_penalty > 0
