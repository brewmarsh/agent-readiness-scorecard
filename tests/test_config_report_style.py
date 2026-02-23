from click.testing import CliRunner
from agent_scorecard.main import cli
import os


def test_pyproject_config_report_style() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a dummy python file
        with open("test.py", "w") as f:
            f.write("def hello(): pass\n")

        # Create pyproject.toml
        with open("pyproject.toml", "w") as f:
            f.write("[tool.agent-scorecard]\nreport_style = 'collapsed'\n")

        # Run score with --report
        runner.invoke(cli, ["score", ".", "--report", "report.md"])
        assert os.path.exists("report.md")

        with open("report.md", "r") as f:
            content = f.read()
            assert "Overall Score" in content
            assert "File Analysis" not in content
