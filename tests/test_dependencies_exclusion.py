import os
from pathlib import Path
from agent_scorecard.dependencies import _scan_directory


def test_scan_directory_exclusions(tmp_path: Path) -> None:
    """
    Tests that _scan_directory excludes node_modules, venv, .venv, .git, and hidden directories.
    """
    # Create structure:
    # root/
    #   include.py
    #   node_modules/
    #     exclude_me.py
    #   venv/
    #     exclude_me_too.py
    #   .venv/
    #     me_neither.py
    #   .git/
    #     git_stuff.py
    #   .hidden/
    #     hidden.py
    #   subdir/
    #     include_also.py

    (tmp_path / "include.py").write_text("print('include')")

    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "exclude_me.py").write_text("print('exclude')")

    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "exclude_me_too.py").write_text("print('exclude')")

    dot_venv = tmp_path / ".venv"
    dot_venv.mkdir()
    (dot_venv / "me_neither.py").write_text("print('exclude')")

    git = tmp_path / ".git"
    git.mkdir()
    (git / "git_stuff.py").write_text("print('exclude')")

    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "hidden.py").write_text("print('exclude')")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "include_also.py").write_text("print('include')")

    files = _scan_directory(str(tmp_path))

    # Only include.py and subdir/include_also.py should be found
    assert len(files) == 2
    filenames = [os.path.basename(f) for f in files]
    assert "include.py" in filenames
    assert "include_also.py" in filenames

    # Ensure none of the excluded ones are there
    for f in files:
        assert "node_modules" not in f
        assert "venv" not in f
        assert ".git" not in f
        assert ".hidden" not in f
