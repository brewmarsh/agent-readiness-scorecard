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


def create_issue(file_path: str, issue_type: str, craft_prompt: str) -> None:
    """
    Creates a new GitHub issue using the gh CLI.
    The CRAFT prompt is used as the issue body.
    """
    title = f"Refactor: {file_path} ({issue_type})"
    try:
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                craft_prompt,
                "--label",
                "tech-debt",
                "--label",
                "ai-ready",
            ],
            check=True,
        )
        print(f"Created issue for {file_path} ({issue_type})")
    except Exception as e:
        print(f"Error creating issue: {e}")


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

    # Regex logic:
    # 1. Look for headers: ### File: `path` - Type
    # 2. Capture path and type
    # 3. Capture all text following until the next file header or the next main section (Full File Analysis)
    # 4. Use re.DOTALL to match across lines
    pattern = r"### File: `(.+?)` - (High Cognitive Load|Low Type Safety)\n(.*?)(?=\n### File:|\n### 📂 Full File Analysis|\Z)"
    matches = re.finditer(pattern, content, re.DOTALL)

    typing_tasks: List[Dict[str, str]] = []

    for match in matches:
        file_path = match.group(1)
        issue_type = match.group(2)
        craft_prompt = match.group(3).strip()

        if issue_type == "High Cognitive Load":
            # High Cognitive Load items trigger GitHub Issues
            if not check_issue_exists(file_path, issue_type):
                create_issue(file_path, issue_type, craft_prompt)
            else:
                print(f"Issue already exists for {file_path} ({issue_type})")
        elif issue_type == "Low Type Safety":
            # Low Type Safety items are collected for later processing
            typing_tasks.append({"file": file_path, "prompt": craft_prompt})

    # Save typing tasks to JSON for the next CI step
    if typing_tasks:
        with open("typing_tasks.json", "w", encoding="utf-8") as f:
            json.dump(typing_tasks, f, indent=2)
        print(f"Saved {len(typing_tasks)} typing tasks to typing_tasks.json")
    else:
        # Create an empty file if no tasks found to avoid CI step failure if it expects the file
        with open("typing_tasks.json", "w", encoding="utf-8") as f:
            json.dump([], f)
        print("No typing tasks found. Created empty typing_tasks.json")


if __name__ == "__main__":
    main()
