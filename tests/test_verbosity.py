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

        # In quiet mode, we suppress metadata and headers
        result = runner.invoke(cli, ["score", ".", "--verbosity", "quiet"])
        
        assert result.exit_code == 0
        # Verify that Rich-enhanced components are suppressed
        assert "Environment Health" not in result.output
        assert "File Analysis" not in result.output
        assert "Running Agent Scorecard" not in result.output
        
        # Only the core outcome should be visible
        assert "Final Agent Score" in result.output


def test_verbosity_summary() -> None:
    """
    Test summary mode behavior (default). 
    Passing files (score 100) should be hidden to reduce noise.

    Returns:
        None
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Case A: One passing file (score 100)
        with open("pass.py", "w") as f:
            f.write('def good() -> None:\n    """Docstring."""\n    pass\n')

        # Case B: One failing file (score < 70)
        # Deeply nested logic ensures high complexity penalty
        content = "def bad():\n"
        for i in range(20):
            content += "    " * (i + 1) + f"if True: # {i}\n"
        content += "    " * 22 + "pass\n"

        with open("fail.py", "w") as f:
            f.write(content)

        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--verbosity", "summary"])
        
        # Environmental and File tables should be visible
        assert "Environment Health" in result.output
        assert "File Analysis" in result.output
        
        # fail.py must be present as it requires action
        assert "fail.py" in result.output
        
        # RESOLUTION: pass.py should be hidden in summary mode to satisfy Cisco Meraki scanability guidelines
        assert "pass.py" not in result.output


def test_verbosity_detailed() -> None:
    """
    Test detailed mode behavior. 
    All files and metadata should be visible regardless of score.

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
        # In detailed mode, even simple passing files are listed
        assert "hello.py" in result.output