import os
import sys
import click
from importlib.metadata import version, PackageNotFoundError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules
from . import analyzer, report, auditor

from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge, score_file

console = Console()

# --- VERSION SETUP ---
try:
    __version__ = version("agent-scorecard")
except PackageNotFoundError:
    __version__ = "0.0.0"

# --- CLI DEFINITION ---
class DefaultGroup(click.Group):
    """Invokes a default command if a subcommand is not found."""
    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and not args[0].startswith('-'):
                args.insert(0, "score")
            elif not args:
                args.insert(0, "score")
            return super().resolve_command(ctx, args)

@click.group(cls=DefaultGroup)
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

    # Run Analysis
    results = analyzer.perform_analysis(path, agent)
    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 1. Environment Health & Auditor Checks (Preserved from Beta Branch)
    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)
    health_table.add_row("AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]")
    health_table.add_row("Linter Config", "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]")
    health_table.add_row("Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]")

    entropy = auditor.check_directory_entropy(path)
    entropy_status = f"{entropy['avg_files']:.1f} files/dir"
    if entropy["warning"]:
        health_table.add_row("Directory Entropy", f"[yellow]WARN ({entropy_status})[/yellow]")
    else:
        health_table.add_row("Directory Entropy", f"[green]PASS ({entropy_status})[/green]")

    tokens = auditor.check_critical_context_tokens(path)
    token_status = f"{tokens['token_count']:,} tokens"
    if tokens["alert"]:
        health_table.add_row("Critical Token Count", f"[red]ALERT ({token_status})[/red]")
    else:
        health_table.add_row("Critical Token Count", f"[green]PASS ({token_status})[/green]")

    # Dependency Analysis Cycle Check
    if results.get("dep_analysis", {}).get("cycles"):
        health_table.add_row("Circular Dependencies", f"[red]DETECTED ({len(results['dep_analysis']['cycles'])})[/red]")
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)
    console.print("") # Spacing

    # 2. Critical Docs Check (Redundant but kept for output consistency)
    if results["missing_docs"]:
        penalty = len(results["missing_docs"]) * 15
        console.print(f"[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(results['missing_docs'])} (-{penalty} pts)\n")

    # 3. File Table
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    for res in results["file_results"]:
        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])

    console.print(table)
    console.print(f"\n[bold]Final Agent Score: {results['final_score']:.1f}/100[/bold]")

    # 4. Badge Generation
    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(results["final_score"])
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    # 5. Report Generation
    if report_path:
        report_content = report.generate_markdown_report(
            results["file_results"],
            results["final_score"],
            path,
            profile,
            results.get("project_issues")
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if results["final_score"] < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")

@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
def fix(path: str, agent: str) -> None:
    """Automatically fix common issues in the codebase."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"
    profile = PROFILES[agent]

    console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
    apply_fixes(path, profile)
    console.print("[bold green]Fixes applied![/bold green]")

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
def advise(path, output_file):
    """Generates a Markdown report with actionable advice based on Agent Physics."""

    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))

    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            parts = root.split(os.sep)
            if any(p.startswith(".") and p != "." for p in parts):
                continue
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    stats = []
    with console.status("[bold green]Analyzing Code Physics...[/bold green]"):
        for filepath in py_files:
            loc = analyzer.get_loc(filepath)
            complexity = analyzer.get_complexity_score(filepath)

            func_stats = analyzer.get_function_stats(filepath)
            max_acl = max((f['acl'] for f in func_stats), default=0)

            stats.append({
                "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
                "loc": loc,
                "complexity": complexity,
                "acl": max_acl,
                "tokens": auditor.check_critical_context_tokens(filepath)["token_count"]
            })

        # Dependency Analysis
        graph = analyzer.get_import_graph(path)
        inbound = analyzer.get_inbound_imports(graph)
        cycles = analyzer.detect_cycles(graph)

        # Entropy Analysis
        entropy = analyzer.get_directory_entropy(path)

    markdown_report = report.generate_advisor_report(stats, inbound, entropy, cycles)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(f"\n[bold green]Report saved to {output_file}[/bold green]")
    else:
        from rich.markdown import Markdown
        console.print(Markdown(markdown_report))

if __name__ == "__main__":
    cli()
