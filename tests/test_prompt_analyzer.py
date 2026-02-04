from src.agent_scorecard.prompt_analyzer import PromptAnalyzer


def test_prompt_analyzer_perfect():
    analyzer = PromptAnalyzer()
    text = """
    You are a professional coder.
    Think step by step to solve the problem.
    <context>
    Code here
    </context>
    Example:
    Input: x
    Output: y
    """
    results = analyzer.analyze(text)
    assert results["score"] == 100
    assert results["results"]["role_definition"] is True
    assert results["results"]["cognitive_scaffolding"] is True
    assert results["results"]["delimiter_hygiene"] is True
    assert results["results"]["few_shot"] is True
    assert (
        results["results"]["negative_constraints"] is True
    )  # No negative constraints found
    assert len(results["improvements"]) == 0


def test_prompt_analyzer_low_score():
    analyzer = PromptAnalyzer()
    text = "Do the task. Don't fail."
    results = analyzer.analyze(text)
    # 0 positive heuristics found, 1 negative constraint penalty
    # 0 - 10 clamped to 0
    assert results["score"] == 0
    assert results["results"]["role_definition"] is False
    assert results["results"]["negative_constraints"] is False
    assert len(results["improvements"]) == 5  # 4 missing + 1 penalty


def test_prompt_analyzer_some_heuristics():
    analyzer = PromptAnalyzer()
    text = "You are a teacher. Reasoning is important. Never lie."
    results = analyzer.analyze(text)
    # Role: 25, CoT (Reasoning): 25, Delimiter: 0, Few-shot: 0. Total: 50.
    # Penalty: -10. Final score: 40.
    assert results["score"] == 40
    assert results["results"]["role_definition"] is True
    assert results["results"]["cognitive_scaffolding"] is True
    assert results["results"]["delimiter_hygiene"] is False
    assert results["results"]["few_shot"] is False
    assert results["results"]["negative_constraints"] is False
