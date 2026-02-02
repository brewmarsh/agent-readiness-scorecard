from typing import Dict, Any, Tuple
from .checks import get_loc, get_complexity_score, check_type_hints

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
    avg_comp, comp_penalty = get_complexity_score(filepath, profile["max_complexity"])
    score -= comp_penalty
    if comp_penalty:
        details.append(f"Complexity {avg_comp:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # 3. Type Hints
    type_cov, type_penalty = check_type_hints(filepath, profile["min_type_coverage"])
    score -= type_penalty
    if type_penalty:
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

    score_str = f"{score:.1f}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="a">
        <rect width="120" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#a)">
        <path fill="#555" d="M0 0h80v20H0z"/>
        <path fill="{color}" d="M80 0h40v20H80z"/>
        <path fill="url(#b)" d="M0 0h120v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
        <text x="40" y="15" fill="#010101" fill-opacity=".3">Agent Score</text>
        <text x="40" y="14">Agent Score</text>
        <text x="100" y="15" fill="#010101" fill-opacity=".3">{score_str}</text>
        <text x="100" y="14">{score_str}</text>
    </g>
</svg>"""
