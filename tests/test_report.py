from agent_readiness_scorecard.report import (
    generate_markdown_report,
    generate_recommendations_report,
    _generate_acl_section,
)
from agent_readiness_scorecard.constants import PROFILES


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
    assert "# Agent Scorecard Report v" in report_content
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


def test_report_acl_success_message() -> None:
    """
    Tests that a success message is displayed when all functions meet ACL targets.
    """
    thresholds = {"acl_yellow": 10}
    stats = [
        {
            "file": "passing.py",
            "function_metrics": [{"name": "good", "acl": 5}],
        }
    ]

    report = _generate_acl_section(stats, thresholds)
    assert "✅ All functions meet the Agent Cognitive Load" in report
    assert "| Function | File | ACL | Status |" not in report


def test_report_sorting_and_limiting() -> None:
    """
    Tests that ACL section correctly sorts and limits functions.
    """
    stats = [
        {
            "file": "file.py",
            "function_metrics": [
                {"name": "fn1", "acl": 15, "loc": 10, "complexity": 5},
                {"name": "fn2", "acl": 12, "loc": 50, "complexity": 2},
                {"name": "fn3", "acl": 11, "loc": 5, "complexity": 10},
            ],
        }
    ]
    thresholds = {"acl_yellow": 10}

    # Test default sort (acl) and no limit
    report = _generate_acl_section(stats, thresholds)
    assert "fn1" in report
    assert "fn2" in report
    assert "fn3" in report
    # Sorting is descending, so fn1 (15) > fn2 (12) > fn3 (11)
    assert report.index("fn1") < report.index("fn2") < report.index("fn3")

    # Test limit
    report = _generate_acl_section(stats, thresholds, top_limit=2)
    assert "fn1" in report
    assert "fn2" in report
    assert "fn3" not in report

    # Test sort by loc
    report = _generate_acl_section(stats, thresholds, sort_by="loc")
    # fn2 (50) > fn1 (10) > fn3 (5)
    assert report.index("fn2") < report.index("fn1") < report.index("fn3")

    # Test sort by complexity
    report = _generate_acl_section(stats, thresholds, sort_by="complexity")
    # fn3 (10) > fn1 (5) > fn2 (2)
    assert report.index("fn3") < report.index("fn1") < report.index("fn2")
