import os
import ast
import tiktoken
from typing import Dict, Any, List, Optional


def check_directory_entropy(path: str) -> Dict[str, Any]:
    """
    Calculate directory entropy.
    Warns if avg files > 15 OR any single directory has > 50 files.
    High entropy makes it difficult for RAG or Agents to find specific files.
    """
    if not os.path.isdir(path):
        return {"avg_files": 0, "warning": False, "max_files": 0, "crowded_dirs": []}

    total_files = 0
    total_folders = 0
    max_files = 0
    crowded_dirs = []

    for root, dirs, files in os.walk(path):
        # Filter out hidden directories and __pycache__ to avoid noise
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

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
        "crowded_dirs": crowded_dirs,
    }


def get_crowded_directories(root_path: str, threshold: int = 50) -> Dict[str, int]:
    """Returns a flat dictionary of directories exceeding the file count threshold."""
    entropy_stats: Dict[str, int] = {}
    if os.path.isfile(root_path):
        return entropy_stats

    for root, dirs, files in os.walk(root_path):
        if any(part.startswith(".") for part in root.split(os.sep)):
            continue

        count = len(files)
        if count > threshold:
            rel_path = os.path.relpath(root, start=root_path)
            if rel_path == ".":
                rel_path = os.path.basename(os.path.abspath(root_path))
            entropy_stats[rel_path] = count
    return entropy_stats


def _extract_signature_from_node(node: ast.AST) -> Optional[str]:
    """
    Extracts function/class signatures from an AST node.
    This provides the 'skeleton' of the code for token counting.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None

    if hasattr(ast, "unparse"):
        # Python 3.9+ logic: Replace body with 'pass' to get just the signature
        # Use getattr/setattr for maximum compatibility with various AST implementations
        orig_body = getattr(node, "body", [])
        setattr(node, "body", [ast.Pass()])
        try:
            unparsed = ast.unparse(node)
            lines = unparsed.splitlines()
            if lines:
                # For functions/classes, unparse usually includes the signature and 'pass'
                # We want just the signature.
                sig = "\n".join(lines[:-1]).strip()
                if not sig:  # Fallback if it's a single line
                    sig = lines[0]
                return sig
        except Exception:
            pass
        finally:
            setattr(node, "body", orig_body)
    else:
        # Fallback for older Python versions
        deco_list = [
            f"@{deco.id}" if isinstance(deco, ast.Name) else "@decorator"
            for deco in getattr(node, "decorator_list", [])
        ]

        if isinstance(node, ast.ClassDef):
            sig = f"class {node.name}:"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            sig = f"{prefix} {node.name}(...):"
        else:
            return None

        return "\n".join(deco_list + [sig]) if deco_list else sig
    return None


def get_python_signatures(filepath: str) -> str:
    """Extracts all top-level function and class signatures from a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return ""

    signatures: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            sig = _extract_signature_from_node(node)
            if sig:
                signatures.append(sig)

    return "\n".join(signatures)


def count_python_tokens(filepath: str) -> int:
    """Calculates the token count of a single Python file using tiktoken."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return len(enc.encode(content))
    except Exception:
        return 0


def check_critical_context_tokens(path: str) -> Dict[str, Any]:
    """
    Counts tokens for the project's 'Critical Context':
    (README + AGENTS.md + All Python Signatures).
    If this exceeds 32k, an Agent will likely lose track of the overall architecture.
    """

    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        return {"token_count": 0, "alert": False}

    # Gather documentation
    total_content = ""
    critical_files = ["README.md", "AGENTS.md"]
    base_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))

    for cf in critical_files:
        cf_path = os.path.join(base_dir, cf)
        if os.path.exists(cf_path):
            try:
                with open(cf_path, "r", encoding="utf-8", errors="ignore") as f:
                    total_content += f.read() + "\n"
            except Exception:
                pass

    # Gather signatures
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    total_content += (
                        get_python_signatures(os.path.join(root, file)) + "\n"
                    )
    elif os.path.isfile(path) and path.endswith(".py"):
        total_content += get_python_signatures(path)

    tokens = enc.encode(total_content)
    count = len(tokens)
    return {"token_count": count, "alert": count > 32000}


def check_environment_health(path: str) -> Dict[str, Any]:
    """Check for essential agent configuration: AGENTS.md, Linters, and Lock files."""
    results = {
        "agents_md": False,
        "linter_config": False,
        "lock_file": False,
        "pyproject_valid": True,
    }

    base_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    if not os.path.exists(base_dir):
        return results

    root_files = os.listdir(base_dir)

    # 1. AGENTS.md check
    results["agents_md"] = any(f.lower() == "agents.md" for f in root_files)

    # 2. Linter check
    linter_files = ["ruff.toml", ".flake8", ".eslintrc", "pyproject.toml"]
    results["linter_config"] = any(f in root_files for f in linter_files)

    # 3. Lock file check
    lock_files = ["package-lock.json", "poetry.lock", "uv.lock", "requirements.txt"]
    results["lock_file"] = any(f in root_files for f in lock_files)

    # 4. pyproject.toml validity
    if "pyproject.toml" in root_files:
        filepath = os.path.join(base_dir, "pyproject.toml")
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore

            with open(filepath, "rb") as f:
                tomllib.load(f)
        except ImportError:
            # Fallback for Python < 3.11 without toml package
            pass
        except Exception:
            results["pyproject_valid"] = False

    return results
