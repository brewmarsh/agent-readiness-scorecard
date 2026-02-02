import pytest
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
