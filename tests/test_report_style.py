from agent_scorecard.report import generate_markdown_report


def test_report_style_full() -> None:
    """Test the 'full' report style includes all sections."""
    stats = [
        {
            "file": "test.py",
            "score": 100,
            "issues": "",
            "loc": 10,
            "complexity": 1.0,
            "type_coverage": 100.0,
            "function_metrics": [],
            "tokens": 10,
            "cumulative_tokens": 10,
            "acl": 0.0,
        }
    ]
    report = generate_markdown_report(
        stats=stats,
        final_score=100.0,
        path=".",
        profile={"description": "Test Profile"},
        report_style="full",
    )
    assert "Full File Analysis" in report
    assert "Type Safety Index" in report
    assert "test.py" in report


def test_report_style_actionable_failing() -> None:
    """Test the 'actionable' report style shows failing files."""
    stats = [
        {
            "file": "fail.py",
            "score": 60,
            "issues": "Low score",
            "loc": 10,
            "complexity": 1.0,
            "type_coverage": 50.0,
            "function_metrics": [],
            "tokens": 10,
            "cumulative_tokens": 10,
            "acl": 0.0,
        },
        {
            "file": "pass.py",
            "score": 100,
            "issues": "",
            "loc": 10,
            "complexity": 1.0,
            "type_coverage": 100.0,
            "function_metrics": [],
            "tokens": 10,
            "cumulative_tokens": 10,
            "acl": 0.0,
        },
    ]
    report = generate_markdown_report(
        stats=stats,
        final_score=80.0,
        path=".",
        profile={"description": "Test Profile"},
        report_style="actionable",
    )
    assert "Failing File Analysis" in report
    assert "fail.py" in report
    assert "pass.py" not in report
    assert "50%" in report  # failing type safety
    assert "100%" not in report  # passing type safety


def test_report_style_collapsed() -> None:
    """Test the 'collapsed' report style only shows summary."""
    stats = [{"file": "test.py", "score": 100}]
    report = generate_markdown_report(
        stats=stats,
        final_score=100.0,
        path=".",
        profile={"description": "Test Profile"},
        report_style="collapsed",
    )
    assert "Overall Score: 100.0/100" in report
    assert "File Analysis" not in report
    assert "Type Safety Index" not in report
