import textwrap
from pathlib import Path
from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_score_file_acl_penalty(tmp_path):
    # Create a file with high ACL function
    # ACL = CC + LOC/20
    # Goal: > 15
    # Let's make LOC high ~300 lines -> 15.

    code = "def high_acl():\n"
    code += "    x = 0\n"
    # 320 lines of assignment
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"

    p = tmp_path / "high_acl.py"
    p.write_text(code, encoding="utf-8")

    # Generic profile: max_loc 200. This file has > 320 lines, so LOC penalty applies too.
    # LOC penalty: (322 - 200) // 10 = 12 points.
    # ACL: CC=1, LOC=322. ACL = 1 + 16.1 = 17.1 > 15. Penalty 5.

    score, details = score_file(str(p), PROFILES['generic'])

    assert "ACL(high_acl)" in details
    assert "(-5)" in details
    assert "LOC" in details
