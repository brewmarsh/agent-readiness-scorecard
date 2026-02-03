import os
import ast
import tiktoken
from typing import Dict, Any

def check_directory_entropy(path: str) -> Dict[str, Any]:
    """Calculate the average number of files per folder. Warn if > 15."""
    if not os.path.isdir(path):
        return {"avg_files": 0, "warning": False}

    total_files = 0
    total_folders = 0

    for root, dirs, files in os.walk(path):
        if ".git" in root or "__pycache__" in root:
            continue
        total_folders += 1
        total_files += len(files)

    avg = total_files / total_folders if total_folders > 0 else 0
    return {
        "avg_files": avg,
        "warning": avg > 15
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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # In Python 3.9+, ast.unparse is available.
            if hasattr(ast, "unparse"):
                # We want just the signature. A trick is to replace the body with 'pass'
                orig_body = node.body
                node.body = [ast.Pass()]
                try:
                    unparsed = ast.unparse(node)
                    # The first line is usually the signature
                    signature = unparsed.split('\n')[0]
                    signatures.append(signature)
                except Exception:
                    pass
                finally:
                    node.body = orig_body
            else:
                # Fallback for < 3.9: just use the name
                signatures.append(f"def {node.name}(...):")

        elif isinstance(node, ast.ClassDef):
            if hasattr(ast, "unparse"):
                orig_body = node.body
                node.body = [ast.Pass()]
                try:
                    unparsed = ast.unparse(node)
                    signature = unparsed.split('\n')[0]
                    signatures.append(signature)
                except Exception:
                    pass
                finally:
                    node.body = orig_body
            else:
                signatures.append(f"class {node.name}:")

    return "\n".join(signatures)

def check_critical_context_tokens(path: str) -> Dict[str, Any]:
    """Count tokens in README.md + AGENTS.md + python signatures."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback if tiktoken fails for some reason
        return {"token_count": 0, "alert": False}

    total_content = ""

    # Files to check in root
    critical_files = ["README.md", "AGENTS.md"]
    if os.path.isdir(path):
        for cf in critical_files:
            cf_path = os.path.join(path, cf)
            if os.path.exists(cf_path):
                try:
                    with open(cf_path, "r", encoding="utf-8", errors="ignore") as f:
                        total_content += f.read() + "\n"
                except Exception:
                    pass

        # Python signatures
        for root, _, files in os.walk(path):
            if ".git" in root or "__pycache__" in root:
                continue
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

    if not os.path.isdir(path):
        # If it's a file, we can still check the directory it's in
        path = os.path.dirname(os.path.abspath(path))

    root_files = os.listdir(path)

    # 1. AGENTS.md (case-insensitive)
    if any(f.lower() == "agents.md" for f in root_files):
        results["agents_md"] = True

    # 2. Linter Config
    target_linters = ["ruff.toml", ".flake8", ".eslintrc"]
    if any(f in root_files for f in target_linters):
        results["linter_config"] = True
    elif "pyproject.toml" in root_files:
        try:
            with open(os.path.join(path, "pyproject.toml"), "r", encoding="utf-8") as f:
                content = f.read()
                if "[tool.ruff]" in content:
                    results["linter_config"] = True
        except Exception:
            pass

    # 3. Lock File
    lock_files = ["package-lock.json", "poetry.lock", "uv.lock"]
    if any(f in root_files for f in lock_files):
        results["lock_file"] = True

    return results
