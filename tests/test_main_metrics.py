from click.testing import CliRunner
from src.agent_scorecard.main import cli

def test_main_metrics_god_module(tmp_path):
    # Create 55 files importing 'god_module'
    (tmp_path / "god_module.py").write_text("x = 1")

    for i in range(55):
        (tmp_path / f"client_{i}.py").write_text("import god_module\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path)])

    assert "God Modules Detected" in result.output
    assert "god_module" in result.output

def test_main_metrics_directory_entropy(tmp_path):
    # Create 55 files in one directory
    for i in range(55):
        (tmp_path / f"file_{i}.txt").write_text("content") # .txt files are counted by count_directory_files
        # Note: main.py uses py_files to find directories, so at least one .py file is needed

    (tmp_path / "trigger.py").write_text("pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", str(tmp_path)])

    assert "High Directory Entropy" in result.output
