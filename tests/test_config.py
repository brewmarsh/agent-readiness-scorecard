import os
import tempfile
from agent_scorecard.config import load_config, DEFAULT_CONFIG


def test_load_config_defaults():
    # Test loading from a directory with no pyproject.toml
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(tmpdir)
        assert config["verbosity"] == DEFAULT_CONFIG["verbosity"]
        assert config["thresholds"] == DEFAULT_CONFIG["thresholds"]


def test_load_config_with_pyproject():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_content = """
[tool.agent-scorecard]
verbosity = "detailed"
[tool.agent-scorecard.thresholds]
acl_yellow = 5
type_safety = 80
"""
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
            f.write(pyproject_content)

        config = load_config(tmpdir)
        assert config["verbosity"] == "detailed"
        assert config["thresholds"]["acl_yellow"] == 5
        assert (
            config["thresholds"]["acl_red"] == DEFAULT_CONFIG["thresholds"]["acl_red"]
        )
        assert config["thresholds"]["type_safety"] == 80


def test_load_config_invalid_toml():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
            f.write("invalid = [")

        config = load_config(tmpdir)
        assert config == DEFAULT_CONFIG
