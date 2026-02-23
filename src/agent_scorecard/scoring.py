import warnings
from typing import Dict, Any, Tuple, List, Optional
from .analyzers.python import PythonAnalyzer
from .types import FunctionMetric


def score_file(
    filepath: str,
    profile: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None,
    cumulative_tokens: int = 0,
) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
    """
    Calculates score based on the selected profile and Agent Readiness spec.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.score_file` instead.
    """
    warnings.warn(
        "score_file is deprecated, use PythonAnalyzer().score_file() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().score_file(filepath, profile, thresholds, cumulative_tokens)


def generate_badge(score: float) -> str:
    """
    Generates an SVG badge based on the final agent readiness score.

    Args:
        score (float): The final agent readiness score.

    Returns:
        str: SVG string representing the badge.
    """
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
        <rect width="{total_width}" height="{height}" fill="#555"/>
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
