import textwrap
from pathlib import Path
from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES
from agent_scorecard import analyzer


def test_bloated_files_penalty(tmp_path: Path) -> None:
    """
    Verify that files over 200 lines get a penalty.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    # Base 100 score. 310 lines - 200 = 110. 110 // 10 = 11 penalty points.
    content = "x = 1\n" * 310
    py_file = tmp_path / "bloated.py"
    py_file.write_text(content, encoding="utf-8")

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    assert loc == 310
    assert "Bloated File: 310 lines (-11)" in details
    assert score == 89  # Calculation: 100 - 11


def test_acl_strictness(tmp_path: Path) -> None:
    """
    Verify ACL thresholds: Red > 15, Yellow 10-15.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    # Formula: ACL = Cyclomatic Complexity + (Lines of Code / 20)
    # Target function: CC=1, LOC=300. ACL = 1 + (300 / 20) = 16.0 (Red status)
    content = textwrap.dedent("""
    def hall_func():
        pass
    """)
    # Append lines inside the function to reach 300 lines total
    for i in range(298):
        content += f"    x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    assert any(m["acl"] == 16.0 for m in metrics)
    assert "1 Red ACL functions (-15)" in details


def test_empty_directory(tmp_path: Path) -> None:
    """
    Verify handling of empty directories.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    results = analyzer.perform_analysis(str(empty_dir), "generic")
    assert results["file_results"] == []
    # If README is missing (project penalty -15), final_score reflects the 20% project weight.
    assert results["final_score"] < 100


def test_malformed_pyproject(tmp_path: Path) -> None:
    """
    Verify that malformed pyproject.toml is detected and penalized.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    bad_toml = "[[[ invalid toml"
    (tmp_path / "pyproject.toml").write_text(bad_toml, encoding="utf-8")
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def f(): pass", encoding="utf-8")

    results = analyzer.perform_analysis(str(tmp_path), "generic")
    assert "Malformed pyproject.toml detected" in results["project_issues"]
    # Final score handles both file results and weighted project penalties.
    assert results["final_score"] == 80.0


def test_missing_dependencies_parsing(tmp_path: Path) -> None:
    """
    Verify that imports are parsed via AST regardless of system installation.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    content = "import non_existent_package\nfrom another_one import something"
    py_file = tmp_path / "imports.py"
    py_file.write_text(content, encoding="utf-8")

    graph = analyzer.get_import_graph(str(tmp_path))
    assert "imports.py" in graph
    # RESOLUTION: Scanner finds imports via AST even if packages aren't installed.
    # This ensures the tool is environment-agnostic.
    assert len(graph) == 1