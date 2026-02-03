import sys
import click
from importlib.metadata import version, PackageNotFoundError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules
from . import analyzer, report

# Use the Modular Refactor imports
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge

console = Console()

# --- MERGED VERSION SETUP ---
try:
    __version__ = version("agent-scorecard")
except PackageNotFoundError:
    __version__ = "0.0.0"

# --- MERGED CLI DEFINITION ---
# We use analyzer.DefaultGroup from the 'fix' branch to enable correct default behavior
# We use version_option from the 'main' branch for standard --version support
@click.group(cls=analyzer.DefaultGroup)
@click.version_option(version=__version__)
def cli() -> None:
    """Main entry point for the agent-scorecard CLI."""
    pass

def run_scoring(path: str, agent: str, fix: bool, badge: bool, report_path: str) -> None:
    """Helper to run the scoring logic."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"
    profile = PROFILES[agent]

    if fix:
        console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)
        console.print("")

    results = analyzer.perform_analysis(path, agent)
    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    if results["missing_docs"]:
        penalty = len(results["missing_docs"]) * 15
        console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(results['missing_docs'])} (-{penalty} pts)")

    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    for res in results["file_results"]:
        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])

    console.print(table)
    console.print(f"\n[bold]Final Agent Score: {results['final_score']:.1f}/100[/bold]")

    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(results["final_score"])
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    if report_path:
        report_content = report.generate_markdown_report(results)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if results["final_score"] < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")

@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
@click.option("--report", "report_path", type=click.Path(), help="Save the report to a Markdown file.")
def score(path: str, agent: str, fix: bool, badge: bool, report_path: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    run_scoring(path, agent, fix, badge, report_path)


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save the report to a Markdown file.")
@click.option("--agent", default="generic", help="Profile to use.")
def advise(path, output_file, agent):
    """Generates a Markdown report with actionable advice."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    results = analyzer.perform_analysis(path, agent)
    report_content = report.generate_markdown_report(results)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        console.print(f"\n[bold green]Report saved to {output_file}[/bold green]")
    else:
        console.print("\n" + report_content)

if __name__ == "__main__":
    cli()
