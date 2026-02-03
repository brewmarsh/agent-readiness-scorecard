import pytest
from pathlib import Path
from src.agent_scorecard.report import generate_markdown_report
from src.agent_scorecard.constants import PROFILES

def test_generate_markdown_report():
    """Tests the Markdown report generation with new Agent Readiness metrics."""
    file_results = [
        {
            'file': 'file1.py',
            'score': 40,
            'issues': '1 Red ACL functions',
            'loc': 250,
            'complexity': 15,
            'type_coverage': 0,
            'function_metrics': [
                {'name': 'complex_untyped', 'acl': 25, 'complexity': 15, 'loc': 200, 'is_typed': False}
            ]
        },
        {
            'file': 'file2.py',
            'score': 100,
            'issues': '',
            'loc': 50,
            'complexity': 2,
            'type_coverage': 100,
            'function_metrics': [
                {'name': 'simple_typed', 'acl': 3, 'complexity': 2, 'loc': 20, 'is_typed': True}
            ]
        },
    ]

    results = {
        'final_score': 70.0,
        'file_results': file_results,
        'profile': PROFILES['generic'],
        'agent': 'generic',
        'missing_docs': ['agents.md']
    }

    report_content = generate_markdown_report(results)

    assert "# Agent Scorecard Report" in report_content
    assert "Final Score: 70.0/100" in report_content
    assert "PASSED" in report_content
    assert "Top Refactoring Targets (Agent Cognitive Load)" in report_content
    assert "complex_untyped" in report_content
    assert "25.0" in report_content
    assert "🔴 Red" in report_content
    assert "Type Safety Index" in report_content
    assert "Agent Prompts for Remediation" in report_content
    assert "Missing Critical Documentation" in report_content
    assert "agents.md" in report_content
