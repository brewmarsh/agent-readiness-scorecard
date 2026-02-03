import textwrap
from pathlib import Path
from click.testing import CliRunner
from src.agent_scorecard.main import cli

def test_report_full(tmp_path):
<<<<<<< HEAD
    # Create file with high ACL
    code = "def high_acl():\n"
    code += "    x = 0\n"
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"
    (tmp_path / "high_acl.py").write_text(code, encoding="utf-8")

=======
    # Create file with high ACL (Red)
    # cc = 1, loc = 400 -> acl = 1 + 20 = 21.
    code = "def red_acl():\n"
    for i in range(400):
        code += f"    print({i})\n"
    (tmp_path / "high_acl.py").write_text(code, encoding="utf-8")

    # Score should be:
    # File Score: 100 - 15 (Red ACL) - 20 (Type Safety Index 0%) = 65.
    # Project Score (no README.md): 100 - 15 = 85.
    # Final Score: 65 * 0.8 + 85 * 0.2 = 52 + 17 = 69.
    # 69 < 70, so exit code should be 1.

>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
    # Report output file
    report_file = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_file)])

<<<<<<< HEAD
    assert result.exit_code == 1 # Fails because score is low

    content = report_file.read_text(encoding="utf-8")

    assert "High ACL" in content
    assert "high_acl.py" in content
    assert "ACL 17.1" in content # approx
    assert "High Cognitive Load" in content
    assert "Missing Critical Agent Docs" in content
=======
    assert result.exit_code == 1

    content = report_file.read_text(encoding="utf-8")

    assert "Top Refactoring Targets (Agent Cognitive Load)" in content
    assert "red_acl" in content
    assert "🔴 Red" in content
    assert "Type Safety Index" in content
    assert "Agent Prompts for Remediation" in content
    assert "Missing Critical Documentation" in content
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
