import os
import ast
import tiktoken
from typing import Dict, Any

def check_directory_entropy(path: str) -> Dict[str, Any]:
    """Calculate directory entropy. Warn if avg files > 15 OR max files > 50."""
    if not os.path.isdir(path):
        return {
            "avg_files": 0,
            "warning": False,
            "max_files": 0,
            "crowded_dirs": []
        }

    total_files = 0
    total_folders = 0
    max_files = 0
    crowded_dirs = []

    for root, dirs, files in os.walk(path):
        # Filter out hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        total_folders += 1
        num_files = len(files)
        total_files += num_files

        if num_files > max_files:
            max_files = num_files

        if num_files > 50:
            crowded_dirs.append(root)

    avg = total_files / total_folders if total_folders > 0 else 0

    return {
        "avg_files": avg,
        "warning": avg > 15 or max_files > 50,
        "max_files": max_files,
        "crowded_dirs": crowded_dirs
    }

def get_crowded_directories(root_path: str, threshold: int = 50) -> Dict[str, int]:
    """Returns directories with file count > threshold."""
    entropy_stats = {}
    if os.path.isfile(root_path):
        return entropy_stats

    for root, dirs, files in os.walk(root_path):
        # Ignore hidden directories like .git
        if any(part.startswith(".") for part in root.split(os.sep)):
            continue

        count = len(files)
        if count > threshold:
            rel_path = os.path.relpath(root, start=root_path)
            if rel_path == ".":
                rel_path = os.path.basename(os.path.abspath(root_path))
            entropy_stats[rel_path] = count
    return entropy_stats

def get_python_signatures(filepath: str) -> str:
    """Extracts function/method signatures from a python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return ""

    signatures = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if hasattr(ast, "unparse"):
                # We want just the signature. A trick is to replace the body with 'pass'
                orig_body = node.body
                node.body = [ast.Pass()]
                try:
                    unparsed = ast.unparse(node)
                    # Take everything but the last 'pass' line
                    lines = unparsed.splitlines()
                    if lines:
                        # Reconstruct the signature part
                        signature = "\n".join(lines[:-1]).strip()
                        if signature:
                            signatures.append(signature)
                        else:
                            # Fallback if it's somehow empty
                            signatures.append(lines[0])
                except Exception:
                    pass
                finally:
                    node.body = orig_body
            else:
                # Fallback for < 3.9: Capture decorators and name
                deco_list = []
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Name):
                        deco_list.append(f"@{deco.id}")
                    elif isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
                        deco_list.append(f"@{deco.func.id}(...)")

                if isinstance(node, ast.ClassDef):
                    sig = f"class {node.name}:"
                else:
                    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                    sig = f"{prefix} {node.name}(...):"

                if deco_list:
                    signatures.append("\n".join(deco_list) + "\n" + sig)
                else:
                    signatures.append(sig)

    return "\n".join(signatures)

def check_critical_context_tokens(path: str) -> Dict[str, Any]:
    """Count tokens in README.md + AGENTS.md + python signatures."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback if tiktoken fails for some reason
        return {"token_count": 0, "alert": False}

    total_content = ""

    # Determine search directories for critical files
    search_dirs = []
    if os.path.isdir(path):
        search_dirs.append(os.path.abspath(path))
    else:
        search_dirs.append(os.path.dirname(os.path.abspath(path)))
        # Also check one level up if we are in a subdirectory like 'src' or 'tests'
        parent = os.path.dirname(search_dirs[0])
        if parent and parent != search_dirs[0]:
            search_dirs.append(parent)

    # Files to check in search_dirs (deduplicated)
    critical_files = ["README.md", "AGENTS.md"]
    checked_paths = set()
    for s_dir in search_dirs:
        for cf in critical_files:
            cf_path = os.path.join(s_dir, cf)
            if os.path.exists(cf_path) and cf_path not in checked_paths:
                checked_paths.add(cf_path)
                try:
                    with open(cf_path, "r", encoding="utf-8", errors="ignore") as f:
                        total_content += f.read() + "\n"
                except Exception:
                    pass

    if os.path.isdir(path):
        # Python signatures
        for root, dirs, files in os.walk(path):
            # Filter out hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith(".py"):
                    total_content += get_python_signatures(os.path.join(root, file)) + "\n"
    elif os.path.isfile(path) and path.endswith(".py"):
        total_content += get_python_signatures(path)

    tokens = enc.encode(total_content)
    count = len(tokens)
    return {
        "token_count": count,
        "alert": count > 32000
    }

def check_environment_health(path: str) -> Dict[str, Any]:
    """Check for AGENTS.md, Linter Config, and Lock File."""
    results = {
        "agents_md": False,
        "linter_config": False,
        "lock_file": False
    }

    # Normalize path to directory
    base_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))

    # We might need to look up one level if we are in a subfolder
    search_dirs = [base_dir]
    parent = os.path.dirname(base_dir)
    if parent and parent != base_dir:
        search_dirs.append(parent)

    for s_dir in search_dirs:
        try:
            root_files = os.listdir(s_dir)
        except OSError:
            continue

        # 1. AGENTS.md (case-insensitive)
        if not results["agents_md"]:
            if any(f.lower() == "agents.md" for f in root_files):
                results["agents_md"] = True

        # 2. Linter Config
        if not results["linter_config"]:
            target_linters = ["ruff.toml", ".flake8", ".eslintrc"]
            if any(f in root_files for f in target_linters):
                results["linter_config"] = True
            elif "pyproject.toml" in root_files:
                try:
                    with open(os.path.join(s_dir, "pyproject.toml"), "r", encoding="utf-8") as f:
                        if "[tool.ruff]" in f.read():
                            results["linter_config"] = True
                except Exception:
                    pass

        # 3. Lock File
        if not results["lock_file"]:
            lock_files = ["package-lock.json", "poetry.lock", "uv.lock"]
            if any(f in root_files for f in lock_files):
                results["lock_file"] = True

    return results
