Here is a draft for the v1.0 PRD that captures our strategic pillars, structured specifically to live in your repository (e.g., as `docs/PRD_v1.0.md`). It elevates the focus on metric fidelity and flexible, low-token LLM integration.

---

# Agent Scorecard v1.0: Product Requirements Document

## Executive Summary

The Agent Scorecard measures the "Physics of Agent-Code Interaction." Version 1.0 transitions the tool from a baseline utility into a foundational CI/CD staple. The primary focus of this release is upgrading the fidelity of our scoring algorithms to reflect true cognitive friction, alongside a flexible, token-efficient remediation engine that allows teams to plug in their LLM of choice.

## Core Objectives

1. **Unassailable Accuracy:** Replace blunt heuristics with deep static analysis (AST) to measure true structural complexity.
2. **Bring-Your-Own-LLM (BYO-LLM) Remediation:** Enable seamless, low-token automated refactoring using the user's preferred model architecture.
3. **Frictionless DX:** Ensure the tool is immediately actionable without extensive configuration.

---

## Epic 1: High-Fidelity Metric Accuracy (Priority: Immediate)

Current heuristics (like LOC and flat Cyclomatic Complexity) can be gamed. Version 1.0 will calculate the actual architectural pressure an AI agent faces.

* **AST-Driven Nesting Analysis:** [COMPLETED]
* *Feature:* Parse the Abstract Syntax Tree to measure maximum nesting depth (e.g., loops inside conditionals inside `try/catch` blocks).
* *Value:* Deeply nested logic is the primary cause of LLM context loss and hallucination. Implemented using the formula `(Depth * 2) + (Complexity * 1.5) + (LOC / 50)`, heavily weighting structural depth over flat LOC.


* **Dynamic Context Economics:** [COMPLETED]
* *Feature:* Map the import graph to calculate the *cumulative* token load of a file plus its required dependencies.
* *Value:* An agent cannot edit a file in isolation if it relies on a "God Module." The token budget must reflect the entire context window required to understand the target unit. Implemented with a 32,000 token limit.


* **Shadow Evaluation (LLM-in-the-Loop):**
* *Feature:* An optional background verification run that asks a lightweight model to summarize flagged functions, matching the LLM's failure rate against our ACL red zones to continuously tune the scoring thresholds.



## Epic 2: BYO-LLM & Token-Optimized Remediation (Priority: Immediate)

Remediation must be accessible, agnostic, and highly economical regarding token spend.

* **Provider-Agnostic Engine:**
* *Feature:* Support standard API structures (e.g., via `litellm` or a standard interface) allowing users to easily inject API keys and configure their preferred models (GPT-4, Claude 3.5, Gemini) in the `pyproject.toml`.


* **Token-Optimized CRAFT Prompts:**
* *Feature:* The `agent-score fix` and `advise` commands will generate highly compressed, fluff-free prompts strictly adhering to the CRAFT (Context, Request, Actions, Frame, Template) framework.
* *Value:* Maximizes output quality while minimizing input token costs.


* **Requirement Regression Guardrails:**
* *Feature:* All generated AI agent instructions *must* explicitly command the LLM to check the project requirements to prevent regressions, and to update the requirements documentation based on any newly implemented features or structural changes.



## Epic 3: Developer Experience & Adoption (Priority: Fast Follow)

Features designed to lower the barrier to entry and shift feedback to the earliest possible moment in the SDLC.

* **Zero-Config Initiation:** An `agent-score init` command that interactively scaffolds `AGENTS.md` and default configurations.
* **Shift-Left IDE Extension:** Real-time ACL highlighting in VS Code/JetBrains.
* **Trend Tracking:** A `.agent-score.json` artifact to gamify improvements and track PR-over-PR agent-readiness progress.
