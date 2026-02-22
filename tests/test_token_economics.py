import os
import tempfile
from agent_scorecard.analyzer import perform_analysis


def test_cumulative_token_budget_exceeded():
    """
    Tests that a small file importing a massive module triggers a token budget alert.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a massive "God Module" (approx 35,000 tokens)
        # 35,000 tokens * 4 chars/token (approx) = 140,000 chars
        god_module_path = os.path.join(tmpdir, "god_module.py")
        with open(god_module_path, "w") as f:
            f.write("# Massive module\n")
            f.write("def massive_func():\n")
            f.write("    pass\n")
            # Add a lot of content to exceed the token limit
            for i in range(10000):
                f.write(f"def func_{i}():\n    pass\n")

        # Create a small main file that imports the god module
        main_py_path = os.path.join(tmpdir, "main.py")
        with open(main_py_path, "w") as f:
            f.write("import god_module\n")
            f.write("def main():\n")
            f.write("    pass\n")

        # Run analysis
        results = perform_analysis(tmpdir)

        # Find main.py results
        main_result = next(r for r in results["file_results"] if r["file"] == "main.py")

        # main.py should have high cumulative tokens
        assert main_result["cumulative_tokens"] > 32000

        # main.py should have a penalty in its issues
        assert "Cumulative Token Budget Exceeded" in main_result["issues"]

        # score should be less than 100
        assert main_result["score"] < 100


def test_cumulative_token_budget_within_limit():
    """
    Tests that a small file with small imports does not trigger the alert.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        utils_py_path = os.path.join(tmpdir, "utils.py")
        with open(utils_py_path, "w") as f:
            f.write("def helper():\n    pass\n")

        main_py_path = os.path.join(tmpdir, "main.py")
        with open(main_py_path, "w") as f:
            f.write("import utils\n")
            f.write("def main():\n    pass\n")

        results = perform_analysis(tmpdir)
        main_result = next(r for r in results["file_results"] if r["file"] == "main.py")

        assert main_result["cumulative_tokens"] < 32000
        assert "Cumulative Token Budget Exceeded" not in main_result["issues"]
        # If no other issues, score should be 100 (assuming it has docstrings etc if checked, but here it's simple)
        # Actually it might have penalties for missing docstrings if profile requires them.
        # But here we just care about the token budget.
