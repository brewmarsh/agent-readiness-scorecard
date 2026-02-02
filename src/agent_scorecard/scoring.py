from typing import Dict, Any, Tuple
from .analyzer import get_loc, analyze_complexity, analyze_type_hints

def score_file(filepath: str, profile: Dict[str, Any]) -> Tuple[int, str]:
    """Calculates score based on the selected profile."""
    score = 100
    details = []

    # 1. Lines of Code
    loc = get_loc(filepath)
    limit = profile["max_loc"]
    if loc > limit:
        # -1 point per 10 lines over limit
        excess = loc - limit
        loc_penalty = (excess // 10)
        score -= loc_penalty
        details.append(f"LOC {loc} > {limit} (-{loc_penalty})")

    # 2. Complexity
    avg_comp = analyze_complexity(filepath)
    comp_penalty = 0
    if avg_comp > profile["max_complexity"]:
        comp_penalty = 10  # Fixed penalty for complexity
        score -= comp_penalty
        details.append(f"Complexity {avg_comp:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # 3. Type Hints
    type_cov = analyze_type_hints(filepath)
    type_penalty = 0
    if type_cov < profile["min_type_coverage"]:
        type_penalty = 20 # Fixed penalty for types
        score -= type_penalty
        details.append(f"Types {type_cov:.0f}% < {profile['min_type_coverage']}% (-{type_penalty})")

    return max(score, 0), ", ".join(details)

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
