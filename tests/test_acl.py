import pytest
import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import calculate_acl, get_loc, get_complexity_score
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_calculate_acl_logic():
    """Tests the ACL calculation formula."""
    # Formula: ACL = CC + (LOC / 20)

    # Case 1: Simple file
    cc = 1.0
    loc = 20
    # ACL = 1 + 1 = 2
    assert calculate_acl(cc, loc) == 2.0

    # Case 2: Complex file
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
    """Tests that a function with high ACL receives a penalty."""

    content = textwrap.dedent("""
    def very_long_function():
    """)
    for i in range(320):
        content += f"    x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    # Score the file
    score, details = score_file(str(py_file), PROFILES["generic"])

    assert "ACL" in details
    assert "(-5)" in details
