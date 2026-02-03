import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import get_acl_score, get_loc, get_complexity_score
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_get_acl_score_logic():
    """Tests the ACL calculation formula."""
    # Formula: ACL = CC + (LOC / 20)

    # Case 1: Simple file
    cc = 1.0
    loc = 20
    # ACL = 1 + 1 = 2
    assert get_acl_score(loc, cc) == 2.0

    # Case 2: Complex file
    cc = 10.0
    loc = 100
    # ACL = 10 + 5 = 15
    assert get_acl_score(loc, cc) == 15.0

    # Case 3: High ACL
    cc = 10.0
    loc = 200
    # ACL = 10 + 10 = 20
    assert get_acl_score(loc, cc) == 20.0

def test_scoring_with_acl_penalty(tmp_path: Path):
    """Tests that a file with high ACL receives a penalty."""

    # Create a file that will result in high ACL for a function.
    # ACL > 15.
    # We create a function with > 300 LOC.
    # complexity 1. ACL = 1 + 300/20 = 16.

    content = textwrap.dedent("""
    def big_function():
        x = 0
    """)
    # Add 320 lines of assignment inside the function
    for i in range(320):
        content += f"    x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    # Score the file
    score, details = score_file(str(py_file), PROFILES["generic"])

    assert "Hallucination Risk" in details
    # We expect -5 penalty (defined in scoring.py) + maybe LOC penalty?
    # Max LOC is 200. 320 lines -> 120 excess -> -12.
    # Plus -5 for ACL.
    # The test specifically checks for the ACL penalty part string.
    assert "(-5)" in details
