import os
from click.testing import CliRunner
from agent_scorecard.main import cli

def test_cli_happy_path():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a dummy python file
        with open("hello.py", "w") as f:
            f.write("def hello():\n    print('hello')\n")

        # Create required files for generic profile (README.md)
        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, ["."])
        assert result.exit_code == 0
        assert "Running Agent Scorecard" in result.output
        assert "Final Agent Score" in result.output

def test_cli_profiles_jules_fail_missing_agents_md():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Directory is empty (no agents.md)
        # We need a python file to trigger scoring, or let it fail due to no files and missing docs
        result = runner.invoke(cli, [".", "--agent=jules"])

        # Should fail because missing agents.md and instructions.md
        # And no python files means avg_file_score is 0.
        assert result.exit_code == 1
        assert "Missing Critical Agent Docs" in result.output

def test_cli_fix_flag():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a blank python file
        with open("test.py", "w") as f:
            f.write("def test():\n    pass\n")

        # Run with --fix and jules profile to ensure agents.md is created
        result = runner.invoke(cli, [".", "--agent=jules", "--fix"])
        # Exit code might be 0 or 1 depending on score, but we care about file creation

        assert os.path.exists("agents.md")
        with open("agents.md", "r") as f:
            content = f.read()
            assert "Agent Context" in content

        assert os.path.exists("instructions.md")

def test_cli_badge_generation():
    runner = CliRunner()
    with runner.isolated_filesystem():
         # Create a dummy python file
        with open("hello.py", "w") as f:
            f.write("def hello():\n    print('hello')\n")
        with open("README.md", "w") as f:
            f.write("# README")

        result = runner.invoke(cli, [".", "--badge"])
        assert result.exit_code == 0
        assert os.path.exists("agent_score.svg")
        assert "Badge saved" in result.output

def test_cli_advise_command():
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
        with open("report.md", "r") as f:
            content = f.read()
            assert "# 🧠 Agent Advisor Report" in content
