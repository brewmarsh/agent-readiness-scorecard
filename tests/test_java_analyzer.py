import pytest
from pathlib import Path
from src.agent_scorecard.analyzers.java import JavaAnalyzer


@pytest.fixture
def java_analyzer() -> JavaAnalyzer:
    return JavaAnalyzer()


def test_java_simple_method(java_analyzer: JavaAnalyzer, tmp_path: Path) -> None:
    java_file = tmp_path / "Test.java"
    java_file.write_text(
        """
public class Test {
    public int add(int a, int b) {
        if (a > 0) {
            return a + b;
        }
        return b;
    }
}
""",
        encoding="utf-8",
    )

    metrics = java_analyzer.get_function_stats(str(java_file))
    assert len(metrics) == 1
    func = metrics[0]
    assert func["name"] == "add"
    assert func["complexity"] == 2.0  # if
    assert func["nesting_depth"] == 1
    assert func["loc"] == 6
    # ACL = (1 * 2) + (2 * 1.5) + (6 / 50) = 2 + 3 + 0.12 = 5.12
    assert func["acl"] == 5.12
    assert func["is_typed"] is True


def test_java_complexity(java_analyzer: JavaAnalyzer, tmp_path: Path) -> None:
    java_file = tmp_path / "Complex.java"
    java_file.write_text(
        """
public class Complex {
    public void complex(boolean a, boolean b) {
        if (a && b) {
            while (a) {
                if (b) break;
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    metrics = java_analyzer.get_function_stats(str(java_file))
    assert len(metrics) == 1
    func = metrics[0]
    # Complexity:
    # if (a && b) -> if + && = 2
    # while -> 1
    # if (b) -> 1
    # Total = 1 (base) + 2 + 1 + 1 = 5.0
    assert func["complexity"] == 5.0
    assert func["nesting_depth"] == 3


def test_java_switch(java_analyzer: JavaAnalyzer, tmp_path: Path) -> None:
    java_file = tmp_path / "Switch.java"
    java_file.write_text(
        """
public class Switch {
    public void check(int x) {
        switch (x) {
            case 1:
                System.out.println("1");
                break;
            case 2:
                System.out.println("2");
                break;
            default:
                System.out.println("default");
        }
    }
}
""",
        encoding="utf-8",
    )

    metrics = java_analyzer.get_function_stats(str(java_file))
    assert len(metrics) == 1
    func = metrics[0]
    # Complexity:
    # switch -> 0 (base 1)
    # case 1 -> +1
    # case 2 -> +1
    # default -> +0
    # Total = 1 + 1 + 1 = 3.0
    assert func["complexity"] == 3.0


def test_score_file_java(java_analyzer: JavaAnalyzer, tmp_path: Path) -> None:
    java_file = tmp_path / "Score.java"
    java_file.write_text(
        """
public class Score {
    public int add(int a, int b) {
        return a + b;
    }
}
""",
        encoding="utf-8",
    )

    profile = {"thresholds": {}}
    score, details, loc, complexity, type_safety, metrics = java_analyzer.score_file(
        str(java_file), profile
    )

    assert score == 100
    assert type_safety == 100.0
