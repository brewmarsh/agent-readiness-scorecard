from src.agent_scorecard.scoring import score_file
from src.agent_scorecard.constants import PROFILES

def test_score_file_acl_penalty(tmp_path):
    # Create a file with high ACL function
    # ACL = CC + LOC/20
    # Let's make LOC high ~300 lines -> 15.

    code = "def high_acl():\n"
    code += "    x = 0\n"
    # 320 lines of assignment
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"

    p = tmp_path / "high_acl.py"
    p.write_text(code, encoding="utf-8")

    # ACL: CC=1, LOC=323. ACL = 1 + 16.15 = 17.15. Red ACL (>15). Penalty -15.
    # Type Safety: 0/1 typed -> 0%. Penalty -20.
    # Bloated File (323 LOC): -12.
    # Total score = 100 - 15 - 20 - 12 = 53.

    score, details, loc, avg_comp, type_cov, metrics = score_file(str(p), PROFILES['generic'])

    assert "Red ACL functions" in details
    assert "(-15)" in details
    assert "Type Safety Index" in details
    assert "Bloated File" in details
    assert score == 53
