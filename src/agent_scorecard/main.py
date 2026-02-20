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
    except Exception:
        return []


def _print_project_issues(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints critical project-level issues."""
    issues = results.get("project_issues", [])
    if issues:
        console.print(
            Panel("[bold red]Project Issues Detected[/bold red]", expand=False)
        )
        for issue in issues:
            console.print(f"[red]• {issue}[/red]")
        console.print("")


def _print_environment_health(
    path: str, results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the environment health table."""
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
    status = f"{entropy['avg_files']:.1f} files/dir"
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        status = f"Max {entropy['max_files']} files/dir"

    color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{color}]{status}[/{color}]")

    tokens = auditor.check_critical_context_tokens(path)
    t_color = "red" if tokens["alert"] else "green"
    health_table.add_row(
        "Critical Token Count", f"[{t_color}]{tokens['token_count']:,} tokens[/]"
    )

    console.print(health_table)
    console.print("")


def _print_file_analysis(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the file analysis table based on verbosity."""
    if verbosity != "quiet":
        table = Table(title="File Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Issues", style="magenta")

        has_rows = False
        for res in results["file_results"]:
            if verbosity == "summary" and res["score"] == 100:
                continue
            color = "green" if res["score"] >= 70 else "red"
            table.add_row(
                res["file"], f"[{color}]{res['score']}[/{color}]", res["issues"]
            )
            has_rows = True

        if has_rows:
            console.print(table)

    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(
        f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]"
    )


# --- COMMANDS ---


@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
def fix(path: str, agent: str) -> None:
    """Automatically fix common issues using configuration thresholds."""
    cfg = load_config(path)
    profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))

    # RESOLUTION: Use Beta branch casting for safe dict merging
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


@cli.command(name="check-prompts")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--plain", is_flag=True, help="Output plain text.")
def check_prompts(path: str, plain: bool) -> None:
    """Checks a prompt file for best practices."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        sys.exit(1)

    analyzer_inst = PromptAnalyzer()
    res = analyzer_inst.analyze(content)

    if plain:
        print(f"Score: {res['score']}")
        for imp in res["improvements"]:
            print(f"- {imp}")
    else:
        style = "green" if res["score"] >= 80 else "red"
        console.print(
            Panel(
                f"Prompt Score: [{style}]{res['score']}/100[/{style}]",
                title=f"Prompt Analysis: {os.path.basename(path)}",
                expand=False,
            )
        )

        for check, passed in res["results"].items():
            icon = "✅" if passed else "❌"
            name = check.replace("_", " ").title()
            console.print(f"{icon} {name}")

        if res["score"] >= 80:
            console.print("\n[bold green]PASSED: Prompt is optimized![/bold green]")

        if res["improvements"]:
            console.print("\n[bold]Improvements Needed:[/bold]")
            for imp in res["improvements"]:
                console.print(f"[yellow]• {imp}[/yellow]")

    if res["score"] < 80:
        sys.exit(1)


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option(
    "--report", "report_path", type=click.Path(), help="Save Markdown report."
)
@click.option(
    "--verbosity",
    type=click.Choice(["quiet", "summary", "detailed"]),
    help="Override verbosity.",
)
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
def score(
    path: str, agent: str, fix: bool, report_path: str, verbosity: str, badge: bool
) -> None:
    """Scores a codebase based on agent compatibility."""
    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")

    if final_verbosity != "quiet":
        console.print(
            Panel("[bold cyan]Running Agent Scorecard[/bold cyan]", expand=False)
        )

    if agent not in PROFILES:
        console.print(f"Unknown agent profile: {agent}. using generic.")

    thresholds = cast(Dict[str, Any], cfg.get("thresholds"))

    if fix:
        console.print(
            Panel(
                f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
                expand=False,
            )
        )
        profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))
        apply_fixes(path, profile)

    results = analyzer.perform_analysis(path, agent, thresholds=thresholds)

    _print_environment_health(path, results, final_verbosity)
    _print_project_issues(results, final_verbosity)
    _print_file_analysis(results, final_verbosity)

    if report_path:
        content = report.generate_markdown_report(
            cast(List[Dict[str, Any]], results["file_results"]),
            results["final_score"],
            path,
            PROFILES[agent],
            thresholds=thresholds,
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

    if badge:
        svg = generate_badge(results["final_score"])
        with open("agent_score.svg", "w", encoding="utf-8") as f:
            f.write(svg)
        console.print("[bold green]Badge saved to agent_score.svg[/bold green]")

    if results["final_score"] < 70:
        sys.exit(1)


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown."
)
def advise(path: str, output_file: Optional[str]) -> None:
    """Detailed advice based on Agent Physics using absolute paths for CI."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))

    cfg = load_config(path)
    results = analyzer.perform_analysis(
        path, "generic", thresholds=cast(Dict[str, Any], cfg.get("thresholds"))
    )

    # Enrichment loop for Advisor-specific token metrics
    stats: List[AdvisorFileResult] = []
    for res in results.get("file_results", []):
        tokens = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))
        m_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0.0])

        stats.append(
            cast(
                AdvisorFileResult,
                {**res, "acl": m_acl, "tokens": tokens["token_count"]},
            )
        )

    report_md = report.generate_advisor_report(
        stats=cast(List[Dict[str, Any]], stats),
        dependency_stats=results.get("dep_analysis", {}).get("god_modules", {}),
        entropy_stats={
            d["path"]: d["file_count"] for d in results.get("directory_stats", [])
        },
        cycles=results.get("dep_analysis", {}).get("cycles", []),
    )

    if output_file:
        dest = os.path.abspath(output_file)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(
                report_md if stats else "# Advisor Report\n\nNo Python files found."
            )
        console.print(f"[bold green]Report saved to {dest}[/bold green]")
    else:
        from rich.markdown import Markdown

        console.print(Markdown(report_md))


if __name__ == "__main__":
    cli()
