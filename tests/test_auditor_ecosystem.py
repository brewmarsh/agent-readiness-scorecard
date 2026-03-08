import os
import shutil
import tempfile
import unittest
from agent_readiness_scorecard.auditor import check_agentic_ecosystem, check_environment_health

class TestAuditorEcosystem(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def test_detect_context_files(self) -> None:
        # Create some context files
        open(os.path.join(self.test_dir, ".cursorrules"), "w").close()
        os.makedirs(os.path.join(self.test_dir, "cline_docs"))

        result = check_agentic_ecosystem(self.test_dir)
        self.assertTrue(result["has_context_files"])
        self.assertIn(".cursorrules", result["found_files"])
        self.assertIn("cline_docs", result["found_files"])
        self.assertFalse(result["has_agent_frameworks"])

    def test_detect_frameworks_in_pyproject(self) -> None:
        with open(os.path.join(self.test_dir, "pyproject.toml"), "w") as f:
            f.write('[project]\ndependencies = ["pydantic-ai", "instructor"]')

        result = check_agentic_ecosystem(self.test_dir)
        self.assertTrue(result["has_agent_frameworks"])
        self.assertIn("pydantic-ai", result["found_frameworks"])
        self.assertIn("instructor", result["found_frameworks"])
        self.assertFalse(result["has_context_files"])

    def test_detect_frameworks_in_requirements(self) -> None:
        with open(os.path.join(self.test_dir, "requirements.txt"), "w") as f:
            f.write("crewai\nlangfuse")

        result = check_agentic_ecosystem(self.test_dir)
        self.assertTrue(result["has_agent_frameworks"])
        self.assertIn("crewai", result["found_frameworks"])
        self.assertIn("langfuse", result["found_frameworks"])

    def test_environment_health_integration(self) -> None:
        # Create a context file
        open(os.path.join(self.test_dir, ".windsurfrules"), "w").close()

        health = check_environment_health(self.test_dir)
        self.assertIsNotNone(health["agentic_ecosystem"])
        self.assertTrue(health["agentic_ecosystem"]["has_context_files"])
        self.assertIn(".windsurfrules", health["agentic_ecosystem"]["found_files"])

if __name__ == "__main__":
    unittest.main()
