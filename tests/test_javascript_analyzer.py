import pytest
from typing import Dict, Any
from pathlib import Path
from agent_scorecard.analyzers.javascript import JavascriptAnalyzer


@pytest.fixture
def js_analyzer() -> JavascriptAnalyzer:
    return JavascriptAnalyzer()


def test_js_simple_function(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test basic JavaScript function analysis.

    Mathematical Breakdown:
    - complexity: 2.0 (1.0 base + 1.0 for 'if')
    - nesting_depth: 1 (1 level for 'if')
    - loc: 6
    - ACL = (1 * 2.0) + (2.0 * 1.5) + (6 / 50.0) = 2 + 3 + 0.12 = 5.12
    """
    js_file = tmp_path / "test.js"
    js_file.write_text(
        """
function add(a, b) {
    if (a > 0) {
        return a + b;
    }
    return b;
}
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(js_file))
    assert len(metrics) == 1
    func = metrics[0]
    assert func["name"] == "add"
    assert func["complexity"] == 2.0  # if
    assert func["nesting_depth"] == 1
    assert func["loc"] == 6
    # ACL = (1 * 2) + (2 * 1.5) + (6 / 50) = 2 + 3 + 0.12 = 5.12
    assert func["acl"] == 5.12


def test_js_arrow_function(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test basic arrow function analysis.

    Mathematical Breakdown:
    - complexity: 1.0 (base)
    - nesting_depth: 0
    - loc: 3
    - ACL = (0 * 2.0) + (1.0 * 1.5) + (3 / 50.0) = 0 + 1.5 + 0.06 = 1.56
    """
    js_file = tmp_path / "arrow.js"
    js_file.write_text(
        """
const mul = (a, b) => {
    return a * b;
};
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(js_file))
    assert len(metrics) == 1
    func = metrics[0]
    # Name might be anonymous for arrow function currently
    # assert func["name"] == "anonymous"
    assert func["complexity"] == 1.0
    assert func["nesting_depth"] == 0
    assert func["loc"] == 3


def test_ts_typed_function(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test TypeScript function with type annotations.

    Mathematical Breakdown:
    - complexity: 1.0 (base)
    - nesting_depth: 0
    - loc: 3
    - ACL = (0 * 2.0) + (1.0 * 1.5) + (3 / 50.0) = 1.56
    """
    ts_file = tmp_path / "typed.ts"
    ts_file.write_text(
        """
function add(a: number, b: number): number {
    return a + b;
}
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(ts_file))
    assert len(metrics) == 1
    func = metrics[0]
    assert func["is_typed"] is True


def test_ts_untyped_function(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test TypeScript function without type annotations.

    Mathematical Breakdown:
    - complexity: 1.0 (base)
    - nesting_depth: 0
    - loc: 3
    - ACL = (0 * 2.0) + (1.0 * 1.5) + (3 / 50.0) = 1.56
    """
    ts_file = tmp_path / "untyped.ts"
    ts_file.write_text(
        """
function add(a, b) {
    return a + b;
}
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(ts_file))
    assert len(metrics) == 1
    func = metrics[0]
    assert func["is_typed"] is False


def test_js_complex_logic(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test complex JavaScript logic with multiple branching and nesting.

    Mathematical Breakdown:
    - complexity: 5.0 (1.0 base + 1.0 for 'if', 1.0 for '&&', 1.0 for 'while', 1.0 for 'if')
    - nesting_depth: 3 (if -> while -> if)
    - loc: 11
    - ACL = (3 * 2.0) + (5.0 * 1.5) + (11 / 50.0) = 6 + 7.5 + 0.22 = 13.72
    """
    js_file = tmp_path / "complex.js"
    js_file.write_text(
        """
function complex(a, b) {
    if (a && b) {
        while (a > 0) {
            a--;
            if (b > 10) break;
        }
    } else {
        return 0;
    }
}
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(js_file))
    assert len(metrics) == 1
    func = metrics[0]
    # Complexity:
    # if (a && b) -> if + && = 2
    # while -> 1
    # if (b > 10) -> 1
    # Total = 1 (base) + 2 + 1 + 1 = 5

    assert func["complexity"] == 5.0

    # Depth:
    # if -> depth 1
    #   while -> depth 2
    #     if -> depth 3
    # Max depth = 3
    assert func["nesting_depth"] == 3


def test_score_file(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test scoring of a TypeScript file.
    """
    ts_file = tmp_path / "score.ts"
    ts_file.write_text(
        """
function add(a: number, b: number): number {
    return a + b;
}
""",
        encoding="utf-8",
    )

    profile: Dict[str, Any] = {"thresholds": {}}
    score, details, loc, complexity, type_safety, metrics = js_analyzer.score_file(
        str(ts_file), profile
    )

    assert score == 100
    assert type_safety == 100.0


def test_score_file_untyped_ts(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test scoring of an untyped TypeScript file, verifying Type Safety penalty.
    """
    ts_file = tmp_path / "score_bad.ts"
    ts_file.write_text(
        """
function add(a, b) {
    return a + b;
}
""",
        encoding="utf-8",
    )

    profile: Dict[str, Any] = {"thresholds": {"type_safety": 90}}
    score, details, loc, complexity, type_safety, metrics = js_analyzer.score_file(
        str(ts_file), profile
    )

    assert type_safety == 0.0
    assert score < 100
    assert "Type Safety Index" in details


def test_callback_hell(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test that deeply nested asynchronous callbacks increase the nesting_depth of the parent function.

    Mathematical Breakdown for 'outer':
    - complexity: 1.0 (base)
    - nesting_depth: 3 (3 levels of nested anonymous functions)
    - loc: 9 (lines 2 to 10)
    - ACL = (3 * 2.0) + (1.0 * 1.5) + (9 / 50.0) = 6 + 1.5 + 0.18 = 7.68
    """
    js_file = tmp_path / "callback_hell.js"
    js_file.write_text(
        """
function outer() {
    setTimeout(() => {
        setTimeout(() => {
            setTimeout(() => {
                console.log("Hell");
            }, 100);
        }, 100);
    }, 100);
}
""",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(js_file))
    # Functions: outer, and 3 nested arrow functions
    assert len(metrics) == 4

    outer = next(m for m in metrics if m["name"] == "outer")
    assert outer["nesting_depth"] == 3
    assert outer["acl"] == 7.68


def test_inline_arrow_function(js_analyzer: JavascriptAnalyzer, tmp_path: Path) -> None:
    """
    Test that inline arrow functions (e.g., as callbacks in .map()) are identified as functional units.

    Mathematical Breakdown for the arrow function 'x => x * 2':
    - complexity: 1.0 (base)
    - nesting_depth: 0
    - loc: 1 (single line arrow function)
    - ACL = (0 * 2.0) + (1.0 * 1.5) + (1 / 50.0) = 0 + 1.5 + 0.02 = 1.52
    """
    js_file = tmp_path / "inline.js"
    js_file.write_text(
        "const doubled = [1, 2, 3].map(x => x * 2);",
        encoding="utf-8",
    )

    metrics = js_analyzer.get_function_stats(str(js_file))
    assert len(metrics) == 1
    func = metrics[0]
    assert func["name"] == "anonymous"
    assert func["loc"] == 1
    assert func["nesting_depth"] == 0
    assert func["acl"] == 1.52


def test_missing_tree_sitter_graceful_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that the JavascriptAnalyzer handles missing tree-sitter gracefully.

    Mocking HAS_TREE_SITTER to False should result in an empty list of metrics
    as the analyzer cannot proceed without the underlying parser.
    """
    # Mock the flag that indicates tree-sitter presence
    monkeypatch.setattr(
        "agent_scorecard.analyzers.javascript.HAS_TREE_SITTER", False
    )

    analyzer = JavascriptAnalyzer()
    p = tmp_path / "valid.js"
    p.write_text("function a() {}", encoding="utf-8")

    # Should not raise an exception and should return an empty list
    stats = analyzer.get_function_stats(str(p))
    assert stats == []
