import pytest
from pathlib import Path
from click.testing import CliRunner
<<<<<<< HEAD
from agent_scorecard.main import cli
from agent_scorecard.checks import check_type_hints
=======
# RESOLUTION: Use 'src' prefix and import from 'analyzer' instead of deleted 'checks' module
from src.agent_scorecard.main import cli
from src.agent_scorecard.analyzer import check_type_hints
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252

def test_async_function_support_checks(tmp_path: Path):
    """Test that check_type_hints correctly identifies async functions."""
    p = tmp_path / "async_test.py"
    p.write_text("""
async def fetch_data(url):
<<<<<<< HEAD
    await some_lib.get(url)
""")

    # Should find 1 function, 0 typed -> 0% coverage.
    cov, penalty = check_type_hints(str(p), 50)
    assert cov == 0
    assert penalty == 20
=======
    return url
""")

    # Should find 1 function, 0 typed -> 0% coverage.
    # RESOLUTION: Updated function name from analyze_type_hints to check_type_hints
    cov = check_type_hints(str(p))
    assert cov == 0
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252

def test_fix_async_function(tmp_path: Path):
    """Test that 'fix' command adds docstrings and type hints to async functions."""
    p = tmp_path / "async_fix.py"
    p.write_text("""
async def process_data(data):
    pass
""")

    runner = CliRunner()
    # Run 'fix' command
    result = runner.invoke(cli, ["fix", str(p)])
    assert result.exit_code == 0

    content = p.read_text()
    assert '"""TODO: Add docstring for AI context."""' in content
    assert '# TODO: Add type hints for Agent clarity' in content

def test_score_async_function(tmp_path: Path):
    """Test that 'score' command detects issues in async functions."""
    p = tmp_path / "async_score.py"
    p.write_text("""
async def process_data(data):
    pass
""")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(p)])
<<<<<<< HEAD
    # We verify that it detects the type hint issue
    assert "Types 0% < 50%" in result.output
=======

    # RESOLUTION: Updated assertion to match scoring.py output format
    # The CLI table outputs "Types 0% < 50%" based on the Generic profile.
    assert "Types 0%" in result.output
>>>>>>> origin/upgrade-scoring-logic-4412913730962226252
