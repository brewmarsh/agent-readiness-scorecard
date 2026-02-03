import os
import tempfile
import pytest
from agent_scorecard import auditor

def test_check_directory_entropy():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a few folders and files
        os.makedirs(os.path.join(tmpdir, "folder1"))
        os.makedirs(os.path.join(tmpdir, "folder2"))

        for i in range(10):
            with open(os.path.join(tmpdir, "folder1", f"file{i}.txt"), "w") as f:
                f.write("test")

        for i in range(5):
            with open(os.path.join(tmpdir, "folder2", f"file{i}.txt"), "w") as f:
                f.write("test")

        # total folders: root + folder1 + folder2 = 3
        # total files: 10 + 5 = 15
        # avg = 15 / 3 = 5

        result = auditor.check_directory_entropy(tmpdir)
        assert result["avg_files"] == 5.0
        assert result["warning"] is False

def test_check_directory_entropy_warning():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(20):
            with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                f.write("test")

        # 1 folder, 20 files -> avg 20
        result = auditor.check_directory_entropy(tmpdir)
        assert result["avg_files"] == 20.0
        assert result["warning"] is True

def test_get_python_signatures():
    code = """
def func1(a: int) -> str:
    return str(a)

async def func2(b: float):
    pass

class MyClass:
    def method1(self):
        pass
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        sigs = auditor.get_python_signatures(tmp_path)
        assert "def func1(a: int) -> str:" in sigs
        assert "async def func2(b: float):" in sigs
        assert "class MyClass:" in sigs
        assert "def method1(self):" in sigs
    finally:
        os.remove(tmp_path)

def test_check_critical_context_tokens():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("Hello world")

        with open(os.path.join(tmpdir, "test.py"), "w") as f:
            f.write("def foo(): pass")

        result = auditor.check_critical_context_tokens(tmpdir)
        assert result["token_count"] > 0
        assert result["alert"] is False

def test_check_environment_health():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initial: everything False
        res = auditor.check_environment_health(tmpdir)
        assert res["agents_md"] is False
        assert res["linter_config"] is False
        assert res["lock_file"] is False

        # Add AGENTS.md
        with open(os.path.join(tmpdir, "AGENTS.md"), "w") as f: f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["agents_md"] is True

        # Add Linter
        with open(os.path.join(tmpdir, "ruff.toml"), "w") as f: f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["linter_config"] is True

        # Add Lock file
        with open(os.path.join(tmpdir, "poetry.lock"), "w") as f: f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["lock_file"] is True

def test_check_environment_health_pyproject_ruff():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
            f.write("[tool.ruff]\nline-length = 88")
        res = auditor.check_environment_health(tmpdir)
        assert res["linter_config"] is True
