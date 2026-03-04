import pytest
from pathlib import Path
from agent_readiness_scorecard.analyzer import scan_project_docs
from agent_readiness_scorecard.analyzers.python import PythonAnalyzer
from agent_readiness_scorecard.scoring import generate_badge


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """
    Pytest fixture to create a sample Python file for analysis.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        Path: Path to the created sample file.
    """
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "hello.py"
    p.write_text(
        """
def hello():
    print("Hello")

def complex_func(n):
    if n > 1:
        if n > 2:
            if n > 3:
                return 3
    return 1
"""
    )
    return p


@pytest.fixture
def typed_file(tmp_path: Path) -> Path:
    """
    Pytest fixture to create a typed Python file for analysis.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        Path: Path to the created typed file.
    """
    p = tmp_path / "typed.py"
    p.write_text(
        """
def add(a: int, b: int) -> int:
    return a + b
"""
    )
    return p


def test_get_loc(sample_file: Path) -> None:
    """
    Tests line count calculation on a sample file.

    Args:
        sample_file (Path): Path to the sample file.

    Returns:
        None
    """
    assert PythonAnalyzer()._get_loc(str(sample_file)) == 8


def test_analyze_complexity(sample_file: Path) -> None:
    """
    Tests complexity score calculation on a sample file.

    Args:
        sample_file (Path): Path to the sample file.

    Returns:
        None
    """
    avg = PythonAnalyzer().get_complexity_score(str(sample_file))
    assert avg == 2.5

    # Penalty Logic Simulation (threshold=10)
    penalty = 10 if avg > 10 else 0
    assert penalty == 0

    # Penalty Logic Simulation (threshold=2)
    penalty = 10 if avg > 2 else 0
    assert penalty == 10


def test_check_type_hints(sample_file: Path, typed_file: Path) -> None:
    """
    Tests type hint coverage calculation.

    Args:
        sample_file (Path): Path to an untyped sample file.
        typed_file (Path): Path to a typed sample file.

    Returns:
        None
    """
    cov = PythonAnalyzer().check_type_hints(str(sample_file))
    assert cov == 0

    # Penalty Logic Simulation (threshold=50)
    penalty = 20 if cov < 50 else 0
    assert penalty == 20

    # typed_file: 1/1 typed -> 100%
    cov = PythonAnalyzer().check_type_hints(str(typed_file))
    assert cov == 100

    # Penalty Logic Simulation (threshold=50)
    penalty = 20 if cov < 50 else 0
    assert penalty == 0


def test_scan_project_docs(tmp_path: Path) -> None:
    """
    Tests scanning for project documentation files.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    required = ["agents.md", "instructions.md"]
    missing = scan_project_docs(str(tmp_path), required)
    assert "agents.md" in missing
    assert "instructions.md" in missing

    (tmp_path / "agents.md").touch()
    missing = scan_project_docs(str(tmp_path), required)
    assert "agents.md" not in missing
    assert "instructions.md" in missing


def test_generate_badge() -> None:
    """
    Tests SVG badge generation for various score ranges.

    Returns:
        None
    """
    svg = generate_badge(95)
    assert "#4c1" in svg
    assert "95/100" in svg

    # >= 70 and < 90: Green
    svg = generate_badge(85)
    assert "#97ca00" in svg
    assert "85/100" in svg

    # >= 50 and < 70: Yellow
    svg = generate_badge(60)
    assert "#dfb317" in svg
    assert "60/100" in svg

    # < 50: Red
    svg = generate_badge(40)
    assert "#e05d44" in svg
    assert "40/100" in svg
