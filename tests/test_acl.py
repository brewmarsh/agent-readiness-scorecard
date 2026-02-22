import textwrap
from pathlib import Path
from agent_scorecard.analyzer import calculate_acl
from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES


def test_acl_calculation_logic() -> None:
    """
    Tests the Agent Cognitive Load (ACL) calculation formula.

    The formula verified is: ACL = Cyclomatic Complexity + (Lines of Code / 20)

    Returns:
        None
    """
    # Case 1: Simple file (Low complexity, short length)
    cc = 1.0
    loc = 20
    # ACL = 1 + 1 = 2.0
    assert calculate_acl(cc, loc) == 2.0

    # Case 2: Complex file (Medium complexity, medium length)
    cc = 10.0
    loc = 100
    # ACL = 10 + 5 = 15.0
    assert calculate_acl(cc, loc) == 15.0

    # Case 3: High ACL (High complexity, high length - Hallucination risk)
    cc = 10.0
    loc = 200
    # ACL = 10 + 10 = 20.0
    assert calculate_acl(cc, loc) == 20.0


def test_scoring_with_acl_penalty(tmp_path: Path) -> None:
    """
    Tests that a function with high ACL receives a penalty during file scoring.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """

    # RESOLUTION: We use the Advisor-Mode setup (Large Function) because
    # the new logic ignores global scope for ACL calculations to focus on unit depth.
    content = textwrap.dedent("""
    def big_function():
        x = 0
    """)
    # Add 320 lines of assignment inside the function to force a high ACL
    for i in range(320):
        content += f"    x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    # Score the file using the generic agent profile
    score, details, loc, avg_comp, type_cov, func_metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    # RESOLUTION: Verify the specific output format from scoring.py
    # Math: 322 LOC / 20 + 1 CC = 17.1 ACL -> Red ACL status (>15)
    assert "Red ACL functions" in details
    assert "(-15)" in details

    # Verify secondary penalty: Bloated file penalty for total LOC > 200
    assert "Bloated File" in details
    assert any(m["name"] == "big_function" for m in func_metrics)
