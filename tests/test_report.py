import pytest
<<<<<<< HEAD
from src.agent_scorecard.report import generate_report
from src.agent_scorecard.constants import PROFILES

def test_generate_report():
    """Tests that generate_report produces correct markdown."""
    profile = PROFILES["generic"]

    file_results = [
        {"filepath": "bloated.py", "loc": 300, "complexity": 5, "type_coverage": 100, "score": 90},
        {"filepath": "complex.py", "loc": 50, "complexity": 15, "type_coverage": 100, "score": 90},
        {"filepath": "untyped.py", "loc": 50, "complexity": 5, "type_coverage": 20, "score": 80},
    ]

    missing_docs = ["agents.md"]
    project_score = 85.0

    report = generate_report(project_score, file_results, missing_docs, profile)

    # Check headers
    assert "# 🕵️ Agent Scorecard Report" in report
    assert "**Final Score:** 85.0/100" in report

    # Check Missing Docs section
    assert "### ❌ Missing Documentation" in report
    assert "- `root/agents.md`: Missing." in report

    # Check Bloated Files section
    assert "### 📉 Bloated Files (Too Large)" in report
    assert "- `bloated.py`: **300 lines**" in report

    # Check Complex Logic section
    assert "### 🌀 Complex Logic" in report
    assert "- `complex.py`: **15.0 avg complexity**" in report

    # Check Missing Types section
    assert "### ❓ Missing Type Hints" in report
    assert "- `untyped.py`: **20% covered**" in report

    # Check Recommendations
    assert "## 💡 Recommendations" in report

def test_generate_report_no_issues():
    """Tests report generation with a perfect project."""
    profile = PROFILES["generic"]
    report = generate_report(100.0, [], [], profile)

    assert "✅ No critical issues found! Your codebase is agent-ready." in report
    assert "### ❌ Missing Documentation" not in report
    assert "### 📉 Bloated Files" not in report
=======
from pathlib import Path
from src.agent_scorecard.report import generate_markdown_report
from src.agent_scorecard.main import PROFILES

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
>>>>>>> main
