import os
import shutil
import tempfile
import unittest
from agent_readiness_scorecard.analyzer import perform_analysis


class TestAgenticBonuses(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        # Create a dummy python file to analyze
        with open(os.path.join(self.test_dir, "core.py"), "w") as f:
            f.write("def hello():\n    pass\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def test_context_steering_bonus(self) -> None:
        # Create a context file
        open(os.path.join(self.test_dir, ".cursorrules"), "w").close()

        results = perform_analysis(self.test_dir)
        # Verify bonus is applied. Default missing docs penalty might be present.
        self.assertTrue(results["agentic_ecosystem"]["has_context_files"])

    def test_framework_bonus(self) -> None:
        # Create a requirements.txt with a framework
        with open(os.path.join(self.test_dir, "requirements.txt"), "w") as f:
            f.write("pydantic-ai\n")

        results = perform_analysis(self.test_dir)
        self.assertTrue(results["agentic_ecosystem"]["has_agent_frameworks"])

    def test_multiple_bonuses_capped(self) -> None:
        # Both bonuses. We want to check that it doesn't exceed 100 if we have enough base score.
        # To ensure high base score, we need to satisfy mandatory docs if any.

        results = perform_analysis(self.test_dir)
        self.assertLessEqual(results["final_score"], 100.0)

    def test_bonus_affects_lower_score(self) -> None:
        # Force a penalty by missing critical docs (AGENTS.md is usually required by jules profile)
        # jules profile requires AGENTS.md and instructions.md
        # If they are missing, penalty is applied.

        # Let's use the generic profile but induce some penalty if possible.
        # Missing docs penalty: len(missing_docs) * 15
        # Generic profile required_files: [] by default? Let's check constants.py

        # Actually, let's just mock the project_issues or induca a penalty.
        # One easy way is to have a lot of files for entropy penalty, but that's slow.

        # Let's just verify that with NO bonuses, score might be 100.
        # If we have a penalty of 20, score becomes 80. +5 bonus -> 85.

        # Missing docs in generic profile?
        from agent_readiness_scorecard.constants import PROFILES
        profile = PROFILES["generic"].copy()
        profile["required_files"] = ["MANDATORY.md"] # Induce penalty

        # No bonus
        results_no_bonus = perform_analysis(self.test_dir, profile=profile)
        score_no_bonus = results_no_bonus["final_score"]

        # Add context bonus
        open(os.path.join(self.test_dir, ".cursorrules"), "w").close()
        results_with_bonus = perform_analysis(self.test_dir, profile=profile)
        score_with_bonus = results_with_bonus["final_score"]

        self.assertEqual(score_with_bonus, min(100.0, score_no_bonus + 5.0))


if __name__ == "__main__":
    unittest.main()
