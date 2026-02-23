import pytest
from pathlib import Path
from agent_scorecard.analyzers.javascript import JavascriptAnalyzer
from agent_scorecard.constants import PROFILES


def test_js_analyzer_basic_function(tmp_path: Path) -> None:
    """Test analysis of a basic JS function."""
    js_content = """
function hello(name) {
  if (name) {
    return "Hello " + name;
  }
  return "Hello anonymous";
}
"""
    js_file = tmp_path / "test.js"
    js_file.write_text(js_content, encoding="utf-8")

    analyzer = JavascriptAnalyzer()
    stats = analyzer.get_function_stats(str(js_file))

    assert len(stats) == 1
    assert stats[0]["name"] == "hello"
    assert stats[0]["complexity"] == 2.0  # 1 (base) + 1 (if)
    assert stats[0]["nesting_depth"] == 1  # 1 (if)
    assert stats[0]["is_typed"] is False


def test_js_analyzer_arrow_function(tmp_path: Path) -> None:
    """Test analysis of an arrow function."""
    js_content = """
const sum = (a, b) => {
  return a + b;
};
"""
    js_file = tmp_path / "test.js"
    js_file.write_text(js_content, encoding="utf-8")

    analyzer = JavascriptAnalyzer()
    stats = analyzer.get_function_stats(str(js_file))

    assert len(stats) == 1
    assert stats[0]["name"] == "sum"
    assert stats[0]["complexity"] == 1.0
    assert stats[0]["nesting_depth"] == 0


def test_js_analyzer_nested_logic(tmp_path: Path) -> None:
    """Test analysis of deeply nested logic."""
    js_content = """
function complex(x) {
  if (x > 0) {
    for (let i = 0; i < x; i++) {
      if (i % 2 === 0) {
        console.log(i);
      }
    }
  }
}
"""
    js_file = tmp_path / "test.js"
    js_file.write_text(js_content, encoding="utf-8")

    analyzer = JavascriptAnalyzer()
    stats = analyzer.get_function_stats(str(js_file))

    assert len(stats) == 1
    assert stats[0]["complexity"] == 4.0  # 1 (base) + 1 (if) + 1 (for) + 1 (if)
    assert stats[0]["nesting_depth"] == 3


def test_ts_analyzer_typing(tmp_path: Path) -> None:
    """Test type detection in TS files."""
    ts_content = """
function typed(a: number): string {
  return a.toString();
}

function untyped(a) {
  return a;
}
"""
    ts_file = tmp_path / "test.ts"
    ts_file.write_text(ts_content, encoding="utf-8")

    analyzer = JavascriptAnalyzer()
    stats = analyzer.get_function_stats(str(ts_file))

    assert len(stats) == 2
    typed_func = next(s for s in stats if s["name"] == "typed")
    untyped_func = next(s for s in stats if s["name"] == "untyped")

    assert typed_func["is_typed"] is True
    assert untyped_func["is_typed"] is False


def test_js_analyzer_score_file(tmp_path: Path) -> None:
    """Test full file scoring for JS."""
    js_content = """
function a() { return 1; }
function b() { return 2; }
"""
    js_file = tmp_path / "test.js"
    js_file.write_text(js_content, encoding="utf-8")

    analyzer = JavascriptAnalyzer()
    score, issues, loc, complexity, type_safety, metrics = analyzer.score_file(
        str(js_file), PROFILES["generic"]
    )

    # JS has 0% type safety, so it gets a penalty of 20
    assert score == 80
    assert loc == 2
    assert complexity == 1.0
    assert type_safety == 0.0
