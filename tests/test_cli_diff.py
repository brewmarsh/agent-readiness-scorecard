import os
import subprocess
from click.testing import CliRunner
from agent_scorecard.main import cli


def setup_git_repo(path: str) -> None:
    """Initialize a git repo and make initial commit."""
    # Create origin/main branch/ref simulation for default behavior
    subprocess.run(["git", "init"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "you@example.com"], cwd=path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Your Name"], cwd=path, check=True)
    # Default branch name 'main' to match default logic
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, check=True)

    with open(os.path.join(path, "README.md"), "w") as f:
        f.write("# Test Repo\n")

    with open(os.path.join(path, "file1.py"), "w") as f:
        f.write("def foo():\n    pass\n")

    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)

    # Create origin/main as a branch to simulate remote tracking branch
    subprocess.run(["git", "branch", "origin/main"], cwd=path, check=True)


def test_diff_no_changes() -> None:
    """Test --diff with no changes."""
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        setup_git_repo(temp_dir)

        # Run with --diff. Should find no changes.
        # verbosity detailed so we can see if files are listed.
        result = runner.invoke(cli, ["score", ".", "--diff", "--verbosity", "detailed"])

        assert result.exit_code == 0
        # Should report no changed files warning
        assert "No changed files found to analyze" in result.output
        # Should NOT list file1.py
        assert "file1.py" not in result.output


def test_diff_with_changes() -> None:
    """Test --diff with changes."""
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        setup_git_repo(temp_dir)

        # Modify file1.py
        with open(os.path.join(temp_dir, "file1.py"), "a") as f:
            f.write("\ndef bar():\n    pass\n")

        # Create new file2.py
        with open(os.path.join(temp_dir, "file2.py"), "w") as f:
            f.write("def baz():\n    pass\n")

        # We need to stage file2.py so git diff sees it (untracked files are ignored by diff)
        subprocess.run(["git", "add", "file2.py"], cwd=temp_dir, check=True)

        # Run with --diff
        result = runner.invoke(cli, ["score", ".", "--diff", "--verbosity", "detailed"])

        assert result.exit_code == 0
        assert "file1.py" in result.output
        assert "file2.py" in result.output


def test_diff_base_option() -> None:
    """Test --diff-base option."""
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        setup_git_repo(temp_dir)

        # Create a feature branch
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=temp_dir, check=True)

        with open(os.path.join(temp_dir, "file1.py"), "a") as f:
            f.write("\n# change\n")

        subprocess.run(
            ["git", "commit", "-am", "Change on feature"], cwd=temp_dir, check=True
        )

        # Compare against main
        result = runner.invoke(
            cli,
            ["score", ".", "--diff", "--diff-base", "main", "--verbosity", "detailed"],
        )

        assert result.exit_code == 0
        assert "file1.py" in result.output


def test_diff_and_limit_to() -> None:
    """Test interaction of --diff and --limit-to."""
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        setup_git_repo(temp_dir)

        # Modify file1.py
        with open(os.path.join(temp_dir, "file1.py"), "a") as f:
            f.write("\n# change 1\n")

        # Create file2.py and add it
        with open(os.path.join(temp_dir, "file2.py"), "w") as f:
            f.write("def baz():\n    pass\n")
        subprocess.run(["git", "add", "file2.py"], cwd=temp_dir, check=True)

        # Both file1.py and file2.py are changed vs origin/main.

        # Limit to file2.py
        result = runner.invoke(
            cli,
            [
                "score",
                ".",
                "--diff",
                "--limit-to",
                "file2.py",
                "--verbosity",
                "detailed",
            ],
        )

        assert result.exit_code == 0
        assert "file1.py" not in result.output
        assert "file2.py" in result.output
