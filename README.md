# 🤖 Agent Scorecard

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

```bash
agent-score src/ --agent=jules

```

### 3. Auto-Fix Issues

Bootstrap your repository with the necessary context files and skeleton docstrings:

```bash
agent-score . --fix

```

## 📊 The Scoring System

Your codebase starts at **100 points**. Penalties are applied for:

| Metric | Penalty | Why? |
| --- | --- | --- |
| **Bloated Files** | -1 pt per 10 lines > 200 | Agents lose focus in large files. |
| **Complexity** | -10 pts if McCabe > 10 | If code is hard to read, it's hard to refactor safely. |
| **Missing Types** | -20 pts if coverage < 50% | Agents need types to call functions correctly. |
| **Missing Context** | -15 pts per missing file | `agents.md` acts as the System Prompt for your repo. |

## 🛠 Project Structure

To get a perfect score, your project should look like this:

```text
my-project/
├── agents.md          # High-level architecture map for the Agent
├── instructions.md    # Testing/Linting commands for the Agent
└── src/               # Your source code (Typed & Docstringed)

```

## 🛡 Badges

Show off your Agent-Readiness!

*(Run `agent-score --badge` to generate this for your repo)*

## ⚡ CI/CD & Diff Mode

Optimize your CI/CD pipeline by scoring only the files changed in a Pull Request. This mode is faster and focuses on new changes while still validating the entire project for circular dependencies.

```bash
# Score only changes vs the main branch
agent-score score --diff origin/main
```

This feature uses `git diff` to identify modified `.py` files and ensures that even if you only check one file, the codebase's global "Agent Physics" (like dependency cycles) remains healthy.

## 📝 Prompt Engineering Linter

Static analysis for your LLM prompts. Ensure your system prompts follow best practices (Role Definition, Few-Shot, CoT) before deploying them to production.

```bash
agent-score check-prompts prompts/system_v1.txt
```

### Heuristics Checked:
* **Role Definition**: Does the prompt establish a persona?
* **Cognitive Scaffolding**: Are there "Think step-by-step" instructions?
* **Delimiter Hygiene**: Are instructions separated from data using XML/Markdown tags?
* **Few-Shot Examples**: Does it include 1-3 examples?
* **Negative Constraints**: Identifies "Don't" statements and suggests positive alternatives.

## 🤖 Using the CRAFT Prompts

The score report now includes auto-generated **CRAFT** prompts for every major issue detected in your codebase. These prompts are designed to be copy-pasted directly into LLMs like **ChatGPT, Claude, or Cursor** to get optimal refactoring results.

### What is CRAFT?

CRAFT is a prompt engineering framework that ensures the AI has enough context and structure to perform complex tasks:

- **C**ontext: Defines the persona (e.g., "You are a Software Architect").
- **R**equest: The specific task to be performed.
- **A**ctions: Step-by-step instructions for the AI.
- **F**rame: Constraints and boundaries (e.g., "Keep functions under 50 lines").
- **T**emplate: The desired output format.

### Example CRAFT Prompt

If `agent-scorecard` detects a **God Module**, it will generate a prompt like this:

> **Context**: You are a Software Architect specializing in modular system design.
> **Request**: Decompose the God Module `main.py` to improve maintainability.
> **Actions**:
> - Analyze the module to identify distinct responsibilities.
> - Extract logic into smaller, cohesive modules.
> - Refactor inbound imports to point to the new, smaller modules.
> **Frame**: Ensure inbound imports for any single module stay below 50. Maintain all existing functionality.
> **Template**: A detailed refactoring plan followed by the code for the new module structure.

### How to use them
1. Run `agent-score . --report report.md`.
2. Open `report.md` and scroll to the **🤖 Agent Prompts for Remediation (CRAFT Format)** section.
3. Copy a CRAFT prompt.
4. Paste it into your AI editor (Cursor) or chat interface (Claude/ChatGPT).
5. Review and apply the generated code!
