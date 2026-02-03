from typing import Dict, Any, Tuple
from . import analyzer

def score_file(filepath: str, profile: Dict[str, Any]) -> Tuple[int, str]:
    """Calculates score based on the selected profile."""
    score = 100
    details = []

    # 1. Lines of Code
    loc = analyzer.get_loc(filepath)
    limit = profile["max_loc"]
    if loc > limit:
        # -1 point per 10 lines over limit
        excess = loc - limit
        loc_penalty = (excess // 10)
        score -= loc_penalty
        details.append(f"LOC {loc} > {limit} (-{loc_penalty})")

    # 2. Complexity
    avg_comp = analyzer.get_complexity_score(filepath)
    comp_penalty = 10 if avg_comp > profile["max_complexity"] else 0
    score -= comp_penalty
    if comp_penalty:
        details.append(f"Complexity {avg_comp:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # 3. Type Hints
    type_cov = analyzer.check_type_hints(filepath)
    type_penalty = 20 if type_cov < profile["min_type_coverage"] else 0
    score -= type_penalty
    if type_penalty:
        details.append(f"Types {type_cov:.0f}% < {profile['min_type_coverage']}% (-{type_penalty})")

    # 4. Agent Cognitive Load (ACL)
    # We penalize specific functions that are too hard for an agent to read,
    # rather than just averaging the whole file.
    func_stats = analyzer.get_function_stats(filepath)
    acl_penalty = 0
    for func in func_stats:
        if func['acl'] > 15:
            penalty = 5
            acl_penalty += penalty
            # Use concise Beta format for CLI table readability
            details.append(f"ACL({func['name']}) {func['acl']:.1f} > 15 (-{penalty})")

    score -= acl_penalty

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