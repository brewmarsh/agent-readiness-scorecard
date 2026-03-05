## 🤖 Agent Readiness Scorecard

![Agent Score](./agent_score.svg) [![CI](https://github.com/brewmarsh/agent-readiness-scorecard/actions/workflows/ci.yml/badge.svg)](https://github.com/brewmarsh/agent-readiness-scorecard/actions/workflows/ci.yml) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) ![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue) ![Strictly Typed](https://img.shields.io/badge/Strictly-Typed-blue)

**Is your codebase ready for the AI workforce?**

`agent-readiness-scorecard` is a CLI tool that analyzes your Python project to determine how "friendly" it is for AI Agents (like Jules, Copilot, Gemini, or Devin).

AI Agents struggle with:

* **Massive Contexts:** Large files confuse models and waste token limits.
* **Ambiguity:** Missing type hints lead to hallucinated parameters.
* **Hidden Logic:** Complex code flows (high cyclomatic complexity) make it hard for agents to reason about changes.

This tool scores your repo and helps you fix it.

## 📦 Installation

```bash
pip install agent-readiness-scorecard

```

## 🚀 Usage

### 1. Check your Score

Run the scorecard on your current directory:

```bash
agent-score .

```

### 2. Select an Agent Profile

Different agents have different strengths. Optimize for specific workflows:

* **`--agent=generic`** (Default): Balanced checks for readability and types.
* **`--agent=jules`**: Strict typing and high documentation requirements (expects `agents.md`).
* **`--agent=copilot`**: Focuses on small file sizes for autocomplete efficiency.

### 3. Auto-Fix Issues

Bootstrap your repository with the necessary context files and skeleton docstrings:

```bash
agent-score . --fix

```

### 4. Generate a Markdown Report

Generate a detailed report for your team or CI/CD logs. Control the level of detail with `--report-style`:

```bash
agent-score . --report scorecard.md --report-style actionable
```

* **`--report-style=full`**: Includes all sections and a complete breakdown of every file.
* **`--report-style=actionable`** (Default): Focuses on issues; hides passing files and high-coverage type safety rows.
* **`--report-style=collapsed`**: (Minimal) Only includes the Executive Summary.

## ⚙️ Configuration

`agent-readiness-scorecard` can be configured via `pyproject.toml`, `.agent-readiness-scorecard.json`, or CLI flags.

### Priority

Settings are resolved in the following order (highest to lowest):

1. **CLI Flags** (e.g., `--agent`, `--verbosity`)
2. **Configuration File** (`pyproject.toml` or `.agent-readiness-scorecard.json`)
3. **Defaults**

### Customizing Output Verbosity

You can control how much visual noise the scorecard generates by adding the `verbosity` or `report_style` keys to your `pyproject.toml`.

#### Noise-Reduction Configuration

```toml
[tool.agent-readiness-scorecard]
# Control CLI output (quiet, summary, detailed)
verbosity = "summary"

# Control Markdown report detail (collapsed, actionable, full)
report_style = "actionable"

[tool.agent-readiness-scorecard.thresholds]
acl_yellow = 10
acl_red = 15
type_safety = 90

# Language-specific overrides
[tool.agent-readiness-scorecard.javascript.thresholds]
acl_yellow = 12
acl_red = 18

[tool.agent-readiness-scorecard.markdown.thresholds]
token_limit = 64000
```

### Verbosity Levels (CLI Output)

| Level | Description |
| --- | --- |
| `quiet` | Suppresses tables; only prints the Final Score and Project-Wide Issues. Ideal for CI/CD. |
| `summary` | (Default) Displays Environment Health and actionable files with issues. Perfect scores (100) are hidden to reduce noise. |
| `detailed` | Deep-dive mode. Provides a full breakdown of every file, using progressive disclosure for passing metrics. |

### Report Styles (Markdown Report)

Used when generating a report via the `--report` flag.

| Style | Description |
| --- | --- |
| `collapsed` | (Minimal) Only includes the Executive Summary. |
| `actionable` | (Default) Focuses on issues: hides passing files and high-coverage type safety rows from tables. |
| `full` | Includes all sections and a complete breakdown of every file and metric. |

## 🌐 Supported Languages

While `agent-readiness-scorecard` is written in Python, it supports analyzing multiple languages:

*   **Python**: First-class support, included by default.
*   **Markdown**: Standard documentation analysis, included by default.
*   **Docker**: Dockerfile analysis, included by default.
*   **JavaScript/TypeScript**: Requires the `[treesitter]` extra.

To enable analysis for non-Python languages, install the optional dependencies:

```bash
pip install agent-readiness-scorecard[treesitter]
```

## 📊 The Scoring System

Your codebase starts at **100 points**. Penalties are applied for:

| Metric | Penalty | Why? |
| --- | --- | --- |
| **Bloated Files** | -1 pt per 10 lines > 200 | Agents lose focus in large files. |
| **High ACL** | -15 (Red) / -5 (Yellow) | Agent Cognitive Load: `(Depth*2) + (Complexity*1.5) + (LOC/50)`. Target <= 10. |
| **Missing Types** | -20 pts if coverage < 90% | Agents need types to call functions correctly. |
| **Missing Context** | -15 pts per missing file | `agents.md` acts as the System Prompt for your repo. |
| **God Modules** | -10 pts per module | Modules with > 50 inbound imports overload context. |
| **High Entropy** | -5 pts per directory | Folders with > 50 files confuse retrieval tools. |
| **Circular Deps** | -5 pts per cycle | Causes infinite recursion in agent planning. |

## 🛠 Project Structure

To get a perfect score, your project should look like this:

```text
my-project/
├── agents.md          # High-level architecture map for the Agent
├── instructions.md    # Testing/Linting commands for the Agent
└── src/               # Your source code (Typed & Docstringed)

```

## 🚀 Beta Features

The `beta` branch includes upcoming capabilities for enhanced agent-readiness:

* **`pyproject.toml` Configuration**: Centralize settings alongside your other tools.
* **Prompt Linter (`check-prompts`)**: Validate your system prompts against LLM best practices (Role Definition, Few-Shot, etc.).
* **Verbosity Control (`--verbosity`)**: Choose between `quiet`, `summary` (default), or `detailed` output.
* **Enhanced Metrics**: Track "Average ACL" and "Average Type Safety" in the summary report.
* **CI/CD Automation**: Automated badge updates and GitHub Actions workflows for continuous agent-readiness.

## 🛡 Badges

Show off your Agent-Readiness! Run `agent-score --badge` to generate an `agent_score.svg` for your repo.

## ⚡ CI/CD & Diff Mode

Optimize your CI/CD pipeline by scoring only the files changed in a Pull Request.

### Diff-Aware CI Reporting

The provided GitHub Action defaults to **Diff-Aware Reporting**. This means that in a Pull Request, the scorecard will automatically detect and only score the files you've modified.

**Benefits:**
- **Noise Reduction**: Developers only see scores and issues for the code they are actually touching.
- **Speed**: Analysis is significantly faster on large repositories.
- **Project Integrity**: While focusing on specific files for scoring, the tool still validates project-wide issues like circular dependencies and global context health.

### Local Incremental Analysis

You can use the `--diff` flag to analyze only the files that have changed compared to a base reference (default: `origin/main`). This is useful for quickly checking your work before committing.

```bash
# Check only changed files (compared to origin/main)
agent-score --diff

# Check changes compared to a specific branch or commit
agent-score --diff --diff-base HEAD^
```

### Manual File Limitation

You can also manually use the `--limit-to` flag to restrict analysis to a subset of files. You can provide the flag multiple times. If used with `--diff`, it will analyze the intersection of changed files and the specified files.

```bash
# Score only specific files
agent-score score . --limit-to src/core.py --limit-to src/utils.py
```

## 📝 Prompt Engineering Linter

Static analysis for your LLM prompts. Ensure your system prompts follow best practices before deploying them to production.

```bash
agent-score check-prompts prompts/system_v1.txt

```

### Heuristics Checked:

* **Role Definition**: Does the prompt establish a persona?
* **Cognitive Scaffolding**: Are there "Think step-by-step" instructions?
* **Delimiter Hygiene**: Are instructions separated from data using XML/Markdown tags?
* **Few-Shot Examples**: Does it include 1-3 examples?
* **Negative Constraints**: Identifies "Don't" statements and suggests positive alternatives.

---