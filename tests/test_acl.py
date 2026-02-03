import pytest
import textwrap
from pathlib import Path
<<<<<<< HEAD
from src.agent_scorecard.analyzer import calculate_acl, get_loc, get_complexity_score
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_acl_calculation_logic():
    """Tests the ACL calculation formula."""
    # Formula: ACL = CC + (LOC / 20)

    # Case 1: Simple file
=======
from src.agent_scorecard.analyzer import calculate_acl
from src.agent_scorecard.checks import analyze_functions
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_calculate_acl_logic():
    """Tests the ACL calculation formula."""
    # Formula: ACL = CC + (LOC / 20)

    # Case 1: Simple
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
    cc = 1.0
    loc = 20
    # ACL = 1 + 1 = 2
    assert calculate_acl(cc, loc) == 2.0

<<<<<<< HEAD
    # Case 2: Complex file
=======
    # Case 2: Complex
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
    cc = 10.0
    loc = 100
    # ACL = 10 + 5 = 15
    assert calculate_acl(cc, loc) == 15.0

    # Case 3: High ACL
    cc = 10.0
    loc = 200
    # ACL = 10 + 10 = 20
    assert calculate_acl(cc, loc) == 20.0

def test_scoring_with_acl_penalty(tmp_path: Path):
<<<<<<< HEAD
    """Tests that a function with high ACL receives a penalty."""

    # RESOLUTION: We use the Advisor-Mode setup (Large Function) because 
    # the new logic ignores global scope for ACL calculations.
    content = textwrap.dedent("""
    def big_function():
        x = 0
    """)
    # Add 320 lines of assignment inside the function
    for i in range(320):
        content += f"    x = {i}\n"
=======
    """Tests that a file with high ACL receives a penalty."""

    # Create a function with high ACL (> 20)
    # cc = 1, loc = 400 -> acl = 1 + 20 = 21.
    content = textwrap.dedent("""
    def very_long_function():
    """)
    content += "    print('hello')\n" * 400
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

<<<<<<< HEAD
    # Score the file
    score, details = score_file(str(py_file), PROFILES["generic"])

    # RESOLUTION: Verify the specific output format from scoring.py
    # "ACL(big_function) ... (-5)"
    assert "ACL(big_function)" in details
    assert "(-5)" in details
=======
    metrics = analyze_functions(str(py_file))
    acl = metrics[0]["acl"]
    assert acl > 20

    # Score the file
    score, issues, loc, avg_comp, type_cov, func_metrics = score_file(str(py_file), PROFILES["generic"])

    # ACL > 20 is Red ACL. Penalty is -15 per function.
    assert "Red ACL functions" in issues
    assert "(-15)" in issues

    # Type Safety is also checked. Single function, no types -> 0%. Penalty -20.
    # Total score should be 100 - 15 - 20 = 65.
    assert score == 65
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
