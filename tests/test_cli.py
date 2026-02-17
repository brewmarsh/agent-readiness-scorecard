import os
from click.testing import CliRunner
from agent_scorecard.main import cli


def test_cli_happy_path():
    """Test standard CLI execution (smoke test)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a dummy python file
        with open("hello.py", "w") as f:
            f.write("def hello():\n    print('hello')\n")

        # Create required files for generic profile (README.md)
        with open("README.md", "w") as f:
            f.write("# README")

        # cli is a group, so we need to invoke 'score'
        result = runner.invoke(cli, ["score", "."])
        assert result.exit_code == 0
        assert "Running Agent Scorecard" in result.output
        assert "Final Agent Score" in result.output


def test_cli_profiles_jules_fail_missing_agents_md():
    """Test jules profile fails if agents.md is missing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Directory is empty (no agents.md)
        result = runner.invoke(cli, ["score", ".", "--agent=jules"])

        # Should fail because missing agents.md and instructions.md
        assert result.exit_code == 1
        assert "Missing Critical Agent Docs" in result.output


def test_cli_fix_flag():
    """Test --fix flag behavior."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a blank python file
        with open("test.py", "w") as f:
            f.write("def test():\n    pass\n")

        # Run with --fix and jules profile to ensure agents.md is created
        runner.invoke(cli, ["score", ".", "--agent=jules", "--fix"])

        assert os.path.exists("agents.md")
        with open("agents.md", "r") as f:
            content = f.read()
            assert "Agent Context" in content

        assert os.path.exists("instructions.md")


def test_cli_badge_generation():
    """Test SVG badge generation."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a dummy python file
        with open("hello.py", "w") as f:
            f.write("def hello():\n    print('hello')\n")
        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["score", ".", "--badge"])
        assert result.exit_code == 0
        assert os.path.exists("agent_score.svg")
        assert "Badge saved" in result.output


def test_cli_advise_command():
    """Test advise command output."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create dummy python file
        with open("hello.py", "w") as f:
            f.write("def hello():\n    pass\n")
        with open("README.md", "w") as f:
            f.write("# README")

        # Run advise command with --output
        result = runner.invoke(cli, ["advise", ".", "--output", "report.md"])
        assert result.exit_code == 0
        assert os.path.exists("report.md")
        with open("report.md", "r", encoding="utf-8") as f:
            content = f.read()
            # RESOLUTION: Use Upgrade logic (Advisor Report header)
            assert "Agent Advisor Report" in content


def test_cli_check_prompts():
    """Test the Beta branch command for prompt best-practice analysis."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a perfect prompt file
        with open("prompt.txt", "w") as f:
            f.write("""
You are a helpful assistant.
Think step by step.
<input>
user input
</input>
Example:
Input: A
Output: B
            """)

        result = runner.invoke(cli, ["check-prompts", "prompt.txt"])
        assert result.exit_code == 0
        assert "Prompt Analysis: prompt.txt" in result.output
        assert "Role Definition" in result.output
        assert "Cognitive Scaffolding" in result.output
        assert "PASSED: Prompt is optimized!" in result.output
