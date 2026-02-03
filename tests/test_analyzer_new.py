import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import get_function_stats

def test_get_function_stats(tmp_path):
    code = textwrap.dedent("""
    def simple():
        return 1

    def complex_long():
        a = 0
        if True:
            a += 1
        else:
            a -= 1
        # Adding lines to increase LOC
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

    stats = get_function_stats(str(p))
    assert len(stats) == 2

    simple = next(s for s in stats if s['name'] == 'simple')
    complex_long = next(s for s in stats if s['name'] == 'complex_long')

    # Simple: Complexity 1, LOC ~2. ACL = 1 + 2/20 = 1.1
    assert simple['complexity'] == 1
    assert simple['loc'] == 2
    assert simple['acl'] == 1.1

    # Complex: Complexity 2 (if/else), LOC ~25. ACL = 2 + 25/20 = 3.25
    assert complex_long['complexity'] == 2
    assert complex_long['loc'] >= 20
    assert complex_long['acl'] > 3.0
