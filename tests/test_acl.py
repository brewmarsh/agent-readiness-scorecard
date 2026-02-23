import textwrap
from pathlib import Path
from agent_scorecard.analyzer import calculate_acl
from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES


def test_acl_calculation_logic() -> None:
    """
    Tests the Agent Cognitive Load (ACL) calculation formula.

    The formula verified is: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)

    Returns:
        None
    """
    # Case 1: Simple file (Low complexity, short length, flat)
    cc = 1.0
    loc = 20
    depth = 1
    # ACL = (1 * 2) + (1 * 1.5) + (20 / 50) = 2 + 1.5 + 0.4 = 3.9
    assert calculate_acl(cc, loc, depth) == 3.9

    # Case 2: Complex file (Medium complexity, medium length, nested)
    cc = 10.0
    loc = 100
    depth = 3
    # ACL = (3 * 2) + (10 * 1.5) + (100 / 50) = 6 + 15 + 2 = 23.0
    assert calculate_acl(cc, loc, depth) == 23.0

    # Case 3: High ACL (High complexity, high length, deep nesting - Hallucination risk)
    cc = 10.0
    loc = 200
    depth = 5
    # ACL = (5 * 2) + (10 * 1.5) + (200 / 50) = 10 + 15 + 4 = 29.0
    assert calculate_acl(cc, loc, depth) == 29.0


def test_scoring_with_acl_penalty(tmp_path: Path) -> None:
    """
    Tests that a function with high ACL receives a penalty during file scoring.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """

    # RESOLUTION: We use a deeply nested structure to trigger Red ACL (>15)
    content = textwrap.dedent(
        """
    def deeply_nested_function():
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            x = 0
    """
    )
    # Add 320 lines of assignment inside the function to force a high LOC and bloat penalty
    # Indentation must match the 24 spaces of level 6
    for i in range(320):
        content += f"                        x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    # Score the file using the generic agent profile
    score, details, loc, avg_comp, type_cov, func_metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    # RESOLUTION: Verify the specific output format from scoring.py
    # Math:
    # Depth = 5
    # CC = 6 (Function + 5 Ifs)
    # LOC = ~327
    # ACL = (5*2) + (6*1.5) + (327/50) = 10 + 9 + 6.54 = 25.54 -> Red ACL status (>15)
    assert "Red ACL functions" in details
    assert "(-15)" in details

    # Verify secondary penalty: Bloated file penalty for total LOC > 200
    assert "Bloated File" in details
    assert any(m["name"] == "deeply_nested_function" for m in func_metrics)
