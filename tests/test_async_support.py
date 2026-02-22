from pathlib import Path
from unittest.mock import patch
import textwrap
from click.testing import CliRunner
from agent_scorecard.main import cli
from agent_scorecard.analyzer import check_type_hints


def test_async_function_support_checks(tmp_path: Path) -> None:
    """
    Test that check_type_hints correctly identifies async functions.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    p = tmp_path / "async_test.py"
    p.write_text("""
async def fetch_data(url):
    return url
""")

    # Should find 1 function, 0 typed -> 0% coverage.
    cov = check_type_hints(str(p))
    assert cov == 0


def test_fix_async_function(tmp_path: Path) -> None:
    """
    Test that 'fix' command adds docstrings and type hints to async functions.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    p = tmp_path / "async_fix.py"
    p.write_text("""
async def process_data(data):
    pass
""")

    runner = CliRunner()

    # RESOLUTION: Use mocking to simulate the LLM refactoring the code
    fixed_code = textwrap.dedent("""
        async def process_data(data: dict) -> None:
            \"\"\"Processes data async.\"\"\"
            pass
    """).strip()

    # Mocking the LLM ensures tests run locally without network access
    with patch("agent_scorecard.fix.LLM.generate", return_value=fixed_code):
        # We invoke the standalone 'fix' command established in the Beta branch
        result = runner.invoke(cli, ["fix", str(p)])
        assert result.exit_code == 0

    content = p.read_text()
    assert "Processes data async." in content
    assert "data: dict" in content


def test_score_async_function(tmp_path: Path) -> None:
    """
    Test that 'score' command detects issues in async functions.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    p = tmp_path / "async_score.py"
    p.write_text("""
async def process_data(data):
    pass
""")
    # RESOLUTION: Ensure README.md exists to prevent project-level failures
    # during the file scoring integration test.
    (tmp_path / "README.md").write_text("# Project")

    runner = CliRunner()

    # Resolution: Test the detailed output to find the specific index string
    # as established in the configuration-heavy Beta branch.
    result = runner.invoke(cli, ["score", str(p), "--verbosity", "detailed"])

    assert result.exit_code == 0
    assert "Type Safety Index 0%" in result.output


def test_cli_check_prompts_async_context_plain() -> None:
    """
    Verify check-prompts --plain handles async context suggestions correctly.

    Returns:
        None
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("async_prompt.txt", "w") as f:
            f.write("Write an async function.")

        # RESOLUTION: Asserting exact strings required for the new GitHub Action regex
        result = runner.invoke(cli, ["check-prompts", "async_prompt.txt", "--plain"])
        assert "Refactored Suggestions:" in result.output
        assert "FAILED: Prompt score too low." in result.output
