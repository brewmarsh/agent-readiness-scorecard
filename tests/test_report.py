from agent_scorecard.report import (
    generate_markdown_report,
    generate_recommendations_report,
)
from agent_scorecard.constants import PROFILES


def test_generate_markdown_report() -> None:
    """
    Tests the Markdown report generation with new Agent Readiness metrics.

    Verifies that ACL violations, Type Safety Index, and remediation prompts
    are correctly formatted in the final output.

    Returns:
        None
    """
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

    # Execute report generation using the generic profile and sample project issues
    report_content = generate_markdown_report(
        stats=file_results,
        final_score=70.0,
        path=".",
        profile=PROFILES["generic"],
        project_issues=["Missing Critical Documentation: agents.md"],
    )

    # Core Content Verification
    assert "# Agent Scorecard Report" in report_content
    assert "Overall Score: 70.0/100" in report_content
    assert "PASSED" in report_content

    # Verify Agent Readiness Features (ACL & Type Safety)
    assert "Top Refactoring Targets (Agent Cognitive Load (ACL))" in report_content
    assert "complex_untyped" in report_content
    assert "25.0" in report_content
    assert "🔴 Red" in report_content

    assert "Type Safety Index" in report_content
    assert "Agent Prompts for Remediation" in report_content

    # Verify Project Issues reporting
    assert "Missing Critical Documentation" in report_content


def test_generate_recommendations_report() -> None:
    """
    Tests the recommendations report generation for systemic improvements.

    Ensures that technical debt findings are mapped to specific "Agent Impacts"
    to provide context for why fixes are necessary.

    Returns:
        None
    """
    # Define a results structure that triggers multiple recommendation types
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

    # Verify Finding/Recommendation pairs
    assert "High Complexity: heavy.py" in rec_content
    assert "Missing AGENTS.md" in rec_content
    assert "Circular Dependency: circular.py" in rec_content
    assert "Low Type Safety: untyped.py" in rec_content

    # Verify Agent Impact explanations
    assert "Context window overflow." in rec_content
    assert "Agent guesses repository structure." in rec_content
    assert "Recursive loops." in rec_content
    assert "Hallucination of signatures." in rec_content
