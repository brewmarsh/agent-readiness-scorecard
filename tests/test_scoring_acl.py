from pathlib import Path
from click.testing import CliRunner
from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES
from agent_scorecard.main import cli


def test_score_file_acl_penalty(tmp_path: Path) -> None:
    """
    Tests ACL (Agent Cognitive Load) penalty calculation within the scoring engine.
    
    This test verifies that the system correctly applies cumulative penalties for 
    high cognitive load, low type safety, and file bloat.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Create a file with a high ACL function
    # Formula: ACL = CC + LOC/20
    code = "def high_acl():\n"
    code += "    x = 0\n"
    # 320 lines of assignment to force high LOC
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"

    p = tmp_path / "high_acl.py"
    p.write_text(code, encoding="utf-8")

    # Math Breakdown:
    # 1. ACL: CC=1, LOC=323. ACL = 1 + 16.15 = 17.15. Red ACL (>15) Penalty: -15.
    # 2. Type Safety: 0/1 functions typed = 0%. Penalty: -20.
    # 3. Bloated File: 323 LOC - 200 threshold = 123. Penalty (1 per 10 lines): -12.
    # Total Score: 100 - 15 - 20 - 12 = 53.

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(p), PROFILES["generic"]
    )

    # Verify that each specific penalty is reflected in the scoring details
    assert "Red ACL functions" in details
    assert "(-15)" in details
    assert "Type Safety Index" in details
    assert "Bloated File" in details
    assert score == 53


def test_cli_check_prompts_scoring_context_plain() -> None:
    """
    Verify check-prompts --plain handles scoring context suggestions correctly.

    This ensures that the CLI output remains compatible with the GitHub Action 
    regex requirements for refactored suggestions and failure strings.

    Returns:
        None
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("scoring_prompt.txt", "w") as f:
            f.write("Analyze the ACL of this file.")

        result = runner.invoke(cli, ["check-prompts", "scoring_prompt.txt", "--plain"])
        
        # RESOLUTION: Assert exact strings established for CI pipeline regex
        assert "Refactored Suggestions:" in result.output
        assert "FAILED: Prompt score too low." in result.output