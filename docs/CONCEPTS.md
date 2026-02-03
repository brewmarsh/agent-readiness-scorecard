# The Physics of Agent-Code Interaction

Traditional code quality metrics (Clean Code) focus on human readability. **Agent Readiness** focuses on machine reason-ability.

## 1. Agent Cognitive Load (ACL)
Agents have a "Reasoning Budget." High complexity burns tokens on logic, leaving fewer tokens for task execution.
* **Formula:** $ACL = CC + (LLOC / 20)$
* **Threshold:** functions with ACL > 15 are "Hallucination Zones."

## 2. Dependency Entanglement
Agents traverse code like a graph.
* **Circular Dependencies:** Cause infinite recursion loops in Agent planning.
* **God Modules:** Overload the context window (Inbound > 50).

## 3. Context Economics
Context is currency.
* **Token Budget:** >32k tokens in a critical path risks "forgetting" instructions.
* **Directory Entropy:** Too many files in one folder confuses retrieval tools.
