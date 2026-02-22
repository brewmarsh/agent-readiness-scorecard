from pathlib import Path
from click.testing import CliRunner
from agent_scorecard.main import cli


def test_report_full(tmp_path: Path) -> None:
    """
    Tests the full Markdown report generation through the CLI interface.

    This test verifies that the 'score' command correctly identifies high-ACL
    files and generates a structured report containing refactoring targets,
    type safety metrics, and remediation prompts.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Create a file with high ACL to trigger various report sections
    # Math: 402 LOC / 20 + 1 CC = 21.1 ACL (triggers Red status > 15)
    code = "def high_acl():\n"
    code += "    x = 0\n"
    for i in range(400):
        code += f"    x += {i}\n"
    code += "    return x\n"
    (tmp_path / "high_acl.py").write_text(code, encoding="utf-8")

    # Define the output path for the Markdown report
    report_file = tmp_path / "report.md"

    runner = CliRunner()
    # Invoke the score command
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_file)])

    # The command should exit with code 1 because the score is below the 70 threshold
    assert result.exit_code == 1

    # Read the generated report and verify its content structure
    content = report_file.read_text(encoding="utf-8")

    assert "# Agent Scorecard Report" in content
    assert "high_acl.py" in content

    # Verify the high-fidelity sections established in the Beta branch
    assert "Top Refactoring Targets (Agent Cognitive Load (ACL))" in content
    assert "Type Safety Index" in content
    assert "Agent Prompts for Remediation" in content
