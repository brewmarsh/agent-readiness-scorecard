from pathlib import Path
from unittest.mock import patch
import textwrap
from click.testing import CliRunner
# RESOLUTION: Use 'src' prefix and import from 'analyzer' instead of deleted 'checks' module
from src.agent_scorecard.main import cli
from src.agent_scorecard.analyzer import check_type_hints

def test_async_function_support_checks(tmp_path: Path):
    """Test that check_type_hints correctly identifies async functions."""
    p = tmp_path / "async_test.py"
    p.write_text("""
async def fetch_data(url):
    return url
""")

    # Should find 1 function, 0 typed -> 0% coverage.
    # RESOLUTION: Updated function name from analyze_type_hints to check_type_hints
    cov = check_type_hints(str(p))
    assert cov == 0

def test_fix_async_function(tmp_path: Path):
    """Test that 'fix' command adds docstrings and type hints to async functions."""
    p = tmp_path / "async_fix.py"
    p.write_text("""
async def process_data(data):
    pass
""")

    runner = CliRunner()
    # Mock LLM.generate to return fixed code
    fixed_code = textwrap.dedent("""
        async def process_data(data: dict) -> None:
            \"\"\"Processes data async.\"\"\"
            pass
    """).strip()

    with patch("src.agent_scorecard.fix.LLM.generate", return_value=fixed_code):
        # Run 'fix' command
        result = runner.invoke(cli, ["fix", str(p)])
        assert result.exit_code == 0

    content = p.read_text()
    assert 'Processes data async.' in content
    assert 'data: dict' in content

def test_score_async_function(tmp_path: Path):
    """Test that 'score' command detects issues in async functions."""
    p = tmp_path / "async_score.py"
    p.write_text("""
async def process_data(data):
    pass
""")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(p), "--verbosity", "detailed"])

    # RESOLUTION: Updated assertion to match scoring.py output format
    assert "Type Safety Index 0%" in result.output
