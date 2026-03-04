import textwrap
from pathlib import Path
from agent_readiness_scorecard.analyzers.python import PythonAnalyzer
from agent_readiness_scorecard.constants import PROFILES


def test_acl_calculation_logic() -> None:
    """
    Tests the Agent Cognitive Load (ACL) calculation formula.

    The formula verified is: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)

    Returns:
        None
    """
    # Case 1: Simple file (Low complexity, short length, depth 0)
    cc = 1.0
    loc = 20
    depth = 0
    # ACL = (0*2) + (1*1.5) + (20/50) = 1.5 + 0.4 = 1.9
    assert PythonAnalyzer().calculate_acl(cc, loc, depth) == 1.9

    # Case 2: Complex file (Medium complexity, medium length, depth 5)
    cc = 10.0
    loc = 100
    depth = 5
    # ACL = (5*2) + (10*1.5) + (100/50) = 10 + 15 + 2 = 27.0
    assert PythonAnalyzer().calculate_acl(cc, loc, depth) == 27.0

    # Case 3: High ACL (High complexity, high length, depth 0)
    cc = 10.0
    loc = 200
    depth = 0
    # ACL = (0*2) + (10*1.5) + (200/50) = 15 + 4 = 19.0
    assert PythonAnalyzer().calculate_acl(cc, loc, depth) == 19.0


def test_scoring_with_acl_penalty(tmp_path: Path) -> None:
    """
    Tests that a function with high ACL receives a penalty during file scoring.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """

    # RESOLUTION: Combined the deep nesting from the refactor branch with
    # the volume testing from beta to thoroughly stress-test the new ACL formula.
    content = textwrap.dedent(
        """
    def big_function():
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            x = 0
    """
    )

    # Add 320 lines of assignment inside the function to force a high ACL/LOC penalty
    for i in range(320):
        content += f"            x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    # Score the file using the generic agent profile
    score, details, loc, avg_comp, type_cov, func_metrics = PythonAnalyzer().score_file(
        str(py_file), PROFILES["generic"]
    )

    # RESOLUTION: Verify the specific output format from scoring.py
    # Math: Depth=5, CC=6, LOC=328.
    # ACL = (5 * 2) + (6 * 1.5) + (328 / 50) = 10 + 9 + 6.56 = 25.56
    # This triggers the "Red ACL status" (>15) which applies a -15 point penalty.
    assert "Red ACL functions" in details
    assert "(-15)" in details

    # Verify secondary penalty: Bloated file penalty for total LOC > 200
    assert "Bloated File" in details
    assert any(m["name"] == "big_function" for m in func_metrics)
