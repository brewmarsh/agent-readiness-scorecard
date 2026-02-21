import os
import subprocess
from typing import List


def collect_python_files(path: str) -> List[str]:
    """Collects all Python files in the given path, ignoring hidden directories."""
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
    return py_files


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
