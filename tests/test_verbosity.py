from click.testing import CliRunner
from agent_scorecard.main import cli


def test_verbosity_quiet():
    """Test quiet mode behavior (should only print score and critical issues)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("hello.py", "w") as f:
            f.write("def hello():\n    pass\n")
        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--verbosity", "quiet"])
        assert result.exit_code == 0
        # Should NOT contain tables or "Running Agent Scorecard"
        assert "Environment Health" not in result.output
        assert "File Analysis" not in result.output
        assert "Running Agent Scorecard" not in result.output
        assert "Final Agent Score" in result.output


def test_verbosity_summary():
    """Test summary mode behavior (default)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # One passing file (score 100), one failing file (score < 70)
        with open("pass.py", "w") as f:
            f.write('def good() -> None:\n    """Docstring."""\n    pass\n')

        # Create a complex, untyped function to ensure score < 70
        # Complexity 20 -> -15 penalty.
        # Untyped -> -20 penalty.
        # Score = 65.
        content = "def bad():\n"
        for i in range(20):
            content += "    " * (i + 1) + f"if True: # {i}\n"
        content += "    " * 22 + "pass\n"

        with open("fail.py", "w") as f:
            f.write(content)

        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--verbosity", "summary"])
        assert "Environment Health" in result.output
        assert "File Analysis" in result.output
        assert "fail.py" in result.output
        # pass.py should be hidden because its score is 100 (>= 70)
        assert "pass.py" not in result.output


def test_verbosity_detailed():
    """Test detailed mode behavior."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("hello.py", "w") as f:
            f.write("def hello():\n    pass\n")
        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--verbosity", "detailed"])
        assert result.exit_code == 0
        assert "Environment Health" in result.output
        assert "File Analysis" in result.output
        assert "hello.py" in result.output


def test_verbosity_summary_hides_passing_files():
    """Verify that a file with a score of 85 (passing) is hidden in summary mode."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a file that will have score 85.
        # 1 red function = -15. 100 - 15 = 85.
        # Must have docstring and type hints to avoid other penalties.
        content = 'def high_acl() -> None:\n    """Docstring."""\n'
        for i in range(16):  # acl_red = 15.
            content += "    " * (i + 1) + f"if True: # {i}\n"
        content += "    " * 18 + "pass\n"

        with open("pass_85.py", "w") as f:
            f.write(content)

        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--verbosity", "summary"])
        # Score 85 is >= 70, so it should be hidden.
        assert "pass_85.py" not in result.output
        assert "Final Agent Score" in result.output


def test_report_verbosity_summary():
    """Verify that the generated report also respects verbosity summary."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("pass.py", "w") as f:
            f.write('def good() -> None:\n    """Docstring."""\n    pass\n')
        with open("fail.py", "w") as f:
            f.write("def bad():\n    pass\n")  # No docstring, no types -> score 65

        with open("README.md", "w") as f:
            f.write("# README")

        runner.invoke(
            cli, ["score", ".", "--verbosity", "summary", "--report", "report.md"]
        )

        with open("report.md", "r") as f:
            content = f.read()

        assert "fail.py" in content
        assert "pass.py" not in content
