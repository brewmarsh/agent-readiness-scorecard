import os
import textwrap
import pytest
from unittest.mock import patch
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
                f.write(textwrap.dedent("""
                    def foo():
                        pass
                """))

            # Mock LLM.generate to return fixed code
            fixed_code = textwrap.dedent("""
                def foo() -> None:
                    \"\"\"A docstring.\"\"\"
                    pass
            """).strip()

            with patch("src.agent_scorecard.fix.LLM.generate", return_value=fixed_code) as mock_gen:
                # Run fix command with default agent (generic)
                result = runner.invoke(cli, ["fix", "."])

                assert result.exit_code == 0
                assert "Applying Fixes" in result.output
                assert "Fixes applied!" in result.output

                # Verify LLM was called with CRAFT prompt
                system_prompt, user_prompt = mock_gen.call_args[0]
                assert "Elite DevOps Engineer" in system_prompt
                assert "ACL > 15 or Missing Types" in user_prompt

            # Check if README.md was created (required by generic)
            assert os.path.exists("README.md")

            # Check if python file was modified
            with open("src/test.py", "r") as f:
                content = f.read()
            assert "A docstring." in content
            assert "-> None" in content

    def test_fix_command_specific_path(self, runner):
        with runner.isolated_filesystem():
             # Create a dummy python file in a subdirectory
            os.makedirs("subdir")
            with open("subdir/test.py", "w") as f:
                f.write(textwrap.dedent("""
                    def bar(x):
                        return x
                """))

            fixed_code = textwrap.dedent("""
                def bar(x: int) -> int:
                    \"\"\"Returns x.\"\"\"
                    return x
            """).strip()

            with patch("src.agent_scorecard.fix.LLM.generate", return_value=fixed_code):
                # Run fix command on subdir with jules agent (requires agents.md)
                result = runner.invoke(cli, ["fix", "subdir", "--agent", "jules"])

            assert result.exit_code == 0
            # Should create docs in subdir because apply_fixes creates docs in the given path if it's a directory
            assert os.path.exists("subdir/agents.md")
            assert os.path.exists("subdir/instructions.md")

            with open("subdir/test.py", "r") as f:
                content = f.read()
            assert "Returns x." in content
            assert "x: int" in content

    def test_fix_command_invalid_agent(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["fix", ".", "--agent", "invalid"])
            assert result.exit_code == 0 # It defaults to generic, so exit code 0
            assert "Unknown agent profile: invalid. using generic." in result.output
