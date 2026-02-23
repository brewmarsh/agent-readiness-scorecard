from click.testing import CliRunner
from agent_scorecard.main import cli

def test_score_limit_to() -> None:
    """
    Test that --limit-to correctly restricts analysis to specified files.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("file1.py", "w") as f:
            f.write("def foo():\n    pass\n")
        with open("file2.py", "w") as f:
            f.write("def bar():\n    pass\n")
        with open("README.md", "w") as f:
            f.write("# README")

        # Run only on file1.py
        # We use verbosity=detailed to see all files in output
        result = runner.invoke(cli, ["score", ".", "--limit-to", "file1.py", "--verbosity", "detailed"])

        assert result.exit_code == 0
        assert "file1.py" in result.output
        assert "file2.py" not in result.output

def test_score_limit_to_multiple() -> None:
    """
    Test that --limit-to handles multiple files correctly.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("file1.py", "w") as f:
            f.write("def foo():\n    pass\n")
        with open("file2.py", "w") as f:
            f.write("def bar():\n    pass\n")
        with open("file3.py", "w") as f:
            f.write("def baz():\n    pass\n")
        with open("README.md", "w") as f:
            f.write("# README")

        # Run on file1.py and file2.py
        result = runner.invoke(cli, ["score", ".", "--limit-to", "file1.py", "--limit-to", "file2.py", "--verbosity", "detailed"])

        assert result.exit_code == 0
        assert "file1.py" in result.output
        assert "file2.py" in result.output
        assert "file3.py" not in result.output
