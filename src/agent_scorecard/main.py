import os
import ast
import click
import mccabe
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# --- AGENT PROFILES ---
PROFILES = {
    "generic": {
        "max_loc": 200,
        "max_complexity": 10,
        "min_type_coverage": 50,
        "required_files": ["README.md"],
        "description": "Standard cleanliness checks."
    },
    "jules": {
        "max_loc": 150,  # Stricter LOC for autonomy
        "max_complexity": 8,
        "min_type_coverage": 80,  # High typing requirement
        "required_files": ["agents.md", "instructions.md"],
        "description": "Strict typing and autonomy instructions."
    },
    "copilot": {
        "max_loc": 100,  # Very small chunks preferred
        "max_complexity": 15, # Lenient on logic, strict on size
        "min_type_coverage": 40,
        "required_files": [],
        "description": "Optimized for small context completion."
    }
}

# --- ANALYZERS ---

def get_loc(filepath):
    """Returns lines of code excluding whitespace/comments roughly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except UnicodeDecodeError:
        return 0

def get_complexity_score(filepath, threshold):
    """Returns (average_complexity, penalty)."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0, 0

    avg_complexity = sum(complexities) / len(complexities)
    penalty = 10 if avg_complexity > threshold else 0
    return avg_complexity, penalty

def check_type_hints(filepath, threshold):
    """Returns (coverage_percent, penalty)."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    if not functions:
        return 100, 0

    typed_functions = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        if has_return or has_args:
            typed_functions += 1

    coverage = (typed_functions / len(functions)) * 100
    penalty = 20 if coverage < threshold else 0
    return coverage, penalty

def scan_project_docs(root_path, required_files):
    """Checks for existence of agent-critical markdown files."""
    missing = []
    # Normalize checking logic to look in the root of the provided path
    root_files = [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing

# --- CORE LOGIC ---

def score_file(filepath, profile):
    """Calculates score based on the selected profile."""
    score = 100
    details = []

    # 1. Lines of Code
    loc = get_loc(filepath)
    limit = profile["max_loc"]
    if loc > limit:
        # -1 point per 10 lines over limit
        excess = loc - limit
        loc_penalty = (excess // 10)
        score -= loc_penalty
        details.append(f"LOC {loc} > {limit} (-{loc_penalty})")

    # 2. Complexity
    avg_comp, comp_penalty = get_complexity_score(filepath, profile["max_complexity"])
    score -= comp_penalty
    if comp_penalty:
        details.append(f"Complexity {avg_comp:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # 3. Type Hints
    type_cov, type_penalty = check_type_hints(filepath, profile["min_type_coverage"])
    score -= type_penalty
    if type_penalty:
        details.append(f"Types {type_cov:.0f}% < {profile['min_type_coverage']}% (-{type_penalty})")

    return max(score, 0), ", ".join(details)

@click.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
def cli(path, agent):
    """Analyze code compatibility for specific AI Agents."""

    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]
    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 1. Project Level Check
    project_score = 100
    missing_docs = []

    if os.path.isdir(path):
        missing_docs = scan_project_docs(path, profile["required_files"])
        if missing_docs:
            penalty = len(missing_docs) * 15
            project_score -= penalty
            console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(missing_docs)} (-{penalty} pts)")

    # 2. File Level Check
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    py_files = []
    if os.path.isfile(path):
        if path.endswith(".py"): py_files = [path]
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    file_scores = []
    for filepath in py_files:
        score, notes = score_file(filepath, profile)
        file_scores.append(score)

        status_color = "green" if score >= 70 else "red"
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        table.add_row(rel_path, f"[{status_color}]{score}[/{status_color}]", notes)

    console.print(table)

    # 3. Final Aggregation
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    # Weighted average: 80% file quality, 20% project structure
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    console.print(f"\n[bold]Final Agent Score: {final_score:.1f}/100[/bold]")

    if final_score < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        import sys
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")

if __name__ == "__main__":
    cli()
