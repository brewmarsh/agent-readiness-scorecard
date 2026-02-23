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
    Verify ACL thresholds using the high-fidelity formula.
    Red > 15, Yellow 10-15.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    # RESOLUTION: Adopted New Formula: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)
    # Target function: Depth=3, CC=4, LOC=200.
    # Math: (3*2) + (4*1.5) + (200/50) = 6 + 6 + 4 = 16.0 (Red status)

    content = textwrap.dedent("""
    def hall_func():
        if True:
            if True:
                if True:
                    pass
    """)
    # Logic: Function already has 5 lines. Add 195 lines to reach 200 total inside function.
    for i in range(195):
        content += f"                x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    # Validate that the AST-based depth analysis resulted in the specific 16.0 score
    assert any(m["acl"] == 16.0 for m in metrics)
    assert "1 Red ACL functions (-15)" in details


def test_empty_directory(tmp_path: Path) -> None:
    """
    Verify handling of empty directories.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    results = analyzer.perform_analysis(str(empty_dir), "generic")
    assert results["file_results"] == []
    # Project penalty applied due to missing README.md/AGENTS.md
    assert results["final_score"] < 100


def test_malformed_pyproject(tmp_path: Path) -> None:
    """
    Verify that malformed pyproject.toml is detected and penalized.
    """
    bad_toml = "[[[ invalid toml"
    (tmp_path / "pyproject.toml").write_text(bad_toml, encoding="utf-8")
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def f(): pass", encoding="utf-8")

    results = analyzer.perform_analysis(str(tmp_path), "generic")
    assert "Malformed pyproject.toml detected" in results["project_issues"]
    assert results["final_score"] == 80.0


def test_missing_dependencies_parsing(tmp_path: Path) -> None:
    """
    Verify that imports are parsed via AST regardless of system installation.
    """
    content = "import non_existent_package\nfrom another_one import something"
    py_file = tmp_path / "imports.py"
    py_file.write_text(content, encoding="utf-8")

    graph, _ = analyzer.get_import_graph(str(tmp_path))
    assert "imports.py" in graph
    # Scanner finds imports via AST even if packages aren't installed.
    assert len(graph) == 1
