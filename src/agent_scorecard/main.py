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

# Import core modules
from . import analyzer, report, auditor
from .prompt_analyzer import PromptAnalyzer
from .config import load_config
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge
from .types import AnalysisResult, AdvisorFileResult

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
def cli() -> None:
    """Main entry point for the agent-scorecard CLI."""
    pass


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
        console.print(
            f"[yellow]Warning: git diff failed (exit code {e.returncode}). Scoring all files instead.[/yellow]"
        )
        return []
    except Exception as e:
        console.print(
            f"[yellow]Warning: Unexpected error while checking git diff: {e}[/yellow]"
        )
        return []


def _print_environment_health(
    path: str, results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the environment health table if verbosity allows."""
    if verbosity == "quiet":
        return

    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)
    health_table.add_row(
        "AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]"
    )
    health_table.add_row(
        "Linter Config",
        "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]",
    )
    health_table.add_row(
        "Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]"
    )

    entropy = auditor.check_directory_entropy(path)
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        entropy_status = f"Max {entropy['max_files']} files/dir"
        entropy_label = "WARN"
    else:
        entropy_status = f"{entropy['avg_files']:.1f} files/dir"
        entropy_label = "WARN" if entropy["warning"] else "PASS"

    entropy_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row(
        "Directory Entropy",
        f"[{entropy_color}]{entropy_label} ({entropy_status})[/{entropy_color}]",
    )

    tokens_check = auditor.check_critical_context_tokens(path)
    token_status = f"{tokens_check['token_count']:,} tokens"
    health_table.add_row(
        "Critical Token Count",
        f"[{'red' if tokens_check['alert'] else 'green'}]{'ALERT' if tokens_check['alert'] else 'PASS'} ({token_status})[/]",
    )

    if results.get("dep_analysis", {}).get("cycles"):
        health_table.add_row(
            "Circular Dependencies",
            f"[red]DETECTED ({len(results['dep_analysis']['cycles'])})[/red]",
        )
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)

    if not health["agents_md"]:
        console.print("[bold red]Missing Critical Agent Docs: AGENTS.md[/bold red]")
    console.print("")


def _print_project_issues(results: Union[Dict[str, Any], AnalysisResult]) -> None:
    """Prints project-wide issues found during analysis."""
    if results.get("project_issues"):
        console.print("\n[bold red]Project Issues Detected:[/bold red]")
        for issue in results["project_issues"]:
            console.print(f"- {issue}")


def _print_score(results: Union[Dict[str, Any], AnalysisResult]) -> None:
    """Prints the final formatted agent score."""
    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(
        f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]"
    )


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
        if verbosity == "summary" and res["score"] == 100:
            continue

        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(
            res["file"],
            f"[{status_color}]{res['score']}[/{status_color}]",
            res["issues"],
        )
        has_rows = True

    if has_rows:
        console.print(table)
    elif verbosity == "summary":
        console.print("[green]All files passed with perfect scores![/green]")


def _generate_artifacts(
    results: Union[Dict[str, Any], AnalysisResult],
    path: str,
    profile: Dict[str, Any],
    badge: bool,
    report_path: Optional[str],
    thresholds: Optional[Dict[str, Any]],
    verbosity: str,
) -> None:
    """Handles the production of external score reports and badges."""
    if badge:
        output_path = "agent_score.svg"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(generate_badge(results["final_score"]))
            if verbosity != "quiet":
                console.print(
                    f"[bold green][Generated][/bold green] Badge saved to ./{output_path}"
                )
        except OSError as e:
            console.print(f"[red]Error saving badge: {e}[/red]")

    if report_path:
        try:
            report_content = report.generate_markdown_report(
                cast(List[Dict[str, Any]], results["file_results"]),
                results["final_score"],
                path,
                profile,
                results.get("project_issues"),
                thresholds=thresholds,
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            if verbosity != "quiet":
                console.print(f"[bold green]Report saved to {report_path}[/bold green]")
        except OSError as e:
            console.print(f"[red]Error saving report: {e}[/red]")


# --- COMMANDS ---


def run_scoring(
    path: str,
    agent: str,
    fix: bool,
    badge: bool,
    report_path: Optional[str],
    limit_to_files: Optional[List[str]] = None,
    verbosity: str = "summary",
    thresholds: Optional[Dict[str, Any]] = None,
) -> None:
    """Orchestrator for the scoring process."""
    if agent not in PROFILES:
        console.print(
            f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]"
        )
        agent = "generic"

    profile = copy.deepcopy(PROFILES[agent])
    if thresholds:
        cast(Dict[str, Any], profile.setdefault("thresholds", {})).update(thresholds)

    if fix:
        console.print(
            Panel(
                f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
                expand=False,
            )
        )
        apply_fixes(path, profile)
        console.print("")

    results = analyzer.perform_analysis(
        path,
        agent,
        limit_to_files=limit_to_files,
        profile=profile,
        thresholds=thresholds,
    )

    if verbosity != "quiet":
        console.print(
            Panel(
                f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}",
                expand=False,
            )
        )

    _print_environment_health(path, results, verbosity)
    _print_file_analysis(results, verbosity)
    _print_project_issues(results)
    _print_score(results)
    _generate_artifacts(
        results, path, profile, badge, report_path, thresholds, verbosity
    )

    if results["final_score"] < 70:
        sys.exit(1)


@cli.command(name="check-prompts")
@click.argument(
    "input_path", type=click.Path(exists=True, dir_okay=False, allow_dash=True)
)
@click.option("--plain", is_flag=True, help="Output raw score and suggestions for CI.")
def check_prompts(input_path: str, plain: bool) -> None:
    """Analyzes prompts for persona, CoT, and delimiter hygiene."""
    try:
        content = (
            sys.stdin.read()
            if input_path == "-"
            else open(input_path, "r", encoding="utf-8").read()
        )
    except OSError as e:
        console.print(f"[red]Error reading prompt file: {e}[/red]")
        sys.exit(1)

    analyzer_inst = PromptAnalyzer()
    result = analyzer_inst.analyze(content)
    score = result["score"]

    if plain:
        click.echo(f"Score: {score}")
        if result.get("improvements"):
            click.echo("Refactored Suggestions:")
            for sug in result["improvements"]:
                click.echo(f"- {sug}")
        if score < 80:
            click.echo("FAILED: Prompt score too low.")
    else:
        table = Table(
            title=f"Prompt Analysis: {os.path.basename(input_path) if input_path != '-' else 'Stdin'}"
        )
        table.add_column("Heuristic", style="cyan")
        table.add_column("Status", justify="right")
        for key in [
            "role_definition",
            "cognitive_scaffolding",
            "delimiter_hygiene",
            "few_shot",
            "negative_constraints",
        ]:
            if key in result.get("results", {}):
                status = (
                    "[green]✅ PASS[/green]"
                    if result["results"][key]
                    else "[red]❌ FAIL[/red]"
                )
                table.add_row(key.replace("_", " ").title(), status)
        console.print(table)
        color = "green" if score >= 80 else "red"
        console.print(f"\nScore: [bold {color}]{score}/100[/bold {color}]")
        if score >= 80:
            console.print("[bold green]PASSED: Prompt is optimized![/bold green]")

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
    """Automatically fix common issues using CRAFT framework prompts."""
    cfg = load_config(path)
    profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))
    if cfg.get("thresholds"):
        cast(Dict[str, Any], profile.setdefault("thresholds", {})).update(
            cast(Dict[str, Any], cfg["thresholds"])
        )

    console.print(
        Panel(
            f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
            expand=False,
        )
    )
    apply_fixes(path, profile)
    console.print("[bold green]Fixes applied![/bold green]")


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
@click.option(
    "--report", "report_path", type=click.Path(), help="Save Markdown report."
)
@click.option("--diff", "diff_base", help="Score only changed files.")
@click.option(
    "--verbosity",
    type=click.Choice(["quiet", "summary", "detailed"]),
    help="Override verbosity.",
)
def score(
    path: str,
    agent: str,
    fix: bool,
    badge: bool,
    report_path: str,
    diff_base: str,
    verbosity: str,
) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    thresholds = cast(Dict[str, Any], cfg.get("thresholds"))
    limit_to_files = get_changed_files(diff_base) if diff_base else None
    run_scoring(
        path,
        agent,
        fix,
        badge,
        report_path,
        limit_to_files=limit_to_files,
        verbosity=final_verbosity,
        thresholds=thresholds,
    )


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown."
)
def advise(path: str, output_file: Optional[str]) -> None:
    """Detailed advice based on Agent Physics using absolute paths for CI reliability."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))

    if output_file:
        output_file = os.path.abspath(output_file)

    cfg = load_config(path)
    try:
        results = analyzer.perform_analysis(
            path, "generic", thresholds=cast(Dict[str, Any], cfg.get("thresholds"))
        )
        stats: List[AdvisorFileResult] = []
        for res in results.get("file_results", []):
            full_path = os.path.join(path, res["file"])
            if not os.path.exists(full_path):
                full_path = res["file"]

            tokens_info = auditor.check_critical_context_tokens(full_path)

            # Pull max ACL and complexity from function metrics for Advisor richness
            max_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0.0])
            max_comp = max(
                [m["complexity"] for m in res.get("function_metrics", [])]
                or [res.get("complexity", 0.0)]
            )

            stats.append(
                cast(
                    AdvisorFileResult,
                    {
                        **res,
                        "acl": max_acl,
                        "complexity": max_comp,
                        "tokens": tokens_info["token_count"],
                    },
                )
            )

        entropy_stats = {
            d["path"]: d["file_count"] for d in results.get("directory_stats", [])
        }
        report_md = report.generate_advisor_report(
            stats=cast(List[Dict[str, Any]], stats),
            dependency_stats=results.get("dep_analysis", {}).get("god_modules", {}),
            entropy_stats=entropy_stats,
            cycles=results.get("dep_analysis", {}).get("cycles", []),
        )

    except Exception as e:
        report_md = f"# Agent Advisor Report\n\nError during analysis: {str(e)}"
        console.print(f"[red]Error during analysis: {e}[/red]")

    if output_file:
        # GUARANTEE: Output file is created even if stats is empty to prevent downstream CI failure
        final_output = (
            report_md if stats else "# Agent Advisor Report\n\nNo Python files found."
        )
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_output)
            console.print(
                f"[bold green]Advisor Report saved to {output_file}[/bold green]"
            )
        except OSError as e:
            console.print(
                f"[red]Error saving advisor report to {output_file}: {e}[/red]"
            )
    else:
        from rich.markdown import Markdown

        console.print(Markdown(report_md))


if __name__ == "__main__":
    cli()
