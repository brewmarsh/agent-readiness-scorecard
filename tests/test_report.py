import pytest
from pathlib import Path
from src.agent_scorecard.report import generate_markdown_report
from src.agent_scorecard.main import PROFILES

def test_generate_markdown_report(tmp_path: Path):
    """Tests the Markdown report generation."""
    # Create a dummy agents.md
    (tmp_path / "agents.md").write_text("dummy content")

    stats = [
        {'file': 'file1.py', 'loc': 250, 'complexity': 15, 'type_coverage': 40},
        {'file': 'file2.py', 'loc': 100, 'complexity': 5, 'type_coverage': 90},
        {'file': 'file3.py', 'loc': 50, 'complexity': 2, 'type_coverage': 100},
    ]

    report = generate_markdown_report(stats, 65.0, str(tmp_path), PROFILES['generic'])

    assert "# Agent Scorecard Report" in report
    assert "Overall Score: 65.0/100" in report
    assert "FAIL" in report
    assert "Top Refactoring Targets" in report
    assert "file1.py" in report
    assert "Complexity" in report
    assert "Lines of Code" in report
    assert "Type Coverage" in report
    assert "Agent Prompts" in report
    assert "✅ `agents.md` found." in report
