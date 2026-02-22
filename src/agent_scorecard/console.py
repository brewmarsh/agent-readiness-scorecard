from typing import List, Dict, Any, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from . import auditor
from .types import AnalysisResult
from .prompt_analyzer import PromptAnalysisResult

console = Console()


def print_project_issues(project_issues: List[str], verbosity: str) -> None:
    """
    Prints systemic project issues using a high-visibility bulleted list.

    Args:
        project_issues (List[str]): List of detected project issues.
        verbosity (str): Output verbosity level.

    Returns:
        None
    """
    if not project_issues or verbosity == "quiet":
        return

    console.print("\n[bold yellow]Project Issues Detected:[/bold yellow]")
    for issue in project_issues:
        console.print(f"- [red]{issue}[/red]")


def print_environment_health(
    path: str, results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """
    Prints the environment health table.

    Args:
        path (str): The project path.
        results (Union[Dict[str, Any], AnalysisResult]): Analysis results.
        verbosity (str): Output verbosity level.

    Returns:
        None
    """
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


def print_file_analysis(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """
    Prints the file analysis table based on verbosity.

    Args:
        results (Union[Dict[str, Any], AnalysisResult]): Analysis results.
        verbosity (str): Output verbosity level.

    Returns:
        None
    """
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
        color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{color}]{res['score']}[/{color}]", res["issues"])
        has_rows = True

    if has_rows:
        console.print(table)


def print_prompt_analysis(
    path: str, result: PromptAnalysisResult, plain: bool
) -> None:
    """
    Prints the prompt analysis result.

    Args:
        path (str): Path to the prompt file.
        result (PromptAnalysisResult): The analysis result.
        plain (bool): Whether to use plain output for CI.

    Returns:
        None
    """
    if plain:
        print(f"Prompt Analysis: {path}")
        print(f"Score: {result['score']}/100\n")
        for k, passed in result["results"].items():
            print(f"{k.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}")

        if result["improvements"]:
            # RESOLUTION: Adopted Beta branch bulleted list and newline formatting
            print("\nRefactored Suggestions:")
            for imp in result["improvements"]:
                print(f"- {imp}")

        if result["score"] >= 80:
            print("PASSED: Prompt is optimized!")
        else:
            print("FAILED: Prompt score too low.")
    else:
        console.print(
            Panel(f"[bold cyan]Prompt Analysis: {path}[/bold cyan]", expand=False)
        )
        style = "green" if result["score"] >= 80 else "red"
        console.print(f"Score: [bold {style}]{result['score']}/100[/bold {style}]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric")
        table.add_column("Status")

        for k, passed in result["results"].items():
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(k.replace("_", " ").title(), status)

        console.print(table)

        if result["improvements"]:
            console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            for imp in result["improvements"]:
                console.print(f"💡 {imp}")

        if result["score"] >= 80:
            console.print("\n[bold green]PASSED: Prompt is optimized![/bold green]")
