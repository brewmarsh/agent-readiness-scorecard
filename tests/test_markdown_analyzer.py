from pathlib import Path
from agent_readiness_scorecard.analyzers.markdown import MarkdownAnalyzer
from agent_readiness_scorecard.constants import PROFILES


def test_markdown_analyzer_get_stats(tmp_path: Path) -> None:
    """
    Test that MarkdownAnalyzer correctly parses headers and calculates ACL.
    """
    md_content = """# Title
Some introduction text that should have some tokens.

## Section 1
This is a section with some content.
It spans multiple lines.

### Subsection 1.1
Short section.
"""
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content, encoding="utf-8")

    analyzer = MarkdownAnalyzer()
    stats = analyzer.get_function_stats(str(md_file))

    assert len(stats) == 3

    # Title section
    assert stats[0]["name"] == "# Title"
    assert stats[0]["nesting_depth"] == 1
    assert stats[0]["lineno"] == 1

    # Section 1
    assert stats[1]["name"] == "## Section 1"
    assert stats[1]["nesting_depth"] == 2
    assert stats[1]["lineno"] == 4

    # Subsection 1.1
    assert stats[2]["name"] == "### Subsection 1.1"
    assert stats[2]["nesting_depth"] == 3
    assert stats[2]["lineno"] == 8

    # Check ACL calculation for one section
    # ACL = (depth * 1.5) + (tokens / 100)
    # We don't know exact tokens without tiktoken encoding, but we can verify it's a float
    assert isinstance(stats[0]["acl"], float)
    assert stats[0]["acl"] > 1.5  # 1 * 1.5 + tokens/100


def test_markdown_analyzer_score_file(tmp_path: Path) -> None:
    """
    Test that MarkdownAnalyzer correctly scores a file and identifies issues.
    """
    # Create a markdown file with a very long section to trigger high ACL
    long_content = "Word " * 2000  # ~2000 tokens
    md_content = f"""# Huge Section
{long_content}
"""
    md_file = tmp_path / "long.md"
    md_file.write_text(md_content, encoding="utf-8")

    analyzer = MarkdownAnalyzer()
    score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
        str(md_file), PROFILES["generic"]
    )

    assert score < 100
    assert "Red ACL sections detected" in issues
    assert type_safety == 100.0


def test_markdown_analyzer_bloat_penalty(tmp_path: Path) -> None:
    """
    Test that MarkdownAnalyzer penalizes bloated files (> 500 lines).
    """
    md_content = "content\n" * 600
    md_file = tmp_path / "bloated.md"
    md_file.write_text(md_content, encoding="utf-8")

    analyzer = MarkdownAnalyzer()
    score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
        str(md_file), PROFILES["generic"]
    )

    assert score < 100
    assert "Bloated Documentation" in issues
