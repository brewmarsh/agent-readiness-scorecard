from typing import Dict, Any, Tuple, List
from .metrics import get_loc, get_function_stats

def score_file(filepath: str, profile: Dict[str, Any]) -> Tuple[int, str, int, float, float, List[Dict[str, Any]]]:
    """Calculates score based on the selected profile and new Agent Readiness spec."""
    metrics = get_function_stats(filepath)
    loc = get_loc(filepath)

    score = 100
    details = []

    # 1. Bloated Files Penalty
    # -1 pt per 10 lines > 200
    if loc > 200:
        bloat_penalty = (loc - 200) // 10
        if bloat_penalty > 0:
            score -= bloat_penalty
            details.append(f"Bloated File: {loc} lines (-{bloat_penalty})")

    if not metrics:
        # If no functions, return score (potentially with bloat penalty)
        return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

    # 2. ACL Scoring (Agent Cognitive Load)
    # Thresholds: Green <= 10, Yellow 10.1-15, Red > 15
    red_count = sum(1 for m in metrics if m["acl"] > 15)
    yellow_count = sum(1 for m in metrics if 10 < m["acl"] <= 15)

    if red_count > 0:
        penalty = red_count * 15
        score -= penalty
        details.append(f"{red_count} Red ACL functions (-{penalty})")

    if yellow_count > 0:
        penalty = yellow_count * 5
        score -= penalty
        details.append(f"{yellow_count} Yellow ACL functions (-{penalty})")

    # 3. Type Safety Index
    # Target based on profile for a "Pass"
    min_type_cov = profile.get("min_type_coverage", 90)
    typed_count = sum(1 for m in metrics if m["is_typed"])
    type_safety_index = (typed_count / len(metrics)) * 100

    if type_safety_index < min_type_cov:
        penalty = 20
        score -= penalty
        details.append(f"Type Safety Index {type_safety_index:.0f}% < {min_type_cov}% (-{penalty})")

    avg_complexity = sum(m["complexity"] for m in metrics) / len(metrics)

    return max(score, 0), ", ".join(details), loc, avg_complexity, type_safety_index, metrics

def generate_badge(score: float) -> str:
    """Generates an SVG badge for the agent score."""
    if score >= 90:
        color = "#4c1"  # Bright Green
    elif score >= 70:
        color = "#97ca00"  # Green
    elif score >= 50:
        color = "#dfb317"  # Yellow
    else:
        color = "#e05d44"  # Red

    score_str = f"{int(score)}/100"

    # Constants for SVG generation
    left_width = 70
    right_width = 50
    total_width = left_width + right_width
    height = 20
    border_radius = 3

    # SVG template using f-strings
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
        <text aria-hidden="true" x="{left_width * 10 / 2}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(left_width - 10) * 10}">Agent Score</text>
        <text x="{left_width * 10 / 2}" y="140" transform="scale(.1)" fill="#fff" textLength="{(left_width - 10) * 10}">Agent Score</text>
        <text aria-hidden="true" x="{(left_width + right_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(right_width - 10) * 10}">{score_str}</text>
        <text x="{(left_width + right_width / 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(right_width - 10) * 10}">{score_str}</text>
    </g>
</svg>
"""
    return svg_template.strip()
