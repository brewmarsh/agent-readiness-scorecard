import pytest
from pathlib import Path
from agent_scorecard.report import generate_markdown_report, generate_recommendations_report
from agent_scorecard.constants import PROFILES

def test_generate_markdown_report(tmp_path: Path):
    """Tests the Markdown report generation."""
    # Create a dummy agents.md
    (tmp_path / "agents.md").write_text("dummy content")

    file_results = [
        {'file': 'file1.py', 'score': 40, 'issues': '...', 'loc': 250, 'complexity': 15, 'type_coverage': 40},
        {'file': 'file2.py', 'score': 90, 'issues': '...', 'loc': 100, 'complexity': 5, 'type_coverage': 90},
        {'file': 'file3.py', 'score': 100, 'issues': '...', 'loc': 50, 'complexity': 2, 'type_coverage': 100},
    ]

    results = {
        'final_score': 65.0,
        'file_results': file_results,
        'profile': PROFILES['generic'],
        'agent': 'generic',
        'missing_docs': []
    }

    report_content = generate_markdown_report(results)

    assert "# Agent Scorecard Report" in report_content
    assert "Final Score: 65.0/100" in report_content
    assert "FAILED" in report_content
    assert "Top Refactoring Targets" in report_content
    assert "file1.py" in report_content
    assert "Complexity" in report_content
    assert "Lines of Code" in report_content
    assert "Type Coverage" in report_content
    assert "Agent Prompts" in report_content

def test_generate_recommendations_report():
    """Tests the recommendations report generation."""
    results = {
        'file_results': [
            {'file': 'heavy.py', 'complexity': 25, 'type_coverage': 95, 'issues': ''},
            {'file': 'untyped.py', 'complexity': 5, 'type_coverage': 80, 'issues': ''},
            {'file': 'circular.py', 'complexity': 5, 'type_coverage': 100, 'issues': 'Circular dependency detected'},
        ],
        'missing_docs': ['agents.md']
    }

    rec_content = generate_recommendations_report(results)

    assert "High ACL in heavy.py" in rec_content
    assert "Missing AGENTS.md" in rec_content
    assert "Circular Dependency in circular.py" in rec_content
    assert "Type Coverage < 90% in untyped.py" in rec_content

    assert "Context window overflow." in rec_content
    assert "Agent guesses commands." in rec_content
    assert "Infinite recursion loops." in rec_content
    assert "Hallucination of signatures." in rec_content
