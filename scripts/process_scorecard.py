import sys
import re
import subprocess
import json
import os
from typing import List, Dict


def check_issue_exists(file_path: str, issue_type: str) -> bool:
    """
    Checks if an open GitHub issue with the same title already exists.
    Title format: Refactor: <file_path> (<issue_type>)
    """
    title = f"Refactor: {file_path} ({issue_type})"
    try:
        # Search for open issues with the exact title
        # We use --json number to get a list of issue numbers
        result = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--search",
                f'"{title}" in:title',
                "--state",
                "open",
                "--json",
                "number",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        issues = json.loads(result.stdout)
        return len(issues) > 0
    except Exception as e:
        print(f"Error checking issue: {e}")
        return False


def _add_label_to_issue(issue_url: str, label: str) -> None:
    """Gracefully attempt to add a label to a GitHub issue."""
    try:
        subprocess.run(
            ["gh", "issue", "edit", issue_url, "--add-label", label],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not add label '{label}': {e.stderr.strip()}")


def create_issue(file_path: str, issue_type: str, craft_prompt: str) -> None:
    """
    Creates a new GitHub issue using the gh CLI.
    The CRAFT prompt is used as the issue body.
    Attempts to add labels but continues if they don't exist.
    """
    title = f"Refactor: {file_path} ({issue_type})"
    try:
        # First create the issue without labels to ensure it gets created
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", craft_prompt],
            capture_output=True,
            text=True,
            check=True,
        )
        issue_url = result.stdout.strip()
        print(f"Created issue for {file_path} ({issue_type}): {issue_url}")

        for label in ["tech-debt", "ai-ready"]:
            _add_label_to_issue(issue_url, label)

    except Exception as e:
        print(f"Error creating issue: {e}")


def _process_match(match: re.Match, typing_tasks: List[Dict[str, str]]) -> None:
    """Process a single regex match from the scorecard."""
    file_path = match.group(1)
    issue_type = match.group(2)
    craft_prompt = match.group(3).strip()

    if issue_type == "High Cognitive Load":
        if not check_issue_exists(file_path, issue_type):
            create_issue(file_path, issue_type, craft_prompt)
        else:
            print(f"Issue already exists for {file_path} ({issue_type})")
    elif issue_type == "Low Type Safety":
        typing_tasks.append({"file": file_path, "prompt": craft_prompt})


def _save_typing_tasks(typing_tasks: List[Dict[str, str]]) -> None:
    """Save typing tasks to JSON for the next CI step."""
    with open("typing_tasks.json", "w", encoding="utf-8") as f:
        json.dump(typing_tasks, f, indent=2 if typing_tasks else None)

    if typing_tasks:
        print(f"Saved {len(typing_tasks)} typing tasks to typing_tasks.json")
    else:
        print("No typing tasks found. Created empty typing_tasks.json")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/process_scorecard.py <scorecard_file>")
        sys.exit(1)

    scorecard_file = sys.argv[1]
    if not os.path.exists(scorecard_file):
        print(f"Error: File {scorecard_file} not found.")
        sys.exit(1)

    with open(scorecard_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex logic: Capture path, type, and CRAFT prompt content.
    pattern = r"### File: `(.+?)` - (High Cognitive Load|Low Type Safety)\n(.*?)(?=\n### File:|\n### 📂 Full File Analysis|\Z)"
    matches = re.finditer(pattern, content, re.DOTALL)

    typing_tasks: List[Dict[str, str]] = []
    for match in matches:
        _process_match(match, typing_tasks)

    _save_typing_tasks(typing_tasks)


if __name__ == "__main__":
    main()
