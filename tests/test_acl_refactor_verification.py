import textwrap
from pathlib import Path
from agent_readiness_scorecard.analyzers.python import PythonAnalyzer


def test_acl_formula_favor_flat_long_over_short_nested(tmp_path: Path) -> None:
    """
    Verifies that the new ACL formula favors flat, long files over short, deeply nested files.

    New Formula: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)
    Old Formula: ACL = Complexity + (LOC / 20)
    """
    # 1. Flat, Long Function
    # Depth=0 (no nested blocks), CC=1, LOC=100
    flat_long_code = "def flat_long():\n"
    for i in range(98):
        flat_long_code += f"    x = {i}\n"
    flat_long_code += "    return x\n"

    # 2. Short, Deeply Nested Function
    # Depth=4, CC=5, LOC=10
    short_nested_code = textwrap.dedent("""
    def short_nested(a):
        if a > 0:
            if a > 1:
                if a > 2:
                    if a > 3:
                        return a
        return 0
    """)

    flat_file = tmp_path / "flat.py"
    flat_file.write_text(flat_long_code, encoding="utf-8")

    nested_file = tmp_path / "nested.py"
    nested_file.write_text(short_nested_code, encoding="utf-8")

    flat_metrics = PythonAnalyzer().get_function_stats(str(flat_file))
    nested_metrics = PythonAnalyzer().get_function_stats(str(nested_file))

    flat_acl = flat_metrics[0]["acl"]
    nested_acl = nested_metrics[0]["acl"]

    # New Formula Calculations:
    # Flat: Depth=0, CC=1, LOC=100. ACL = (0*2) + (1*1.5) + (100/50) = 1.5 + 2 = 3.5
    # Nested: Depth=4, CC=5, LOC=10. ACL = (4*2) + (5*1.5) + (10/50) = 8 + 7.5 + 0.2 = 15.7

    print(f"Flat ACL: {flat_acl}")
    print(f"Nested ACL: {nested_acl}")

    assert flat_acl < nested_acl
    assert nested_acl > 15  # Should be Red
    assert flat_acl < 10  # Should be Green
