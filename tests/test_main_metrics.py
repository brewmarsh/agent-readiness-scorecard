from pathlib import Path
from click.testing import CliRunner
from agent_scorecard.main import cli


def test_main_metrics_god_module(tmp_path: Path) -> None:
    """
    Tests detection of God Modules through the CLI.

    This test simulates a high-pressure context point by creating a single
    module imported by more than 50 clients.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    # Create 55 files importing 'god_module' to trigger the architectural warning
    (tmp_path / "god_module.py").write_text("x = 1")

    for i in range(55):
        (tmp_path / f"client_{i}.py").write_text("import god_module\n")

    runner = CliRunner()
    # Invoke the CLI scorecard against the temporary directory
    result = runner.invoke(cli, ["score", str(tmp_path)])

    # Verify that the system identifies the God Module in the output
    assert "God Modules Detected" in result.output
    assert "god_module" in result.output


def test_main_metrics_directory_entropy(tmp_path: Path) -> None:
    """
    Tests detection of high directory entropy through the CLI.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory.

    Returns:
        None
    """
    # Create 55 files in one directory to trigger entropy warning (>50 files)
    for i in range(55):
        (tmp_path / f"file_{i}.txt").write_text("content")

    # The auditor looks for directories containing python files
    (tmp_path / "trigger.py").write_text("pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path)])

    # Verify that 'High Directory Entropy' is reported to the user
    assert "High Directory Entropy" in result.output