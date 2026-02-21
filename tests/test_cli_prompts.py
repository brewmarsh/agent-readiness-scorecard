from unittest.mock import patch
from click.testing import CliRunner
from agent_scorecard.main import cli

def test_check_prompts_plain_output_fail() -> None:
    """Test check-prompts --plain output when score is low."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("prompt.txt", "w") as f:
            f.write("test prompt")

        mock_result = {
            "score": 50,
            "results": {"role_definition": False, "few_shot": True},
            "improvements": ["Add a role definition."]
        }

        with patch("agent_scorecard.main.PromptAnalyzer") as MockAnalyzer:
            instance = MockAnalyzer.return_value
            instance.analyze.return_value = mock_result

            result = runner.invoke(cli, ["check-prompts", "prompt.txt", "--plain"])

            assert result.exit_code == 1
            assert "Prompt Analysis: prompt.txt" in result.output
            assert "Score: 50/100\n" in result.output
            assert "Role Definition: FAIL" in result.output
            assert "Few Shot: PASS" in result.output
            assert "Refactored Suggestions:" in result.output
            assert "- Add a role definition." in result.output
            assert "FAILED: Prompt score too low." in result.output

def test_check_prompts_plain_output_pass() -> None:
    """Test check-prompts --plain output when score is high."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("prompt.txt", "w") as f:
            f.write("test prompt")

        mock_result = {
            "score": 90,
            "results": {"role_definition": True},
            "improvements": []
        }

        with patch("agent_scorecard.main.PromptAnalyzer") as MockAnalyzer:
            instance = MockAnalyzer.return_value
            instance.analyze.return_value = mock_result

            result = runner.invoke(cli, ["check-prompts", "prompt.txt", "--plain"])

            assert result.exit_code == 0
            assert "Score: 90/100\n" in result.output
            assert "Role Definition: PASS" in result.output
            assert "Refactored Suggestions:" not in result.output
            assert "PASSED: Prompt is optimized!" in result.output
