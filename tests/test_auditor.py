import os
import tempfile
from agent_scorecard import auditor


def test_check_directory_entropy() -> None:
    """
    Tests the directory entropy calculation and warning status under normal conditions.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a few folders and files to simulate a balanced structure
        os.makedirs(os.path.join(tmpdir, "folder1"))
        os.makedirs(os.path.join(tmpdir, "folder2"))

        for i in range(10):
            with open(os.path.join(tmpdir, "folder1", f"file{i}.txt"), "w") as f:
                f.write("test")

        for i in range(5):
            with open(os.path.join(tmpdir, "folder2", f"file{i}.txt"), "w") as f:
                f.write("test")

        # Math: total folders (3) / total files (15) = 5.0 avg
        result = auditor.check_directory_entropy(tmpdir)
        assert result["avg_files"] == 5.0
        assert result["warning"] is False


def test_check_directory_entropy_warning() -> None:
    """
    Tests that a high average file count across the project triggers an entropy warning.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(20):
            with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                f.write("test")

        # Math: 1 folder, 20 files -> avg 20.0 (triggers threshold)
        result = auditor.check_directory_entropy(tmpdir)
        assert result["avg_files"] == 20.0
        assert result["warning"] is True


def test_check_directory_entropy_max_files() -> None:
    """
    Tests that a high file count in a single "God Directory" triggers an entropy warning 
    even if the global average is diluted by empty folders.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a "God Directory" with 60 files to trigger max_files alert
        god_dir = os.path.join(tmpdir, "god_dir")
        os.makedirs(god_dir)
        for i in range(60):
            with open(os.path.join(god_dir, f"file{i}.txt"), "w") as f:
                f.write(".")

        # Create 10 empty folders to dilute the average
        for i in range(10):
            os.makedirs(os.path.join(tmpdir, f"empty{i}"))

        result = auditor.check_directory_entropy(tmpdir)
        # Avg = 60 files / 12 folders = 5.0, but Warning should be True due to spike
        assert result["avg_files"] == 5.0
        assert result["warning"] is True
        assert result["max_files"] == 60
        assert god_dir in result["crowded_dirs"]


def test_get_python_signatures() -> None:
    """
    Tests extraction of Python function and class signatures for agent context.

    Returns:
        None
    """
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
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_get_python_signatures_with_decorators() -> None:
    """
    Tests extraction of Python signatures that include decorators.

    Returns:
        None
    """
    code = """
@deco1
@deco2(x=1)
def decorated_func(a, b):
    pass

class DecoratedClass:
    @property
    def my_prop(self):
        return 1
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        sigs = auditor.get_python_signatures(tmp_path)
        assert "@deco1" in sigs
        assert "@deco2(x=1)" in sigs
        assert "def decorated_func(a, b):" in sigs
        assert "class DecoratedClass:" in sigs
        assert "@property" in sigs
        assert "def my_prop(self):" in sigs
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_get_python_signatures_multiline() -> None:
    """
    Tests extraction of multi-line Python signatures to ensure they are normalized.

    Returns:
        None
    """
    code = """
def multiline_func(
    a: int,
    b: str
) -> bool:
    return True
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        sigs = auditor.get_python_signatures(tmp_path)
        # Verify AST unparsing compacts the signature for token efficiency
        assert "def multiline_func(a: int, b: str) -> bool:" in sigs
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_check_critical_context_tokens() -> None:
    """
    Tests the critical context token counting logic.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("Hello world")

        with open(os.path.join(tmpdir, "test.py"), "w") as f:
            f.write("def foo(): pass")

        result = auditor.check_critical_context_tokens(tmpdir)
        assert result["token_count"] > 0
        assert result["alert"] is False


def test_check_critical_context_tokens_single_file() -> None:
    """
    Tests critical context token counting when targeting a single file, ensuring 
    it still retrieves global context (like README.md) from the parent directory.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w") as f:
            f.write("Global context")

        py_path = os.path.join(tmpdir, "test.py")
        with open(py_path, "w") as f:
            f.write("def foo(): pass")

        result = auditor.check_critical_context_tokens(py_path)
        assert result["token_count"] > 0
        
        # Verify the count includes the README content plus signature tokens
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        sig_tokens = len(enc.encode("def foo():"))
        assert result["token_count"] > sig_tokens


def test_check_environment_health() -> None:
    """
    Tests the environment health checks for AGENTS.md, linters, and lock files.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initial state: no critical files
        res = auditor.check_environment_health(tmpdir)
        assert res["agents_md"] is False
        assert res["linter_config"] is False
        assert res["lock_file"] is False

        # Verify detection of AGENTS.md
        with open(os.path.join(tmpdir, "AGENTS.md"), "w") as f:
            f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["agents_md"] is True

        # Verify detection of external linter config
        with open(os.path.join(tmpdir, "ruff.toml"), "w") as f:
            f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["linter_config"] is True

        # Verify detection of lock file
        with open(os.path.join(tmpdir, "poetry.lock"), "w") as f:
            f.write("")
        res = auditor.check_environment_health(tmpdir)
        assert res["lock_file"] is True


def test_check_environment_health_pyproject_ruff() -> None:
    """
    Tests that ruff configuration within pyproject.toml is correctly recognized 
    as a valid linter configuration.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
            f.write("[tool.ruff]\nline-length = 88")
        res = auditor.check_environment_health(tmpdir)
        assert res["linter_config"] is True