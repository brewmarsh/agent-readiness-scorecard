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

    # Create a file that will result in high ACL.
    # We need ACL > 15.
    # Let's make LOC high. LOC contribution = LOC / 20.
    # If LOC = 300, contribution is 15. Complexity >= 1. Total >= 16.

    content = "x = 1\n" * 320
    # Simple assignments have complexity 0 usually? Or 1? mccabe usually counts functions?
    # Analyzer uses mccabe.PathGraphingAstVisitor.
    # If there are no functions, complexity is 0?
    # analyzer.get_complexity_score returns 0 if no complexities found.

    # So let's add a function.
    content += textwrap.dedent("""
    def foo():
        pass
    """)
    # complexity 1.

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    loc = get_loc(str(py_file))
    comp = get_complexity_score(str(py_file))

    # verify logic
    # loc should be around 322.
    # comp should be 1.
    # acl = 1 + 322/20 = 1 + 16.1 = 17.1 > 15.

    acl = get_acl_score(loc, comp)
    assert acl > 15, f"Expected ACL > 15, got {acl} (LOC={loc}, Comp={comp})"

    # Score the file
    # Generic profile max_loc is 200.
    # So we will also have LOC penalty.
    score, details = score_file(str(py_file), PROFILES["generic"])

    assert "Hallucination Risk" in details
    assert "(-10)" in details
