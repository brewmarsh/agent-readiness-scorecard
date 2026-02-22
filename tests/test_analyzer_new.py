import textwrap
from pathlib import Path
from agent_scorecard.analyzer import get_function_stats, calculate_max_depth


def test_calculate_max_depth() -> None:
    """
    Tests the calculate_max_depth function with various nesting scenarios.

    This test verifies that the analyzer correctly identifies and counts
    nested control flow blocks, including edge cases like list comprehensions
     and inline lambdas.

    Returns:
        None
    """
    # Flat function
    code1 = "def foo(): pass"
    assert calculate_max_depth(code1) == 0

    # Example from prompt
    code2 = textwrap.dedent("""
    def process_data(data):
        if data:
            for item in data:
                if item > 0:
                    print(item)
    """)
    assert calculate_max_depth(code2) == 3

    # Nested Try/Except/Finally
    code3 = textwrap.dedent("""
    try:
        try:
            pass
        except:
            pass
    finally:
        pass
    """)
    assert calculate_max_depth(code3) == 2

    # List comprehension and lambda
    code4 = "x = [lambda y: [i for i in range(y)] for y in range(10)]"
    # ListComp -> Lambda -> ListComp = 3
    assert calculate_max_depth(code4) == 3

    # Deep nesting with mixed types
    code5 = textwrap.dedent("""
    if a:
        while b:
            with c:
                for d in e:
                    if f:
                        pass
    """)
    assert calculate_max_depth(code5) == 5

    # Async variants
    code6 = textwrap.dedent("""
    async def foo():
        async for i in range(10):
            async with a:
                pass
    """)
    assert calculate_max_depth(code6) == 2


def test_get_function_stats(tmp_path: Path) -> None:
    """
    Tests extraction of function statistics including complexity, LOC, ACL, and Nesting Depth.

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

    def deeply_nested():
        if True:
            if True:
                if True:
                    pass
    """)
    p = tmp_path / "test_acl.py"
    p.write_text(code, encoding="utf-8")

    # Analyzer expects a string path; convert from pathlib.Path object
    stats = get_function_stats(str(p))
    assert len(stats) == 3

    simple_func = next(s for s in stats if s["name"] == "simple")
    complex_func = next(s for s in stats if s["name"] == "complex_long")
    nested_func = next(s for s in stats if s["name"] == "deeply_nested")

    # Simple function verification: Complexity 1, LOC 2.
    # Calculation: 1 + 2/20 = 1.1 ACL
    assert simple_func["complexity"] == 1
    assert simple_func["loc"] == 2
    assert simple_func["acl"] == 1.1
    assert simple_func["nesting_depth"] == 0

    # Complex function verification: Complexity 2 (if/else branching), LOC ~25.
    # Calculation: 2 + 25/20 = 3.25 ACL
    assert complex_func["complexity"] == 2
    assert complex_func["loc"] >= 20
    assert complex_func["acl"] > 3.0
    assert complex_func["nesting_depth"] == 1

    # Deeply nested function
    assert nested_func["nesting_depth"] == 3
