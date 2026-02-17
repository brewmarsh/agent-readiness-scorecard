from pathlib import Path
from unittest.mock import patch
import textwrap
from click.testing import CliRunner
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
    
    # RESOLUTION: Use mocking to simulate the LLM refactoring the code
    fixed_code = textwrap.dedent("""
        async def process_data(data: dict) -> None:
            \"\"\"Processes data async.\"\"\"
            pass
    """).strip()

    # Mocking the LLM ensures tests run locally without network access
    with patch("src.agent_scorecard.fix.LLM.generate", return_value=fixed_code):
        # We invoke the standalone 'fix' command established in the Beta branch
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
    # Ensure we test the detailed output to find the specific index string
    result = runner.invoke(cli, ["score", str(p), "--verbosity", "detailed"])

    assert "Type Safety Index 0%" in result.output