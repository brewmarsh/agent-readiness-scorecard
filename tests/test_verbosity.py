from click.testing import CliRunner
from agent_scorecard.main import cli


def test_verbosity_quiet() -> None:
    """
    Test quiet mode behavior (should only print score and critical issues).

    Returns:
        None
    """
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


def test_verbosity_summary() -> None:
    """
    Test summary mode behavior (default).

    Returns:
        None
    """
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


def test_verbosity_detailed() -> None:
    """
    Test detailed mode behavior.

    Returns:
        None
    """
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
