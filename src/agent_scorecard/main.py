import os
import sys
import subprocess
import click
from typing import List, Optional
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

    def resolve_command(self, ctx, args):
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


def run_scoring(
    path: str,
    agent: str,
    fix: bool,
    badge: bool,
    report_path: str,
    limit_to_files: Optional[List[str]] = None,
) -> None:
    """Helper to run the scoring logic."""
    if agent not in PROFILES:
        console.print(
            f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]"
        )
        agent = "generic"
    profile = PROFILES[agent]

    if fix:
        console.print(
            Panel(
                f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
                expand=False,
            )
        )
        apply_fixes(path, profile)
        console.print("")

    # Run Analysis
    results = analyzer.perform_analysis(path, agent, limit_to_files=limit_to_files)
    console.print(
        Panel(
            f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}",
            expand=False,
        )
    )

    # 1. Environment Health & Auditor Checks (Preserved from Beta Branch)
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
    else:
        entropy_status = f"{entropy['avg_files']:.1f} files/dir"

    entropy_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row(
        "Directory Entropy", f"[{entropy_color}]{entropy_status}[/{entropy_color}]"
    )

    tokens = auditor.check_critical_context_tokens(path)
    token_status = f"{tokens['token_count']:,} tokens"
    if tokens["alert"]:
        health_table.add_row(
            "Critical Token Count", f"[red]ALERT ({token_status})[/red]"
        )
    else:
        health_table.add_row(
            "Critical Token Count", f"[green]PASS ({token_status})[/green]"
        )

    # Dependency Analysis Cycle Check
    if results.get("dep_analysis", {}).get("cycles"):
        health_table.add_row(
            "Circular Dependencies",
            f"[red]DETECTED ({len(results['dep_analysis']['cycles'])})[/red]",
        )
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)
    console.print("")  # Spacing

    # 2. Critical Docs Check (Redundant but kept for output consistency)
    if results["missing_docs"]:
        penalty = len(results["missing_docs"]) * 15
        console.print(
            f"[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(results['missing_docs'])} (-{penalty} pts)\n"
        )

    # Project Issues (God Modules, High Entropy, etc.)
    for issue in results.get("project_issues", []):
        if "Missing Critical Agent Docs" in issue:
            continue
        console.print(f"[bold yellow]⚠ {issue}[/bold yellow]")
    if results.get("project_issues"):
        console.print("")  # Spacing

    # 3. File Table
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    for res in results["file_results"]:
        status_color = "green" if res["score"] >= 70 else "red"
        table.add_row(
            res["file"],
            f"[{status_color}]{res['score']}[/{status_color}]",
            res["issues"],
        )

    console.print(table)
    console.print(f"\n[bold]Final Agent Score: {results['final_score']:.1f}/100[/bold]")

    # 4. Badge Generation
    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(results["final_score"])
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(
            f"[bold green][Generated][/bold green] Badge saved to ./{output_path}"
        )
        console.print(
            f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})"
        )

    # 5. Report Generation
    if report_path:
        report_content = report.generate_markdown_report(
            results["file_results"],
            results["final_score"],
            path,
            profile,
            results.get("project_issues"),
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if results["final_score"] < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")


@cli.command(name="check-prompts")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--plain", is_flag=True, help="Output plain text without colors or tables."
)
def check_prompts(path: str, plain: bool) -> None:
    """Statically analyze text prompts for LLM best practices."""
    analyzer_inst = PromptAnalyzer()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    analysis = analyzer_inst.analyze(content)
    score = analysis["score"]

    if plain:
        click.echo(f"Prompt Score: {score}/100")
        if score < 80:
            click.echo("\nRefactored Suggestions:")
            for imp in analysis["improvements"]:
                click.echo(f"- {imp}")
            click.echo("\nFAILED: Prompt does not meet quality standards.")
            sys.exit(1)
        else:
            click.echo("\nPASSED: Prompt is optimized!")
        return

    table = Table(title=f"Prompt Analysis: {os.path.basename(path)}")
    table.add_column("Heuristic", style="cyan")
    table.add_column("Status", justify="right")

    # Order of display
    order = [
        "role_definition",
        "cognitive_scaffolding",
        "delimiter_hygiene",
        "few_shot",
        "negative_constraints",
    ]
    for key in order:
        if key in analysis["results"]:
            passed = analysis["results"][key]
            name = key.replace("_", " ").title()
            status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
            table.add_row(name, status)

    console.print(table)
    console.print(f"\n[bold]Prompt Score: {score}/100[/bold]")

    if score < 80:
        console.print("\n[bold yellow]Refactored Suggestions:[/bold yellow]")
        for imp in analysis["improvements"]:
            console.print(f"- {imp}")
        console.print(
            "\n[bold red]FAILED: Prompt does not meet quality standards.[/bold red]"
        )
        sys.exit(1)
    else:
        console.print("\n[bold green]PASSED: Prompt is optimized![/bold green]")


@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
def fix(path: str, agent: str) -> None:
    """Automatically fix common issues in the codebase."""
    if agent not in PROFILES:
        console.print(
            f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]"
        )
        agent = "generic"
    profile = PROFILES[agent]

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
@click.option(
    "--agent", default="generic", help="Profile to use: generic, jules, copilot."
)
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
@click.option(
    "--report",
    "report_path",
    type=click.Path(),
    help="Save the report to a Markdown file.",
)
@click.option("--diff", "diff_base", help="Only score files changed vs this git ref.")
def score(
    path: str, agent: str, fix: bool, badge: bool, report_path: str, diff_base: str
) -> None:
    """Scores a codebase based on AI-agent compatibility."""
    limit_to_files = None
    if diff_base:
        limit_to_files = get_changed_files(diff_base)
        if not limit_to_files:
            console.print(
                f"[bold yellow]No changed Python files found against {diff_base}. Scoring all files.[/bold yellow]"
            )

    run_scoring(path, agent, fix, badge, report_path, limit_to_files=limit_to_files)


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    "output_file",
    type=click.Path(),
    help="Save the report to a Markdown file.",
)
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
            max_acl = max((f["acl"] for f in func_stats), default=0)

            stats.append(
                {
                    "file": os.path.relpath(
                        filepath,
                        start=path if os.path.isdir(path) else os.path.dirname(path),
                    ),
                    "loc": loc,
                    "complexity": complexity,
                    "acl": max_acl,
                    "tokens": auditor.check_critical_context_tokens(filepath)[
                        "token_count"
                    ],
                }
            )

        # Dependency Analysis
        graph = analyzer.get_import_graph(path)
        inbound = analyzer.get_inbound_imports(graph)
        cycles = analyzer.detect_cycles(graph)

        # Entropy Analysis
        entropy = auditor.get_crowded_directories(path)

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
