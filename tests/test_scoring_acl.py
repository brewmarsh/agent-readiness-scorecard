from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES
from click.testing import CliRunner
from agent_scorecard.main import cli


# TODO: Add type hints for Agent clarity
def test_score_file_acl_penalty(tmp_path):
    # Create a file with high ACL function
    # ACL = CC + LOC/20
    # Let's make LOC high ~300 lines -> 15.

    """TODO: Add docstring for AI context."""
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

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(p), PROFILES["generic"]
    )

    assert "Red ACL functions" in details
    assert "(-15)" in details
    assert "Type Safety Index" in details
    assert "Bloated File" in details
    assert score == 53


def test_cli_check_prompts_scoring_context_plain():
    """Verify check-prompts --plain handles scoring context suggestions correctly."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("scoring_prompt.txt", "w") as f:
            f.write("Analyze the ACL of this file.")

        result = runner.invoke(cli, ["check-prompts", "scoring_prompt.txt", "--plain"])
        assert "Refactored Suggestions:" in result.output
        assert "FAILED: Prompt score too low." in result.output
