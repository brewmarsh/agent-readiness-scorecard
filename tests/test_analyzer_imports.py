import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import get_import_graph, get_inbound_imports

# TODO: Add type hints for Agent clarity
def test_analyze_imports_internal_only(tmp_path):
    # Create internal module
    """TODO: Add docstring for AI context."""
    (tmp_path / "internal.py").write_text("x = 1", encoding="utf-8")

    # Create client importing internal and external
    code = textwrap.dedent("""
    import internal
    import os
    import sys
    from internal import x
    from os import path
    """)
    (tmp_path / "client.py").write_text(code, encoding="utf-8")

    # get_import_graph takes root_path
    graph = get_import_graph(str(tmp_path))
    inbound = get_inbound_imports(graph)

    # Graph keys are relative paths
    print(f"Graph: {graph}")
    print(f"Inbound: {inbound}")

    # internal.py should have 0 inbound imports (nobody imports it? Wait, client.py imports it)
    # client.py imports internal.py.
    # So internal.py inbound count should be > 0.

    # In graph: 'client.py': {'internal.py'}
    # In inbound: 'internal.py': 1

    assert inbound.get('internal.py', 0) >= 1

    # os and sys should NOT be in the graph or inbound (as they are external)
    assert 'os' not in inbound
    assert 'sys' not in inbound
    assert 'os.py' not in inbound

if __name__ == "__main__":
    import shutil
    import tempfile
    path = Path(tempfile.mkdtemp())
    try:
        test_analyze_imports_internal_only(path)
        print("Tests passed!")
    finally:
        shutil.rmtree(path)
