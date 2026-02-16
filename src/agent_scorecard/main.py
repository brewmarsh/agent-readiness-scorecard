import os
import sys
import subprocess
from typing import Optional, List

import click
from importlib.metadata import version, PackageNotFoundError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules
from . import analyzer, report, auditor
from .prompt_analyzer import PromptAnalyzer

from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge

console = Console()

# --- VERSION SETUP ---
try:
    __version__ = version("agent-scorecard")
except PackageNotFoundError:
    __version__ = "0.0.0"

# --- CLI DEFINITION ---
class DefaultGroup(click.Group):
    """Invokes a default command if a subcommand is not found."""
    def resolve_command(self, ctx: click.Context, args: List[str]):
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

def get_changed_files(base_ref: str = "origin/main") -> list:
    """Uses git diff to return a list of changed Python files."""
    try:
        cmd = ["git", "diff", "--name-only", "--diff-filter=d", base_ref, "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [f for f in result.stdout.splitlines() if f.endswith(".py") and os.path.exists(f)]
    except Exception:
        return []

def run_scoring(path: str, agent: str, fix: bool, badge: bool, report_path: str, limit_to_files: list = None) -> None:
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
    results = analyzer.perform_analysis(path, agent, limit_to_files=limit_to_files)
    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 1. Environment Health & Auditor Checks
    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)
    health_table.add_row("AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]")
    health_table.add_row("Linter Config", "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]")
    health_table.add_row("Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]")

    entropy = auditor.check_directory_entropy(path)
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        entropy_status = f"Max {entropy['max_files']} files/dir"
        entropy_label = "WARN"
    else:
        entropy_status = f"{entropy['avg_files']:.1f} files/dir"
        entropy_label = "WARN" if entropy["warning"] else "PASS"

    entropy_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{entropy_color}]{entropy_label} ({entropy_status})[/{entropy_color}]")

    tokens = auditor.check_critical_context_tokens(path)
    token_status = f"{tokens['token_count']:,} tokens"
    if tokens["alert"]:
        health_table.add_row("Critical Token Count", f"[red]ALERT ({token_status})[/red]")
    else:
        health_table.add_row("Critical Token Count", f"[green]PASS ({token_status})[/green]")

    if results.get("dep_analysis", {}).get("cycles"):
        health_table.add_row("Circular Dependencies", f"[red]DETECTED ({len(results['dep_analysis']['cycles'])})[/red]")
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)
    console.print("") 

    # 2. File Table
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    for res in results["file_results"]:
        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])

    console.print(table)
    console.print(f"\n[bold]Final Agent Score: {results['final_score']:.1f}/100[/bold]")

    # Explicit warnings for tests
    if results.get("missing_docs"):
        console.print(f"[bold red]Missing Critical Agent Docs: {', '.join(results['missing_docs'])}[/bold red]")

    god_modules = results.get("dep_analysis", {}).get("god_modules", {})
    if god_modules:
        console.print(f"[bold red]God Modules Detected: {', '.join(god_modules.keys())}[/bold red]")

    if entropy["warning"]:
        console.print(f"[bold yellow]High Directory Entropy ({entropy_status})[/bold yellow]")

    # 3. Artifact Generation
    if badge:
        output_path = "agent_score.svg"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generate_badge(results["final_score"]))
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")

    if report_path:
        report_content = report.generate_markdown_report(
            results["file_results"], results["final_score"], path, profile, results.get("project_issues")
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if results["final_score"] < 70:
        sys.exit(1)

@cli.command(name="check-prompts")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, allow_dash=True))
@click.option("--plain", is_flag=True, help="Output raw score and suggestions for CI.")
def check_prompts(input_path: str, plain: bool) -> None:
    """Checks a prompt file for LLM best practices."""
    if input_path == "-":
        content = sys.stdin.read()
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

    analyzer_inst = PromptAnalyzer()
    result = analyzer_inst.analyze(content)
    score = result["score"]

    if plain:
        click.echo(f"Score: {score}")
        for sug in result.get('improvements', result.get('suggestions', [])):
            click.echo(f"Suggestion: {sug}")
    else:
        table = Table(title=f"Prompt Analysis: {os.path.basename(input_path) if input_path != '-' else 'Stdin'}")
        table.add_column("Heuristic", style="cyan")
        table.add_column("Status", justify="right")

        order = ["role_definition", "cognitive_scaffolding", "delimiter_hygiene", "few_shot", "negative_constraints"]
        for key in order:
            if key in result.get("results", {}):
                status = "[green]✅ PASS[/green]" if result["results"][key] else "[red]❌ FAIL[/red]"
                table.add_row(key.replace("_", " ").title(), status)

        console.print(table)
        color = "green" if score >= 80 else "red"
        console.print(f"\nScore: [bold {color}]{score}/100[/bold {color}]")

        if result.get("improvements"):
            console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            for imp in result["improvements"]:
                console.print(f"💡 {imp}")

        if score >= 80:
            console.print("\n[bold green]PASSED: Prompt is optimized![/bold green]")

    if score < 80:
        sys.exit(1)

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
@click.option("--diff", "diff_base", help="Only score files changed vs this git ref.")
def score(path: str, agent: str, fix: bool, badge: bool, report_path: str, diff_base: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    limit_to_files = get_changed_files(diff_base) if diff_base else None
    run_scoring(path, agent, fix, badge, report_path, limit_to_files=limit_to_files)

@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save the report to a Markdown file.")
def advise(path: str, output_file: Optional[str]) -> None:
    """Generates a Markdown report with actionable advice based on Agent Physics."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    
    # We use 'generic' profile for advisor mode as it's about physics, not specific agent constraints
    results = analyzer.perform_analysis(path, "generic")
    
    # Convert directory_stats back to dict for report generator
    entropy_stats = {d['path']: d['file_count'] for d in results.get('directory_stats', [])}

    report_md = report.generate_advisor_report(
        stats=results['file_results'],
        dependency_stats=results.get('dep_analysis', {}).get('god_modules', {}), # This is pre-filtered > 50, which is fine
        entropy_stats=entropy_stats,
        cycles=results.get('dep_analysis', {}).get('cycles', [])
    )

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        console.print(f"[bold green]Advisor Report saved to {output_file}[/bold green]")
    else:
        console.print(report_md)

if __name__ == "__main__":
    cli()