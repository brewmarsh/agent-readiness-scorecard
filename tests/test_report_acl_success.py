from typing import List, Dict, Any
from agent_readiness_scorecard.report import _generate_acl_section


def test_generate_acl_section_success() -> None:
    # Mock stats where all functions are below acl_yellow (default 10)
    stats: List[Dict[str, Any]] = [
        {
            "file": "test.py",
            "function_metrics": [
                {"name": "func1", "acl": 5.0},
                {"name": "func2", "acl": 9.0},
            ],
        }
    ]
    thresholds: Dict[str, Any] = {"acl_yellow": 10, "acl_red": 15}

    report = _generate_acl_section(stats, thresholds)

    assert (
        "✅ All functions meet the Agent Cognitive Load (ACL) target of <= 10."
        in report
    )
    assert "| Function |" not in report  # No table header


def test_generate_acl_section_with_targets() -> None:
    # Mock stats where some functions exceed acl_yellow
    stats: List[Dict[str, Any]] = [
        {
            "file": "test.py",
            "function_metrics": [
                {"name": "func1", "acl": 12.0},
                {"name": "func2", "acl": 5.0},
            ],
        }
    ]
    thresholds: Dict[str, Any] = {"acl_yellow": 10, "acl_red": 15}

    report = _generate_acl_section(stats, thresholds)

    assert "| Function | File | 🧠 ACL | Status |" in report
    assert "| `func1` | `test.py` | 12.0 | 🟡 Yellow |" in report
    assert "`func2`" not in report  # func2 should be filtered out
