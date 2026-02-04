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

## 📢 Prompt Analyzer

Ensure your prompt engineering follows best practices to get the best results from LLMs.

```bash
agent-score check-prompts my_prompt.txt
```

This checks for:
* **Persona Adoption** (e.g., "You are an expert...")
* **Clear Delimiters** (e.g., `---` or ` ``` `)
* **Few-Shot Examples** (Providing examples)
* **Chain of Thought** (Asking for step-by-step reasoning)
* **Structured Output** (Requesting JSON/CSV/etc.)
* **Negative Constraints** (Warning against "Do not...")
