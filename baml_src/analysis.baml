function GetAgentScore(code: string) -> FunctionMetric[] {
  client CustomGPT5Mini
  prompt #"
    Analyze the following code and extract metrics for each function.

    For each function, calculate the Agent Cognitive Load (ACL) using the formula:
    ACL = (nesting_depth * 2) + (complexity * 1.5) + (loc / 50)

    Code:
    ---
    {{ code }}
    ---

    {{ ctx.output_format }}
  "#
}
