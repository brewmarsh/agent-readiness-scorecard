from agent_scorecard.report import (
    generate_markdown_report,
    generate_recommendations_report,
)
from agent_scorecard.constants import PROFILES


def test_generate_markdown_report():
    """Tests the Markdown report generation with new Agent Readiness metrics."""
    file_results = [
        {
            "file": "file1.py",
            "score": 40,
            "issues": "1 Red ACL functions",
            "loc": 250,
            "complexity": 15,
            "type_coverage": 0,
            "function_metrics": [
                {
                    "name": "complex_untyped",
                    "acl": 25,
                    "complexity": 15,
                    "loc": 200,
                    "is_typed": False,
                }
            ],
        },
        {
            "file": "file2.py",
            "score": 100,
            "issues": "",
            "loc": 50,
            "complexity": 2,
            "type_coverage": 100,
            "function_metrics": [
                {
                    "name": "simple_typed",
                    "acl": 3,
                    "complexity": 2,
                    "loc": 20,
                    "is_typed": True,
                }
            ],
        },
    ]

    # generate_markdown_report(stats, final_score, path, profile, project_issues)
    report_content = generate_markdown_report(
        stats=file_results,
        final_score=70.0,
        path=".",
        profile=PROFILES["generic"],
        project_issues=["Missing Critical Documentation: agents.md"],
    )

    assert "# Agent Scorecard Report" in report_content
    assert "Overall Score: 70.0/100" in report_content
    assert "PASSED" in report_content

    # Verify Upgrade Branch Features (ACL & Type Safety)
    assert "Top Refactoring Targets (Agent Cognitive Load (ACL))" in report_content

    assert "complex_untyped" in report_content
    assert "25.0" in report_content
    assert "🔴 Red" in report_content

    # Regression check: Verify that ACL 16 is now reported as Red (previously it would have been Yellow due to 20 threshold)
    report_with_16 = generate_markdown_report(
        stats=[
            {
                "file": "borderline.py",
                "score": 50,
                "issues": "1 Red ACL functions",
                "loc": 100,
                "complexity": 11,
                "type_coverage": 100,
                "function_metrics": [
                    {
                        "name": "f",
                        "acl": 16.0,
                        "complexity": 11,
                        "loc": 100,
                        "is_typed": True,
                        "has_docstring": True,
                    }
                ],
            }
        ],
        final_score=50.0,
        path=".",
        profile=PROFILES["generic"],
    )
    assert "16.0" in report_with_16
    assert "🔴 Red" in report_with_16

    assert "Type Safety Index" in report_content
    assert "Agent Prompts for Remediation" in report_content

    # Verify Project Issues
    assert (
        "Missing Critical Documentation" in report_content
    )  # From project_issues text passed in


def test_generate_recommendations_report():
    """Tests the recommendations report generation."""
    # This matches the structure expected by generate_recommendations_report
    results = {
        "file_results": [
            {"file": "heavy.py", "complexity": 25, "type_coverage": 95, "issues": ""},
            {"file": "untyped.py", "complexity": 5, "type_coverage": 80, "issues": ""},
            {
                "file": "circular.py",
                "complexity": 5,
                "type_coverage": 100,
                "issues": "Circular dependency detected",
            },
        ],
        "missing_docs": ["agents.md"],
    }

    rec_content = generate_recommendations_report(results)

    assert "High Complexity: heavy.py" in rec_content
    assert "Missing AGENTS.md" in rec_content
    assert "Circular Dependency: circular.py" in rec_content
    assert "Low Type Safety: untyped.py" in rec_content

    assert "Context window overflow." in rec_content
    assert "Agent guesses repository structure." in rec_content
    assert "Recursive loops." in rec_content
    assert "Hallucination of signatures." in rec_content
