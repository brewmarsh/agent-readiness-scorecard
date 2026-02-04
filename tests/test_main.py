import pytest
from pathlib import Path
from src.agent_scorecard.analyzer import (
    get_loc,
    get_complexity_score,  # Renamed from analyze_complexity
    check_type_hints,      # Renamed from analyze_type_hints
    scan_project_docs,
)
from src.agent_scorecard.scoring import generate_badge

@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "hello.py"
    p.write_text("""
def hello():
    print("Hello")

def complex_func(n):
    if n > 1:
        if n > 2:
            if n > 3:
                return 3
    return 1
""")
    return p

@pytest.fixture
def typed_file(tmp_path: Path) -> Path:
    p = tmp_path / "typed.py"
    p.write_text("""
def add(a: int, b: int) -> int:
    return a + b
""")
    return p

def test_get_loc(sample_file: Path) -> None:
    # Manual count: 8 lines
    assert get_loc(str(sample_file)) == 8

def test_analyze_complexity(sample_file: Path) -> None:
    # hello: 1
    # complex_func: 4 (1 + 3 ifs)
    # Avg: 2.5
    # RESOLUTION: Use new function name
    avg = get_complexity_score(str(sample_file))
    assert avg == 2.5

    # Penalty Logic Simulation (threshold=10)
    penalty = 10 if avg > 10 else 0
    assert penalty == 0

    # Penalty Logic Simulation (threshold=2)
    penalty = 10 if avg > 2 else 0
    assert penalty == 10

def test_check_type_hints(sample_file: Path, typed_file: Path) -> None:
    # sample_file: 0/2 typed -> 0%
    # RESOLUTION: Use new function name
    cov = check_type_hints(str(sample_file))
    assert cov == 0

    # Penalty Logic Simulation (threshold=50)
    penalty = 20 if cov < 50 else 0
    assert penalty == 20

    # typed_file: 1/1 typed -> 100%
    cov = check_type_hints(str(typed_file))
    assert cov == 100

    # Penalty Logic Simulation (threshold=50)
    penalty = 20 if cov < 50 else 0
    assert penalty == 0

def test_scan_project_docs(tmp_path: Path) -> None:
    required = ["agents.md", "instructions.md"]
    missing = scan_project_docs(str(tmp_path), required)
    assert "agents.md" in missing
    assert "instructions.md" in missing

    (tmp_path / "agents.md").touch()
    missing = scan_project_docs(str(tmp_path), required)
    assert "agents.md" not in missing
    assert "instructions.md" in missing

def test_generate_badge() -> None:
    # >= 90: Bright Green
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
