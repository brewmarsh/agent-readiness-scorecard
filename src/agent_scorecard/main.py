import os
import sys
import subprocess
import click
from importlib.metadata import version, PackageNotFoundError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules
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

def get_changed_files(base_ref: str = "origin/main") -> list:
    """Uses git diff to return a list of changed Python files."""
    try:
        cmd = ["git", "diff", "--name-only", "--diff-filter=d", base_ref, "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [f for f in result.stdout.splitlines() if f.endswith(".py") and os.path.exists(f)]
    except Exception:
        return []

def run_scoring(path: str, agent: str, fix: bool, badge: bool, report_path: str, limit_to_files: list = None, verbosity: str = "summary", thresholds: dict = None) -> None:
    """Helper to run the scoring logic."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"
    profile = PROFILES[agent]

    if fix:
        if verbosity != "quiet":
            console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)
        if verbosity != "quiet":
            console.print("")

    # Run Analysis
    results = analyzer.perform_analysis(path, agent, limit_to_files=limit_to_files, thresholds=thresholds)

    if verbosity != "quiet":
        console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 1. Environment Health & Auditor Checks
    if verbosity != "quiet":
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
        else:
            entropy_status = f"{entropy['avg_files']:.1f} files/dir"

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
        console.print("")

    # 2. File Table
    if verbosity != "quiet":
        table = Table(title="File Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Issues", style="magenta")

        has_rows = False
        for res in results["file_results"]:
            status_color = "green" if res["score"] >= 70 else "red"

            # summary mode: only show failing files
            if verbosity == "summary" and res["score"] >= 70:
                continue

            table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])
            has_rows = True

        if has_rows:
            console.print(table)
        elif verbosity == "summary":
            console.print("[green]All files passed Agent Readiness checks.[/green]")

    if verbosity != "quiet" and results.get("project_issues"):
        console.print("\n[bold yellow]Project-Wide Issues:[/bold yellow]")
        for issue in results["project_issues"]:
            console.print(f"⚠️ {issue}")

    # Final Score
    score_color = "green" if results['final_score'] >= 70 else "red"
    console.print(f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]")

    if verbosity == "quiet" and results.get("project_issues"):
        for issue in results["project_issues"]:
            console.print(f"[bold red]CRITICAL:[/bold red] {issue}")

    # 3. Artifact Generation
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
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if results["final_score"] < 70:
        sys.exit(1)

@cli.command(name="check-prompts")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, allow_dash=True))
@click.option("--plain", is_flag=True, help="Output raw score and suggestions for CI.")
def check_prompts(input_path, plain):
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

        if score == 100:
            console.print("[green]PASSED: Prompt is optimized![/green]")

        if result.get("improvements"):
            console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            for imp in result["improvements"]:
                console.print(f"💡 {imp}")

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
@click.option("--verbosity", type=click.Choice(["quiet", "summary", "detailed"]), help="Override verbosity level.")
def score(path: str, agent: str, fix: bool, badge: bool, report_path: str, diff_base: str, verbosity: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    cfg = config.load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    thresholds = cfg.get("thresholds")

    limit_to_files = get_changed_files(diff_base) if diff_base else None
    run_scoring(path, agent, fix, badge, report_path, limit_to_files=limit_to_files, verbosity=final_verbosity, thresholds=thresholds)

@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save the report to a Markdown file.")
def advise(path, output_file):
    """Generates a Markdown report with actionable advice based on Agent Physics."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    
    results = analyzer.perform_analysis(path, "generic")
    
    # Prepare stats for the advisor report
    stats = []
    for res in results["file_results"]:
        max_acl = max([m["acl"] for m in res["function_metrics"]] or [0])
        # Token count is needed for advisor report
        tokens_info = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))

        stats.append({
            "file": res["file"],
            "acl": max_acl,
            "complexity": res["complexity"],
            "loc": res["loc"],
            "tokens": tokens_info["token_count"]
        })

    graph = analyzer.get_import_graph(path)
    inbound = analyzer.get_inbound_imports(graph)
    cycles = analyzer.detect_cycles(graph)

    # Directory Entropy via Auditor
    entropy_stats = {}
    entropy = auditor.get_crowded_directories(path, threshold=50)
    for p, count in entropy.items():
        entropy_stats[p] = count

    report_md = report.generate_advisor_report(stats, inbound, entropy_stats, cycles)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        console.print(f"[bold green]Advisor report saved to {output_file}[/bold green]")
    else:
        console.print(report_md)

if __name__ == "__main__":
    cli()