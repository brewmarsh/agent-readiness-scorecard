from typing import Dict, Any, Tuple, List, Optional
from .metrics import get_loc, get_function_stats
from .types import FunctionMetric


def score_file(
    filepath: str, profile: Dict[str, Any], thresholds: Optional[Dict[str, Any]] = None
) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
    """
    Calculates score based on the selected profile and Agent Readiness spec.
    Priority: explicit thresholds arg > profile thresholds > hardcoded defaults.
    """
    # 1. Initialize Thresholds
    p_thresholds = profile.get("thresholds", {})

    if thresholds is None:
        thresholds = {
            "acl_yellow": p_thresholds.get("acl_yellow", 10),
            "acl_red": p_thresholds.get("acl_red", 15),
            "type_safety": p_thresholds.get("type_safety", 90),
        }

    metrics = get_function_stats(filepath)
    loc = get_loc(filepath)

    score = 100
    details = []

    # 2. Bloated Files Penalty
    # -1 pt per 10 lines > 200. High LLOC increases hallucination risk for agents.
    if loc > 200:
        bloat_penalty = (loc - 200) // 10
        if bloat_penalty > 0:
            score -= bloat_penalty
            details.append(f"Bloated File: {loc} lines (-{bloat_penalty})")

    # If no functions, return current score (potentially with bloat penalty)
    if not metrics:
        return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

    # 3. Extract granular thresholds
    acl_yellow = thresholds.get("acl_yellow", 10)
    acl_red = thresholds.get("acl_red", 15)
    type_safety_threshold = thresholds.get("type_safety", 90)

    # 4. ACL Scoring (Agent Cognitive Load)
    # Red functions represent "hallucination zones" where agents lose tracking.
    red_count = sum(1 for m in metrics if m["acl"] > acl_red)
    yellow_count = sum(1 for m in metrics if acl_yellow < m["acl"] <= acl_red)

    if red_count > 0:
        penalty = red_count * 15
        score -= penalty
        details.append(f"{red_count} Red ACL functions (-{penalty})")

    if yellow_count > 0:
        penalty = yellow_count * 5
        score -= penalty
        details.append(f"{yellow_count} Yellow ACL functions (-{penalty})")

    # 5. Type Safety Index
    typed_count = sum(1 for m in metrics if m["is_typed"])
    type_safety_index = (typed_count / len(metrics)) * 100

    if type_safety_index < type_safety_threshold:
        penalty = 20
        score -= penalty
        details.append(
            f"Type Safety Index {type_safety_index:.0f}% < {type_safety_threshold}% (-{penalty})"
        )

    avg_complexity = sum(m["complexity"] for m in metrics) / len(metrics)

    # Ensure score doesn't dip below 0
    return (
        max(score, 0),
        ", ".join(details),
        loc,
        avg_complexity,
        type_safety_index,
        metrics,
    )


def generate_badge(score: float) -> str:
    """Generates an SVG badge based on the final agent readiness score."""
    if score >= 90:
        color = "#4c1"  # Bright Green
    elif score >= 70:
        color = "#97ca00"  # Green
    elif score >= 50:
        color = "#dfb317"  # Yellow
    else:
        color = "#e05d44"  # Red

    score_str = f"{int(score)}/100"
    left_width = 85
    right_width = 50
    total_width = left_width + right_width
    height = 20
    border_radius = 3

    svg_template = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="Agent Score: {score_str}">
    <title>Agent Score: {score_str}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="{height}" rx="{border_radius}" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{left_width}" height="{height}" fill="#555"/>
        <rect x="{left_width}" width="{right_width}" height="{height}" fill="{color}"/>
        <rect width="{total_width}" height="{height}" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{left_width * 10 / 2}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(left_width - 10) * 10}">Agent Readiness</text>
        <text x="{left_width * 10 / 2}" y="140" transform="scale(.1)" fill="#fff" textLength="{(left_width - 10) * 10}">Agent Readiness</text>
        <text aria-hidden="true" x="{(left_width + right_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(right_width - 10) * 10}">{score_str}</text>
        <text x="{(left_width + right_width / 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(right_width - 10) * 10}">{score_str}</text>
    </g>
</svg>
"""
    return svg_template.strip()
