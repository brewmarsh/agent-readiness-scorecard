import textwrap
from pathlib import Path
from src.agent_scorecard.analyzer import analyze_imports

def test_analyze_imports_internal_only(tmp_path):
    # Create internal module
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

    # List of files
    files = [str(tmp_path / "internal.py"), str(tmp_path / "client.py")]

    counts = analyze_imports(files)

    # internal should be counted (once for import internal, once for from internal import x)
    assert counts['internal'] == 2

    # os and sys should NOT be counted as they are not in the file list
    assert 'os' not in counts
    assert 'sys' not in counts
