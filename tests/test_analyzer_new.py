import textwrap
from pathlib import Path
from agent_scorecard.analyzer import get_function_stats


def test_get_function_stats(tmp_path: Path) -> None:
    """
    Tests extraction of function statistics including complexity, LOC, and ACL.

    This test verifies that the analyzer correctly calculates metrics for both
    simple linear functions and more complex functions with branching logic
    and higher line density.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    code = textwrap.dedent("""
    def simple():
        return 1

    def complex_long():
        a = 0
        if True:
            a += 1
        else:
            a -= 1
        # Adding lines to increase LOC and test ACL calculation sensitivity
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        a = a + 1
        return a
    """)
    p = tmp_path / "test_acl.py"
    p.write_text(code, encoding="utf-8")

    # Analyzer expects a string path; convert from pathlib.Path object
    stats = get_function_stats(str(p))
    assert len(stats) == 2

    simple_func = next(s for s in stats if s["name"] == "simple")
    complex_func = next(s for s in stats if s["name"] == "complex_long")

    # Simple function verification: Complexity 1, LOC 2. 
    # Calculation: 1 + 2/20 = 1.1 ACL
    assert simple_func["complexity"] == 1
    assert simple_func["loc"] == 2
    assert simple_func["acl"] == 1.1

    # Complex function verification: Complexity 2 (if/else branching), LOC ~25. 
    # Calculation: 2 + 25/20 = 3.25 ACL
    assert complex_func["complexity"] == 2
    assert complex_func["loc"] >= 20
    assert complex_func["acl"] > 3.0