import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .constants import PROFILES
from .analyzer import scan_project_docs, get_loc, analyze_complexity, analyze_type_hints
from .fix import apply_fixes
from .scoring import score_file, generate_badge
from .report import generate_report

console = Console()

@click.group()
def cli():
    """Agent Scorecard: AI-readiness analyzer."""
    pass

@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
def score(path: str, agent: str, fix: bool, badge: bool):
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
        s, notes = score_file(filepath, profile)
        file_scores.append(s)

        status_color = "green" if s >= 70 else "red"
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        table.add_row(rel_path, f"[{status_color}]{s}[/{status_color}]", notes)

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

@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--output", default="agent_advisor.md", help="Output file for the report.")
def advise(path: str, agent: str, output: str):
    """Generate a detailed Advisor Report."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]
    console.print(Panel(f"[bold cyan]Running Agent Advisor[/bold cyan]\nProfile: {agent.upper()}", expand=False))

    # Collect data
    missing_docs = []
    project_score = 100
    if os.path.isdir(path):
        missing_docs = scan_project_docs(path, profile["required_files"])
        if missing_docs:
            project_score -= (len(missing_docs) * 15)

    py_files = []
    if os.path.isfile(path):
        if path.endswith(".py"): py_files = [path]
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    file_results = []
    file_scores = []

    with console.status("[bold green]Analyzing files..."):
        for filepath in py_files:
            # We need raw metrics + score
            loc = get_loc(filepath)
            complexity = analyze_complexity(filepath)
            type_cov = analyze_type_hints(filepath)

            # Calculate score using score_file logic (or calling it)
            # Since score_file calculates penalties internally, we can call it to get the score.
            s, _ = score_file(filepath, profile)
            file_scores.append(s)

            file_results.append({
                "filepath": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
                "loc": loc,
                "complexity": complexity,
                "type_coverage": type_cov,
                "score": s
            })

    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    report = generate_report(final_score, file_results, missing_docs, profile)

    with open(output, "w", encoding="utf-8") as f:
        f.write(report)

    console.print(f"[bold green]Report generated at {output}[/bold green]")

if __name__ == "__main__":
    cli()
