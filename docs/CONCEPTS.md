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

### JavaScript / TypeScript ACL
* **Formula:** $ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)$
* **Threshold:** functions with ACL > 15 are "Hallucination Zones."
* **AST Mapping:**
    * **Complexity:** Incremented by `if`, `for`, `while`, `do`, `switch case`, `catch`, `ternary`, and logical `&&`/`||`.
    * **Nesting Depth:** Maximum depth of `if`, `for`, `while`, `do`, `switch`, `catch`, and `try` blocks.
    * **Functions:** Analyzes function declarations, expressions, arrow functions, and class methods.

## 2. Dependency Entanglement
Agents traverse code like a graph.
* **Circular Dependencies:** Cause infinite recursion loops in Agent planning.
* **God Modules:** Overload the context window (Inbound > 50).

## 3. Context Economics
Context is currency.
* **Token Budget:** >32k tokens in a critical path risks "forgetting" instructions.
* **Directory Entropy:** Too many files in one folder confuses retrieval tools.
