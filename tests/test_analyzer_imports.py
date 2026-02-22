import textwrap
from pathlib import Path
from agent_scorecard.analyzer import get_import_graph, get_inbound_imports


def test_analyze_imports_internal_only(tmp_path: Path) -> None:
    """
    Tests that only internal project modules are tracked in the import graph,
    ignoring external standard library or third-party imports.

    Args:
        tmp_path (Path): Pytest fixture for temporary directory creation.

    Returns:
        None
    """
    # Create internal module to be imported
    (tmp_path / "internal.py").write_text("x = 1", encoding="utf-8")

    # Create client module importing both internal and external modules
    code = textwrap.dedent("""
    import internal
    import os
    import sys
    from internal import x
    from os import path
    """)
    (tmp_path / "client.py").write_text(code, encoding="utf-8")

    # Build graph and calculate inbound counts using the root path
    graph = get_import_graph(str(tmp_path))
    inbound = get_inbound_imports(graph)

    # In graph: 'client.py' depends on 'internal.py'
    # In inbound: 'internal.py' should have 1 inbound import
    assert inbound.get("internal.py", 0) >= 1

    # Standard library modules (os, sys) should NOT be tracked in the project graph
    assert "os" not in inbound
    assert "sys" not in inbound
    assert "os.py" not in inbound


if __name__ == "__main__":
    import shutil
    import tempfile

    # Manual test execution harness
    path = Path(tempfile.mkdtemp())
    try:
        test_analyze_imports_internal_only(path)
        print("Tests passed!")
    finally:
        shutil.rmtree(path)