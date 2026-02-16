import os
import sys
import subprocess
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import core modules
from . import analyzer, report, auditor, config
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
    def resolve_command(self, ctx: click.Context, args: List[str]) -> Any:
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

# --- HELPERS ---

def get_changed_files(base_ref: str = "origin/main") -> List[str]:
    """Uses git diff to return a list of changed Python files."""
    try:
        cmd = ["git", "diff", "--name-only", "--diff-filter=d", base_ref, "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [f for f in result.stdout.splitlines() if f.endswith(".py") and os.path.exists(f)]
    except Exception:
        return []

def _print_environment_health(path: str, results: Dict[str, Any], verbosity: str) -> None:
    """Prints the environment health table if verbosity allows."""
    if verbosity == "quiet":
        return

    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)
    health_table.add_row("AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]")
    health_table.add_row("Linter Config", "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]")
    health_table.add_row("Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]")

    entropy = auditor.check_directory_entropy(path)
    entropy_status = f"{entropy['avg_files']:.1f} files/dir"
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        entropy_status = f"Max {entropy['max_files']} files/dir"

    entropy_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{entropy_color}]{entropy_status}[/{entropy_color}]")

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
    
    # Explicit alerts for critical issues
    if not health["agents_md"]:
        console.print("[bold red]Missing Critical Agent Docs: AGENTS.md[/bold red]")
    if entropy["warning"]:
        console.print("[bold yellow]High Directory Entropy warning[/bold yellow]")
    console.print("")

def _print_file_analysis(results: Dict[str, Any], verbosity: str) -> None:
    """Prints the file analysis table based on verbosity settings."""
    if verbosity == "quiet":
        return

    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    has_rows = False
    for res in results["file_results"]:
        if verbosity == "summary" and res["score"] >= 70:
            continue
        
        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])
        has_rows = True

    if has_rows:
        console.print(table)
    elif verbosity == "summary":
        console.print("[green]All files passed Agent Readiness checks.[/green]")

    if results.get("project_issues"):
        console.print("\n[bold yellow]Project-Wide Issues:[/bold yellow]")
        for issue in results["project_issues"]:
            console.print(f"⚠️ {issue}")

    score_color = "green" if results['final_score'] >= 70 else "red"
    console.print(f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]")

def _generate_artifacts(results: Dict[str, Any], path: str, profile: Dict[str, Any], badge: bool, report_path: Optional[str], thresholds: Dict[str, Any], verbosity: str) -> None:
    """Handles generation of SVG badges and Markdown reports."""
    if badge:
        output_path = "agent_score.svg"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generate_badge(results["final_score"]))
        if verbosity != "quiet":
            console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")

    if report_path:
        report_content = report.generate_markdown_report(
            results["file_results"], results["final_score"], path, profile, results.get("project_issues"), thresholds=thresholds
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        if verbosity != "quiet":
            console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

# --- COMMANDS ---

def run_scoring(path: str, agent: str, fix: bool, badge: bool, report_path: Optional[str], limit_to_files: Optional[List[str]] = None, verbosity: str = "summary", thresholds: dict = None) -> None:
    """Orchestrator for the scoring process."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"
    profile = PROFILES[agent]

    if fix:
        if verbosity != "quiet":
            console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)

    results = analyzer.perform_analysis(path, agent, limit_to_files=limit_to_files, thresholds=thresholds)

    if verbosity != "quiet":
        console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    _print_environment_health(path, results, verbosity)
    _print_file_analysis(results, verbosity)
    _generate_artifacts(results, path, profile, badge, report_path, thresholds, verbosity)

    if results["final_score"] < 70:
        sys.exit(1)

@cli.command(name="check-prompts")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, allow_dash=True))
@click.option("--plain", is_flag=True, help="Output raw score and suggestions for CI.")
def check_prompts(input_path: str, plain: bool) -> None:
    """Analyzes prompts for persona, CoT, and delimiter hygiene."""
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
        for sug in result.get('improvements', []):
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
        if score >= 80:
            console.print("\n[bold green]PASSED: Prompt is optimized![/bold green]")

    if score < 80:
        sys.exit(1)

@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
@click.option("--report", "report_path", type=click.Path(), help="Save Markdown report.")
@click.option("--diff", "diff_base", help="Score only files changed vs this git ref.")
@click.option("--verbosity", type=click.Choice(["quiet", "summary", "detailed"]), help="Override verbosity.")
def score(path: str, agent: str, fix: bool, badge: bool, report_path: str, diff_base: str, verbosity: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    cfg = config.load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    thresholds = cfg.get("thresholds")

    limit_to_files = get_changed_files(diff_base) if diff_base else None
    run_scoring(path, agent, fix, badge, report_path, limit_to_files=limit_to_files, verbosity=final_verbosity, thresholds=thresholds)

@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown.")
def advise(path: str, output_file: Optional[str]) -> None:
    """Detailed advice based on Agent Physics."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    
    results = analyzer.perform_analysis(path, "generic")
    
    # Enrich file results with token counts for the advisor report
    stats = []
    for res in results["file_results"]:
        tokens_info = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))
        max_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0])
        
        stats.append({
            "file": res["file"],
            "acl": max_acl,
            "complexity": res["complexity"],
            "loc": res["loc"],
            "tokens": tokens_info["token_count"]
        })

    entropy_stats = {d['path']: d['file_count'] for d in results.get('directory_stats', [])}

    report_md = report.generate_advisor_report(
        stats=stats,
        dependency_stats=results.get('dep_analysis', {}).get('god_modules', {}),
        entropy_stats=entropy_stats,
        cycles=results.get('dep_analysis', {}).get('cycles', [])
    )

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        console.print(f"[bold green]Advisor Report saved to {output_file}[/bold green]")
    else:
        from rich.markdown import Markdown
        console.print(Markdown(report_md))

if __name__ == "__main__":
    cli()