import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .constants import PROFILES
from .checks import scan_project_docs
from .fix import apply_fixes
from .scoring import score_file, generate_badge

console = Console()

@click.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
def cli(path: str, agent: str, fix: bool, badge: bool) -> None:
    """Analyze code compatibility for specific AI Agents."""

    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]

    if fix:
        console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)
        console.print("") # Newline

    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 1. Project Level Check
    project_score = 100
    missing_docs = []

    if os.path.isdir(path):
        missing_docs = scan_project_docs(path, profile["required_files"])
        if missing_docs:
            penalty = len(missing_docs) * 15
            project_score -= penalty
            console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(missing_docs)} (-{penalty} pts)")

    # 2. File Level Check
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    py_files = []
    if os.path.isfile(path):
        if path.endswith(".py"): py_files = [path]
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    file_scores = []
    for filepath in py_files:
        score, notes = score_file(filepath, profile)
        file_scores.append(score)

        status_color = "green" if score >= 70 else "red"
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        table.add_row(rel_path, f"[{status_color}]{score}[/{status_color}]", notes)

    console.print(table)

    # 3. Final Aggregation
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    # Weighted average: 80% file quality, 20% project structure
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    console.print(f"\n[bold]Final Agent Score: {final_score:.1f}/100[/bold]")

    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(final_score)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    if final_score < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")


def generate_badge(score):
    """Generates an SVG badge for the agent score."""
    if score >= 90:
        color = "#4c1"  # Bright Green
    elif score >= 70:
        color = "#dfb317"  # Yellow/Orange
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


if __name__ == "__main__":
    cli()
