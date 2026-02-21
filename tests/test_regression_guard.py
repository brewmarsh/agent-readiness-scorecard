import textwrap
from pathlib import Path
from agent_scorecard.scoring import score_file
from agent_scorecard.constants import PROFILES
from agent_scorecard import analyzer


def test_bloated_files_penalty(tmp_path: Path):
    """Verify that files over 200 lines get a penalty."""
    content = "x = 1\n" * 310  # 310 lines of code
    py_file = tmp_path / "bloated.py"
    py_file.write_text(content, encoding="utf-8")

    # 310 lines - 200 = 110. 110 // 10 = 11 penalty points.
    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    assert loc == 310
    assert "Bloated File: 310 lines (-11)" in details
    # Base 100 - 11 = 89
    assert score == 89


def test_acl_strictness(tmp_path: Path):
    """Verify ACL thresholds: Red > 15, Yellow 10-15."""
    # CC=1, LOC=300. ACL = 1 + 300/20 = 1 + 15 = 16.0 (Red)
    content = textwrap.dedent("""
    def hall_func():
        pass
    """)
    # Add 298 lines inside the function (plus def and pass makes 300)
    # Wait, def is 1, pass is 1. We need 298 more.
    for i in range(298):
        content += f"    x = {i}\n"

    py_file = tmp_path / "high_acl.py"
    py_file.write_text(content, encoding="utf-8")

    score, details, loc, avg_comp, type_cov, metrics = score_file(
        str(py_file), PROFILES["generic"]
    )

    # metrics[0] should be hall_func
    assert any(m["acl"] == 16.0 for m in metrics)
    assert "1 Red ACL functions (-15)" in details


def test_empty_directory(tmp_path: Path):
    """Verify handling of empty directories."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    results = analyzer.perform_analysis(str(empty_dir), "generic")
    assert results["file_results"] == []
    # Project issues might exist (missing docs) but final_score handles it.
    # Base score is 100 for project. File average is 0.
    # (0 * 0.8) + (project_score * 0.2)
    # If README is missing, project_score = 100 - 15 = 85.
    # final_score = 0 + 85 * 0.2 = 17.
    assert results["final_score"] < 100


def test_malformed_pyproject(tmp_path: Path):
    """Verify that malformed pyproject.toml is detected and results in a penalty."""
    bad_toml = "[[[ invalid toml"
    (tmp_path / "pyproject.toml").write_text(bad_toml, encoding="utf-8")
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def f(): pass", encoding="utf-8")

    results = analyzer.perform_analysis(str(tmp_path), "generic")
    assert "Malformed pyproject.toml detected" in results["project_issues"]
    # ok.py score: 80 (type penalty). project score: 80 (malformed penalty).
    # final: 80.0
    assert results["final_score"] == 80.0


def test_missing_dependencies_parsing(tmp_path: Path):
    """Verify that missing dependencies in imports don't crash the scanner."""
    content = "import non_existent_package\nfrom another_one import something"
    py_file = tmp_path / "imports.py"
    py_file.write_text(content, encoding="utf-8")

    graph = analyzer.get_import_graph(str(tmp_path))
    assert "imports.py" in graph
    # It should still parse the file even if packages are missing on system,
    # because it uses AST.
    assert len(graph) == 1
