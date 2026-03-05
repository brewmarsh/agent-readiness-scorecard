import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys
import os

from agent_readiness_scorecard.analyzers.javascript import JavascriptAnalyzer
import agent_readiness_scorecard.analyzers.javascript as js_module

from agent_readiness_scorecard.analyzers.markdown import MarkdownAnalyzer
import agent_readiness_scorecard.analyzers.markdown as md_module

from agent_readiness_scorecard.analyzers.config import ConfigAnalyzer
import agent_readiness_scorecard.analyzers.config as config_module

from agent_readiness_scorecard.analyzers.python import PythonAnalyzer
import agent_readiness_scorecard.analyzers.python as py_module

def test_javascript_analyzer_no_treesitter(tmp_path):
    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello');")

    analyzer = JavascriptAnalyzer()

    with patch("agent_readiness_scorecard.analyzers.javascript.HAS_TREESITTER", False):
        # We also need to reset the warning flag to test the output if we wanted,
        # but here we just check the return value.
        with patch("agent_readiness_scorecard.analyzers.javascript.WARN_TREESITTER", False):
            score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
                str(js_file), {"thresholds": {}}
            )

            assert score == 0
            assert "Missing dependencies: Install [treesitter] extra" in issues
            assert loc > 0
            assert metrics == []

def test_markdown_analyzer_no_tiktoken(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\nSome content here.")

    analyzer = MarkdownAnalyzer()

    with patch("agent_readiness_scorecard.analyzers.markdown.HAS_TIKTOKEN", False):
        with patch("agent_readiness_scorecard.analyzers.markdown.WARN_TIKTOKEN", False):
            score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
                str(md_file), {"thresholds": {}}
            )

            assert "Missing dependency: tiktoken (using heuristic)" in issues
            # It should still have metrics because of the heuristic
            assert len(metrics) > 0
            assert metrics[0]["complexity"] > 0

def test_config_analyzer_no_yaml(tmp_path):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key: value")

    analyzer = ConfigAnalyzer()

    with patch("agent_readiness_scorecard.analyzers.config.yaml", None):
        with patch("agent_readiness_scorecard.analyzers.config.WARN_YAML", False):
            score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
                str(yaml_file), {"thresholds": {}}
            )

            assert "Missing dependency: PyYAML" in issues
            assert metrics == []

def test_config_analyzer_no_toml(tmp_path):
    toml_file = tmp_path / "test.toml"
    toml_file.write_text("key = 'value'")

    analyzer = ConfigAnalyzer()

    with patch("agent_readiness_scorecard.analyzers.config.toml_parser", None):
        with patch("agent_readiness_scorecard.analyzers.config.WARN_TOML", False):
            score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
                str(toml_file), {"thresholds": {}}
            )

            assert "Missing dependency: tomli or tomllib" in issues
            assert metrics == []

def test_python_analyzer_no_mccabe(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("def hello():\n    pass")

    analyzer = PythonAnalyzer()

    with patch("agent_readiness_scorecard.analyzers.python.HAS_MCCABE", False):
        with patch("agent_readiness_scorecard.analyzers.python.WARN_MCCABE", False):
            score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
                str(py_file), {"thresholds": {}}
            )

            assert "Missing dependency: mccabe (complexity skipped)" in issues
            assert len(metrics) > 0
            # Complexity should be default 1.0
            assert metrics[0]["complexity"] == 1.0
