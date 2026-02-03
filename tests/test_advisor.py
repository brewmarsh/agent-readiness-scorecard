import os
import textwrap
import pytest
from src.agent_scorecard import analyzer, report
from src.agent_scorecard.constants import PROFILES

def test_acl_calculation(tmp_path):
    code = textwrap.dedent("""
        def complex_function():
            if True:
                print("yes")
            else:
                print("no")
            # a
            # b
            # c
            # d
            # e
            # f
            # g
            # h
            # i
            # j
            # k
            # l
            # m
            # n
            # o
            # p
            # q
            # r
            # s
            # t
            return 0
    """)

    p = tmp_path / "test_acl.py"
    p.write_text(code, encoding="utf-8")

    stats = analyzer.get_function_stats(str(p))
    assert len(stats) == 1
    func = stats[0]
    assert func["name"] == "complex_function"
    assert func["complexity"] >= 2
    assert func["loc"] >= 20
    assert func["acl"] > 2

def test_circular_dependency(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import c", encoding="utf-8")
    (tmp_path / "c.py").write_text("import a", encoding="utf-8")

    stats = analyzer.analyze_project(str(tmp_path))
    deps = stats["dependencies"]
    cycles = deps["cycles"]

    assert len(cycles) > 0

    found = False
    for cycle in cycles:
        if set(cycle) == {"a.py", "b.py", "c.py"}:
            found = True
            break
    assert found

def test_advisor_report_generation(tmp_path):
    # Setup a project that triggers advisor warnings
    # High LOC + Complexity to trigger ACL
    # ACL = CC + LOC/20. > 15
    # Let's make CC=10, LOC=120. ACL = 10 + 6 = 16.

    code = "def hallucinate():\n"
    for _ in range(10):
        code += "    if True: pass\n"
    for i in range(120):
        code += f"    x={i}\n"

    (tmp_path / "hallucination.py").write_text(code, encoding="utf-8")

    stats = analyzer.analyze_project(str(tmp_path))
    report_md = report.generate_markdown_report(stats, 50, str(tmp_path), PROFILES["generic"])

    assert "Advisor Mode Analysis" in report_md
    assert "Agent Cognitive Load (ACL)" in report_md
    assert "hallucinate" in report_md
