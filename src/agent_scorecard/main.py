import os
import ast
import click
from rich.console import Console
from rich.table import Table
import mccabe

console = Console()

def scan_directory(path):
    py_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def get_complexity_stats(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0
    return sum(complexities) / len(complexities)

def get_type_hint_stats(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0, 0

    function_count = 0
    typed_function_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_count += 1
            is_typed = False
            if node.returns:
                is_typed = True
            else:
                # Check args
                if hasattr(node, 'args'):
                    for arg in node.args.args:
                        if arg.annotation:
                            is_typed = True
                            break
                    if not is_typed and node.args.kwonlyargs:
                         for arg in node.args.kwonlyargs:
                            if arg.annotation:
                                is_typed = True
                                break
                    if not is_typed and node.args.vararg and node.args.vararg.annotation:
                        is_typed = True
                    if not is_typed and node.args.kwarg and node.args.kwarg.annotation:
                        is_typed = True

            if is_typed:
                typed_function_count += 1

    return typed_function_count, function_count

def score_file(filepath):
    score = 100
    details = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return 0, [f"Error reading file: {e}"]

    # Lines of Code
    lines = code.splitlines()
    loc = len(lines)
    if loc > 200:
        deduction = (loc - 200) // 10
        score -= deduction
        details.append(f"LOC {loc} > 200 (-{deduction})")

    # Complexity
    avg_complexity = get_complexity_stats(code)
    if avg_complexity > 10:
        score -= 5
        details.append(f"Avg Complexity {avg_complexity:.1f} > 10 (-5)")

    # Type Hints
    typed, total = get_type_hint_stats(code)
    if total > 0:
        ratio = typed / total
        if ratio < 0.5:
            score -= 20
            details.append(f"Type Hints {ratio:.0%} < 50% (-20)")

    return score, details

@click.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def cli(path):
    """Analyze codebases for AI-Agent Friendliness."""
    if os.path.isfile(path):
        files = [path]
    else:
        files = scan_directory(path)

    if not files:
        console.print("No python files found.")
        return

    table = Table(title="Agent Scorecard")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")
    table.add_column("Details", style="green")

    failed = False

    for file in files:
        score, details = score_file(file)
        color = "green" if score >= 70 else "red"
        if score < 70:
            failed = True

        table.add_row(file, f"[{color}]{score}[/{color}]", ", ".join(details))

    console.print(table)

    if failed:
        console.print("[bold red]Fail[/bold red]")
        import sys
        sys.exit(1)
    else:
        console.print("[bold green]Pass[/bold green]")

if __name__ == "__main__":
    cli()
