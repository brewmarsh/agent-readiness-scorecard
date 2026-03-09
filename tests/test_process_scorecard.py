import unittest
from unittest.mock import patch, MagicMock, mock_open
import re
import json
import scripts.process_scorecard as ps

class TestProcessScorecard(unittest.TestCase):

    @patch('subprocess.run')
    def test_check_issue_exists_true(self, mock_run):
        mock_run.return_value.stdout = json.dumps([{"number": 123}])
        self.assertTrue(ps.check_issue_exists("file.py", "High Cognitive Load"))

    @patch('subprocess.run')
    def test_check_issue_exists_false(self, mock_run):
        mock_run.return_value.stdout = json.dumps([])
        self.assertFalse(ps.check_issue_exists("file.py", "High Cognitive Load"))

    @patch('subprocess.run')
    def test_create_issue(self, mock_run):
        mock_run.return_value.stdout = "https://github.com/issue/1"
        ps.create_issue("file.py", "High Cognitive Load", "prompt")
        # Check if gh issue create was called
        self.assertTrue(any("create" in call.args[0] for call in mock_run.call_args_list))
        # Check if labels were attempted
        self.assertTrue(any("edit" in call.args[0] for call in mock_run.call_args_list))

    @patch('scripts.process_scorecard.create_issue')
    @patch('scripts.process_scorecard.check_issue_exists')
    def test_process_match_high_acl_new(self, mock_exists, mock_create):
        mock_exists.return_value = False
        match = MagicMock()
        match.group.side_effect = lambda i: ["", "file.py", "High Cognitive Load", "prompt"][i]
        typing_tasks = []
        ps._process_match(match, typing_tasks)
        mock_create.assert_called_once_with("file.py", "High Cognitive Load", "prompt")

    @patch('scripts.process_scorecard.create_issue')
    @patch('scripts.process_scorecard.check_issue_exists')
    def test_process_match_high_acl_exists(self, mock_exists, mock_create):
        mock_exists.return_value = True
        match = MagicMock()
        match.group.side_effect = lambda i: ["", "file.py", "High Cognitive Load", "prompt"][i]
        typing_tasks = []
        ps._process_match(match, typing_tasks)
        mock_create.assert_not_called()

    def test_process_match_low_type_safety(self):
        match = MagicMock()
        match.group.side_effect = lambda i: ["", "file.py", "Low Type Safety", "prompt"][i]
        typing_tasks = []
        ps._process_match(match, typing_tasks)
        self.assertEqual(len(typing_tasks), 1)
        self.assertEqual(typing_tasks[0]["file"], "file.py")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('scripts.process_scorecard._process_match')
    def test_main(self, mock_process, mock_exists, mock_file):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "### File: `f.py` - High Cognitive Load\nprompt\n"
        with patch('sys.argv', ['script.py', 'scorecard.txt']):
            ps.main()
        self.assertTrue(mock_process.called)

if __name__ == '__main__':
    unittest.main()
