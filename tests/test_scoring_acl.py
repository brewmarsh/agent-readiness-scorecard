import textwrap
from pathlib import Path
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_score_file_acl_penalty(tmp_path):
    # Create a file with high ACL function
    # ACL = CC + LOC/20
<<<<<<< HEAD
    # Goal: > 15
=======
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
    # Let's make LOC high ~300 lines -> 15.

    code = "def high_acl():\n"
    code += "    x = 0\n"
    # 320 lines of assignment
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"

    p = tmp_path / "high_acl.py"
    p.write_text(code, encoding="utf-8")

<<<<<<< HEAD
    # Generic profile: max_loc 200. This file has > 320 lines, so LOC penalty applies too.
    # LOC penalty: (322 - 200) // 10 = 12 points.
    # ACL: CC=1, LOC=322. ACL = 1 + 16.1 = 17.1 > 15. Penalty 5.

    score, details = score_file(str(p), PROFILES['generic'])

    assert "ACL(high_acl)" in details
    assert "(-5)" in details
    assert "LOC" in details
=======
    # ACL: CC=1, LOC=322. ACL = 1 + 16.1 = 17.1. Yellow ACL. Penalty -5.
    # Type Safety: 0/1 typed -> 0%. Penalty -20.
    # Total score = 100 - 5 - 20 = 75.

    score, details, loc, avg_comp, type_cov, metrics = score_file(str(p), PROFILES['generic'])

    assert "Yellow ACL functions" in details
    assert "(-5)" in details
    assert "Type Safety Index" in details
    assert score == 75
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
