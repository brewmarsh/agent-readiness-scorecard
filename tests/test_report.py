import pytest
from pathlib import Path
from src.agent_scorecard.report import generate_markdown_report
from src.agent_scorecard.constants import PROFILES

def test_generate_markdown_report(tmp_path: Path):
    """Tests the Markdown report generation."""
    # Create a dummy agents.md
    (tmp_path / "agents.md").write_text("dummy content")

    results = {
        'final_score': 65.0,
        'file_results': [
            {'file': 'file1.py', 'score': 40, 'issues': '...', 'loc': 250, 'complexity': 15, 'type_coverage': 40},
            {'file': 'file2.py', 'score': 90, 'issues': '...', 'loc': 100, 'complexity': 5, 'type_coverage': 90},
            {'file': 'file3.py', 'score': 100, 'issues': '...', 'loc': 50, 'complexity': 2, 'type_coverage': 100},
        ],
        'profile': PROFILES['generic'],
        'agent': 'generic',
        'missing_docs': []
    }

    report = generate_markdown_report(results)
    assert "# Agent Scorecard Report" in report
    assert "Final Score: 65.0/100" in report
