from click.testing import CliRunner
from agent_scorecard.main import cli
import os


def test_cli_report_style_option() -> None:
    """Test that the --report-style CLI option works correctly."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a dummy python file
        with open("test.py", "w") as f:
            f.write("def hello(): pass\n")

        # Run score with --report and --report-style
        result = runner.invoke(
            cli, ["score", ".", "--report", "report.md", "--report-style", "collapsed"]
        )
        print(result.output)
        # It might exit with 1 if score < 70, which is expected here since no docs
        assert os.path.exists("report.md")

        with open("report.md", "r", encoding="utf-8") as f:
            content = f.read()
            assert "Overall Score" in content
            assert "File Analysis" not in content
