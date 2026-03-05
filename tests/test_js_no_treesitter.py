import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock tree-sitter before importing JavascriptAnalyzer
with patch.dict(sys.modules, {
    'tree_sitter': None,
    'tree_sitter_javascript': None,
    'tree_sitter_typescript': None
}):
    # Import inside the patch context
    from agent_readiness_scorecard.analyzers.javascript import JavascriptAnalyzer, HAS_TREESITTER

class TestJavascriptAnalyzerNoTreesitter(unittest.TestCase):
    def test_has_treesitter_is_false(self):
        self.assertFalse(HAS_TREESITTER)

    def test_score_file_no_treesitter(self):
        analyzer = JavascriptAnalyzer()
        score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
            "test.js",
            {"thresholds": {}},
            thresholds={},
            cumulative_tokens=0
        )
        self.assertEqual(score, 0)
        self.assertIn("[treesitter] extra", issues)
        self.assertEqual(loc, 0)
        self.assertEqual(complexity, 0.0)
        self.assertEqual(type_safety, 0.0)
        self.assertEqual(metrics, [])

    def test_get_function_stats_no_treesitter(self):
        analyzer = JavascriptAnalyzer()
        stats = analyzer.get_function_stats("test.js")
        self.assertEqual(stats, [])

if __name__ == "__main__":
    unittest.main()
