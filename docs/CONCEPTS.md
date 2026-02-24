# The Physics of Agent-Code Interaction

Traditional code quality metrics (Clean Code) focus on human readability. **Agent Readiness** focuses on machine reason-ability.

## 1. Agent Cognitive Load (ACL)
Agents have a "Reasoning Budget." High complexity burns tokens on logic, leaving fewer tokens for task execution.

### Python ACL
* **Formula:** $ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)$
* **Threshold:** functions with ACL > 15 are "Hallucination Zones."

### Markdown ACL
* **Formula:** $ACL = (Header Depth * 1.5) + (Tokens in Section / 100)$
* **Threshold:** sections with ACL > 15 are "Hallucination Zones."
* **Strategy:** Ensure headers group content logically and consider breaking down large documentation chunks.

### Dockerfile ACL
* **Formula:** $ACL = (Chained Commands * 1.5) + (Lines in Instruction * 0.5)$
* **Threshold:** instructions with ACL > 15 are "Hallucination Zones."
* **Strategy:** Break down complex RUN instructions into smaller, logical steps or use scripts. Avoid excessively long chained commands.

### Config ACL
* **Formula:** $ACL = (Max Depth * 2) + (LOC / 50)$
* **Threshold:** files with ACL > 15 are "Hallucination Zones."
* **Strategy:** Flat is better than nested. Keep configuration files shallow and well-documented.

## 2. Dependency Entanglement
Agents traverse code like a graph.
* **Circular Dependencies:** Cause infinite recursion loops in Agent planning.
* **God Modules:** Overload the context window (Inbound > 50).

## 3. Context Economics
Context is currency.
* **Token Budget:** >32k tokens in a critical path risks "forgetting" instructions.
* **Directory Entropy:** Too many files in one folder confuses retrieval tools.

## 4. Multi-Language Support
`agent-scorecard` uses the Strategy Pattern to apply language-specific "Physics" to different file types.

### Language-Specific Configuration
You can customize thresholds for each language in `pyproject.toml`. This allows for different complexity tolerances across your stack.

```toml
[tool.agent-scorecard.python.thresholds]
acl_yellow = 10

[tool.agent-scorecard.javascript.thresholds]
acl_yellow = 12
acl_red = 18
```

The tool will automatically detect the language (Python, JavaScript, Markdown, Docker) and apply the appropriate overrides, falling back to global thresholds if none are specified.
