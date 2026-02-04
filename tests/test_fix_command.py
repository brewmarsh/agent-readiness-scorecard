import os
import textwrap
import pytest
from click.testing import CliRunner
from src.agent_scorecard.main import cli


class TestFixCommand:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_fix_command_happy_path(self, runner):
        with runner.isolated_filesystem():
            # Create a dummy python file
            os.makedirs("src")
            with open("src/test.py", "w") as f:
                f.write(
                    textwrap.dedent("""
                    def foo():
                        pass
                """)
                )

            # Run fix command with default agent (generic)
            result = runner.invoke(cli, ["fix", "."])

            assert result.exit_code == 0
            assert "Applying Fixes" in result.output
            assert "Fixes applied!" in result.output

            # Check if README.md was created (required by generic)
            assert os.path.exists("README.md")

            # Check if python file was modified
            with open("src/test.py", "r") as f:
                content = f.read()
            assert "TODO: Add docstring" in content
            # Note: The exact string depends on constants, but checking for substring is robust enough.
            assert "TODO: Add type hints" in content

    def test_fix_command_specific_path(self, runner):
        with runner.isolated_filesystem():
            # Create a dummy python file in a subdirectory
            os.makedirs("subdir")
            with open("subdir/test.py", "w") as f:
                f.write(
                    textwrap.dedent("""
                    def bar(x):
                        return x
                """)
                )

            # Run fix command on subdir with jules agent (requires agents.md)
            result = runner.invoke(cli, ["fix", "subdir", "--agent", "jules"])

            assert result.exit_code == 0
            # Should create docs in subdir because apply_fixes creates docs in the given path if it's a directory
            assert os.path.exists("subdir/agents.md")
            assert os.path.exists("subdir/instructions.md")

            with open("subdir/test.py", "r") as f:
                content = f.read()
            assert "TODO: Add docstring" in content

    def test_fix_command_invalid_agent(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["fix", ".", "--agent", "invalid"])
            assert result.exit_code == 0  # It defaults to generic, so exit code 0
            assert "Unknown agent profile: invalid. using generic." in result.output
