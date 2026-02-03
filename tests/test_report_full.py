import textwrap
from pathlib import Path
from click.testing import CliRunner
from src.agent_scorecard.main import cli

def test_report_full(tmp_path):
    # Create file with high ACL
    code = "def high_acl():\n"
    code += "    x = 0\n"
    for i in range(320):
        code += f"    x += {i}\n"
    code += "    return x\n"
    (tmp_path / "high_acl.py").write_text(code, encoding="utf-8")

    # Report output file
    report_file = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path), "--report", str(report_file)])

    assert result.exit_code == 1 # Fails because score is low

    content = report_file.read_text(encoding="utf-8")

    assert "High ACL" in content
    assert "high_acl.py" in content
    assert "ACL 17.1" in content # approx
    assert "High Cognitive Load" in content
    assert "Missing Critical Agent Docs" in content
