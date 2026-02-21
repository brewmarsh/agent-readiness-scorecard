import os
import sys
import subprocess
import copy
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional, Union, cast
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

# Import core modules
from . import analyzer, report, auditor
from .prompt_analyzer import PromptAnalyzer
from .config import load_config
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge
from .types import AnalysisResult, AdvisorFileResult, FileAnalysisResult, Profile, Thresholds

console = Console()

# --- VERSION SETUP ---
try:
    __version__ = version("agent-scorecard")
except PackageNotFoundError:
    __version__ = "0.0.0"


# --- CLI DEFINITION ---
class DefaultGroup(click.Group):
    def resolve_command(self, ctx: click.Context, args: List[str]) -> Any:
        """Resolves the command, defaulting to 'score' if no command matches."""
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and not args[0].startswith("-"):
                args.insert(0, "score")
            elif not args:
                args.insert(0, "score")
            return super().resolve_command(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main entry point for the agent-scorecard CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(".")


# --- HELPERS ---

def get_changed_files(base_ref: str = "origin/main") -> List[str]:
    """Uses git diff to return a list of changed Python files."""
    try:
        cmd = ["git", "diff", "--name-only", "--diff-filter=d", base_ref, "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [
            f
            for f in result.stdout.splitlines()
            if f.endswith(".py") and os.path.exists(f)
        ]
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning: git diff failed (exit code {e.returncode}). Scoring all files.[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]Warning: Unexpected error checking git diff: {e}[/yellow]")
        return []


def _print_environment_health(
    path: str, results: AnalysisResult, verbosity: str
) -> None:
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
    status = f"{entropy['avg_files']:.1f} files/dir"
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        status = f"Max {entropy['max_files']} files/dir"
    color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{color}]{status}[/{color}]")

    tokens = auditor.check_critical_context_tokens(path)
    t_color = "red" if tokens["alert"] else "green"
    health_table.add_row("Critical Token Count", f"[{t_color}]{tokens['token_count']:,} tokens[/]")

    if results.get("dep_analysis", {}).get("cycles"):
        health_table.add_row("Circular Dependencies", f"[red]DETECTED ({len(results['dep_analysis']['cycles'])})[/red]")
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)
    if not health["agents_md"] and verbosity != "quiet":
        console.print("[bold red]Missing Critical Agent Docs: AGENTS.md[/bold red]")
    console.print("")


def _print_project_issues(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints systemic project issues (God Modules, Cycles) using QA bullets."""
    if verbosity == "quiet":
        return

    issues = results.get("project_issues", [])
    if issues:
        console.print(Panel("[bold red]Project Issues Detected[/bold red]", expand=False))
        for issue in issues:
            console.print(f"[red]• {issue}[/red]")
        console.print("")


def _print_file_analysis(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
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
        console.print("[green]All files passed![/green]")


def _generate_artifacts(
    results: Union[Dict[str, Any], AnalysisResult],
    path: str,
    profile: Profile,
    badge: bool,
    report_path: Optional[str],
    thresholds: Optional[Thresholds],
    verbosity: str,
) -> None:
    """Handles the production of external score reports and badges."""
    if badge:
        try:
            with open("agent_score.svg", "w", encoding="utf-8") as f:
                f.write(generate_badge(results["final_score"]))
            if verbosity != "quiet":
                console.print("[bold green][Generated][/bold green] Badge saved to ./agent_score.svg")
        except OSError as e:
            console.print(f"[red]Error saving badge: {e}[/red]")

    if report_path:
        try:
            content = report.generate_markdown_report(
                cast(List[FileAnalysisResult], results["file_results"]),
                results["final_score"], path, profile, thresholds=thresholds, verbosity=verbosity
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(content)
            if verbosity != "quiet":
                console.print(f"[bold green]Report saved to {report_path}[/bold green]")
        except OSError as e:
            console.print(f"[red]Error saving report: {e}[/red]")


# --- COMMANDS ---

def run_scoring(
    path: str, agent: str, fix: bool, badge: bool, report_path: Optional[str],
    limit_to_files: Optional[List[str]] = None, verbosity: str = "summary",
    thresholds: Optional[Dict[str, Any]] = None,
) -> None:
    """Orchestrator for the scoring process."""
    if agent not in PROFILES:
        console.print(f"[yellow]Unknown agent profile: {agent}. using generic.[/yellow]")
        agent = "generic"

    profile = cast(Profile, copy.deepcopy(PROFILES[agent]))
    if thresholds:
        profile.setdefault("thresholds", {}).update(thresholds)

    if verbosity != "quiet":
        console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}", expand=False))

    if fix:
        apply_fixes(path, profile)

    results = analyzer.perform_analysis(path, agent, limit_to_files=limit_to_files, thresholds=thresholds)

    _print_environment_health(path, results, verbosity)
    _print_project_issues(results, verbosity)
    _print_file_analysis(results, verbosity)

    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]")

    _generate_artifacts(results, path, profile, badge, report_path, thresholds, verbosity)

    if results["final_score"] < 70 or results.get("missing_docs"):
        sys.exit(1)


@cli.command(name="check-prompts")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, allow_dash=True))
@click.option("--plain", is_flag=True, help="Output raw score for CI.")
def check_prompts(input_path: str, plain: bool) -> None:
    """Analyzes prompts for persona, CoT, and delimiter hygiene."""
    try:
        content = sys.stdin.read() if input_path == "-" else open(input_path, "r", encoding="utf-8").read()
    except OSError as e:
        console.print(f"[red]Error reading prompt file: {e}[/red]")
        sys.exit(1)

    result = PromptAnalyzer().analyze(content)
    score = result["score"]

    if plain:
        click.echo(f"Score: {score}/100")
        for imp in result.get("improvements", []): click.echo(f"- {imp}")
    else:
        table = Table(title=f"Prompt Analysis: {os.path.basename(input_path) if input_path != '-' else 'Stdin'}")
        table.add_column("Heuristic", style="cyan")
        table.add_column("Status", justify="right")
        for key, passed in result.get("results", {}).items():
            status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
            table.add_row(key.replace("_", " ").title(), status)
        console.print(table)
        color = "green" if score >= 80 else "red"
        console.print(f"\nScore: [bold {color}]{score}/100[/bold {color}]")
        if result.get("improvements"):
            console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            for imp in result["improvements"]: console.print(f"💡 {imp}")

    if score < 80: sys.exit(1)


@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.pass_context
def fix(ctx: click.Context, path: str, agent: str) -> None:
    """Automatically fix common issues using configuration thresholds."""
    cfg = load_config(path)
    if agent not in PROFILES: agent = "generic"
    profile = cast(Profile, copy.deepcopy(PROFILES[agent]))
    if cfg.get("thresholds"): profile.setdefault("thresholds", {}).update(cfg["thresholds"])

    console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
    apply_fixes(path, profile)
    console.print("[bold green]Fixes applied![/bold green]")


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
@click.option("--report", "report_path", type=click.Path(), help="Save Markdown report.")
@click.option("--diff", "diff_base", help="Score only changed files.")
@click.option("--verbosity", type=click.Choice(["quiet", "summary", "detailed"]), help="Override verbosity.")
@click.pass_context
def score(ctx: click.Context, path: str, agent: str, fix: bool, badge: bool, report_path: str, diff_base: str, verbosity: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    limit_to_files = get_changed_files(diff_base) if diff_base else None
    run_scoring(path, agent, fix, badge, report_path, limit_to_files, final_verbosity, cfg.get("thresholds"))


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown.")
@click.pass_context
def advise(ctx: click.Context, path: str, output_file: Optional[str]) -> None:
    """Detailed advice based on Agent Physics using absolute paths for CI reliability."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    if output_file: output_file = os.path.abspath(output_file)
    cfg = load_config(path)
    results = analyzer.perform_analysis(path, "generic", thresholds=cfg.get("thresholds"))
    
    stats = []
    for res in results.get("file_results", []):
        tokens_info = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))
        m_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0.0])
        stats.append({**res, "acl": m_acl, "tokens": tokens_info["token_count"]})

    report_md = report.generate_advisor_report(
        stats=stats, dependency_stats=results.get("dep_analysis", {}).get("god_modules", {}),
        entropy_stats={d["path"]: d["file_count"] for d in results.get("directory_stats", [])},
        cycles=results.get("dep_analysis", {}).get("cycles", [])
    )

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f: f.write(report_md)
        console.print(f"[bold green]Advisor Report saved to {output_file}[/bold green]")
    else:
        console.print(Markdown(report_md))


if __name__ == "__main__":
    cli()