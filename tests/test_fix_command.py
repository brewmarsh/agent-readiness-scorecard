import os
import textwrap
import pytest
from unittest.mock import patch
from click.testing import CliRunner
from agent_scorecard.main import cli


class TestFixCommand:
    @pytest.fixture
    def runner(self) -> CliRunner:
        """
        Pytest fixture for CliRunner.

        Returns:
            CliRunner: The CLI runner instance.
        """
        return CliRunner()

    def test_fix_command_happy_path(self, runner: CliRunner) -> None:
        """
        Test the standalone fix command using the generic profile.

        Args:
            runner (CliRunner): The CLI runner instance.

        Returns:
            None
        """
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

            # RESOLUTION: Mock LLM.generate to simulate CRAFT refactoring
            fixed_code = textwrap.dedent("""
                def foo() -> None:
                    \"\"\"A docstring.\"\"\"
                    pass
            """).strip()

            with patch(
                "agent_scorecard.fix.LLM.generate", return_value=fixed_code
            ) as mock_gen:
                # Invoke dedicated 'fix' command
                result = runner.invoke(cli, ["fix", "."])

                assert result.exit_code == 0
                assert "Applying Fixes" in result.output
                assert "Fixes applied!" in result.output

                # Verify LLM was called with the CRAFT persona defined in the refactor
                system_prompt, user_prompt = mock_gen.call_args[0]
                assert "Elite DevOps Engineer" in system_prompt
                assert "ACL > 15 or Missing Types" in user_prompt

            # Check if required docs for generic profile were created
            assert os.path.exists("README.md")

            # Verify file contents were actually overwritten with fixed code
            with open("src/test.py", "r") as f:
                content = f.read()
            assert "A docstring." in content
            assert "-> None" in content

    def test_fix_command_specific_path(self, runner: CliRunner) -> None:
        """
        Test fix command on a subdirectory with a specific agent profile.

        Args:
            runner (CliRunner): The CLI runner instance.

        Returns:
            None
        """
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

            fixed_code = textwrap.dedent("""
                def bar(x: int) -> int:
                    \"\"\"Returns x.\"\"\"
                    return x
            """).strip()

            with patch("agent_scorecard.fix.LLM.generate", return_value=fixed_code):
                # Run fix command on subdir with jules agent (requires agents.md)
                result = runner.invoke(cli, ["fix", "subdir", "--agent", "jules"])

            assert result.exit_code == 0
            # verify path-specific document creation
            assert os.path.exists("subdir/agents.md")
            assert os.path.exists("subdir/instructions.md")

            with open("subdir/test.py", "r") as f:
                content = f.read()
            assert "Returns x." in content
            assert "x: int" in content

    def test_fix_flag_in_score_command(self, runner: CliRunner) -> None:
        """
        Regression test for the --fix flag inside the score command.

        Args:
            runner (CliRunner): The CLI runner instance.

        Returns:
            None
        """
        with runner.isolated_filesystem():
            with open("test.py", "w") as f:
                f.write("def foo():\n    pass\n")

            # Create README.md to satisfy profile
            with open("README.md", "w") as f:
                f.write("# Project")

            fixed_code = 'def foo() -> None:\n    """Doc."""\n    pass'

            with patch("agent_scorecard.fix.LLM.generate", return_value=fixed_code):
                # Using the old --fix flag style
                result = runner.invoke(cli, ["score", ".", "--fix"])
                assert result.exit_code == 0
                assert "Applying Fixes" in result.output

    def test_fix_command_invalid_agent(self, runner: CliRunner) -> None:
        """
        Verify fallback to generic profile when an invalid agent is provided.

        Args:
            runner (CliRunner): The CLI runner instance.

        Returns:
            None
        """
        with runner.isolated_filesystem():
            with open("test.py", "w") as f:
                f.write("def foo():\n    pass\n")

            # Should default to generic and not crash
            result = runner.invoke(cli, ["score", ".", "--fix", "--agent", "invalid"])
            assert result.exit_code == 0
            assert "Unknown agent profile: invalid. using generic." in result.output