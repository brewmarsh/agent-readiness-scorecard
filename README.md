## 🤖 Agent Scorecard

![Agent Score](./agent_score.svg) [![CI](https://github.com/brewmarsh/agent-readiness-scorecard/actions/workflows/ci.yml/badge.svg)](https://github.com/brewmarsh/agent-readiness-scorecard/actions/workflows/ci.yml) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) ![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue) ![Strictly Typed](https://img.shields.io/badge/Strictly-Typed-blue)

**Is your codebase ready for the AI workforce?**

`agent-scorecard` is a CLI tool that analyzes your Python project to determine how "friendly" it is for AI Agents (like Jules, Copilot, Gemini, or Devin).

AI Agents struggle with:

* **Massive Contexts:** Large files confuse models and waste token limits.
* **Ambiguity:** Missing type hints lead to hallucinated parameters.
* **Hidden Logic:** Complex code flows (high cyclomatic complexity) make it hard for agents to reason about changes.

This tool scores your repo and helps you fix it.

## 📦 Installation

```bash
pip install agent-scorecard

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

## 🤖 Using the CRAFT Prompts

`agent-scorecard` uses the **CRAFT** framework to generate high-quality remediation prompts. If you prefer not to use the `--fix` flag, you can use these prompts manually to guide your favorite AI agent.

### The CRAFT Framework

* **Context**: Defines the persona and background for the task.
* **Request**: The specific goal or improvement needed.
* **Actions**: Step-by-step instructions for the agent to follow.
* **Frame**: The constraints and boundaries (e.g., "don't change logic").
* **Template**: The expected format of the output.

### Example Prompt: Fixing a God Module

When the scorecard identifies a "God Module" (a file with too many inbound dependencies), it generates a prompt like this:

> **Context**: You are a Software Architect specializing in modular system design.
> **Request**: Decompose the God Module `main.py` to reduce context pressure.
> **Actions**:
> - Identify distinct responsibilities within the module.
> - Extract logic into smaller, cohesive sub-modules.
> - Refactor imports to maintain internal dependencies.
> **Frame**: Inbound imports must stay below 50. Maintain existing functionality.
> **Template**: A refactoring plan followed by the new module code structure.

### Manual Usage Guide

1. **Run the Scorecard**: Generate your report using `agent-score .`.
2. **Copy the Prompt**: Locate the "Agent Prompts for Remediation" section in the output.
3. **Paste into AI**: Copy and paste the CRAFT prompt directly into **Cursor**, **GitHub Copilot**, or **ChatGPT**.
4. **Apply Fixes**: Use the AI's output to refactor your code with confidence.

## ⚙️ Configuration

`agent-scorecard` can be configured via `pyproject.toml`, `.agent-scorecard.json`, or CLI flags.

### Priority

Settings are resolved in the following order (highest to lowest):

1. **CLI Flags** (e.g., `--agent`, `--verbosity`)
2. **Configuration File** (`pyproject.toml` or `.agent-scorecard.json`)
3. **Defaults**

### pyproject.toml Example

Add a `[tool.agent-scorecard]` section to your `pyproject.toml` to customize thresholds and output:

```toml
[tool.agent-scorecard]
agent = "jules"
verbosity = "summary"

[tool.agent-scorecard.thresholds]
acl_yellow = 10
acl_red = 15
type_safety = 90

```

### Verbosity Levels

| Level | Description |
| --- | --- |
| `quiet` | Suppresses tables; only prints the Final Score and Project-Wide Issues. Ideal for CI/CD. |
| `summary` | (Default) Displays Environment Health table and rows for files with issues. |
| `detailed` | Deep-dive mode. Provides a full breakdown of every file, including ACL calculations. |

## 📊 The Scoring System

Your codebase starts at **100 points**. Penalties are applied for:

| Metric | Penalty | Why? |
| --- | --- | --- |
| **Bloated Files** | -1 pt per 10 lines > 200 | Agents lose focus in large files. |
| **High ACL** | -15 (Red) / -5 (Yellow) | Agent Cognitive Load: . Target <= 10. |
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

## 🛡 Badges

Show off your Agent-Readiness! Run `agent-score --badge` to generate an `agent_score.svg` for your repo.

## ⚡ CI/CD & Diff Mode

Optimize your CI/CD pipeline by scoring only the files changed in a Pull Request. This mode is faster and focuses on new changes while still validating the entire project for circular dependencies.

```bash
# Score only changes vs the main branch
agent-score score --diff origin/main

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