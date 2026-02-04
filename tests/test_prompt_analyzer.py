import pytest
from src.agent_scorecard.prompt_analyzer import PromptAnalyzer

def test_perfect_prompt():
    analyzer = PromptAnalyzer()
    prompt = """
    You are an expert software engineer.
    Please fix the following code step-by-step.

    Example:
    Input: x = 1
    Output: x = 2

    ```python
    print("hello")
    ```

    Output the result in JSON format.
    """
    result = analyzer.analyze(prompt)

    # 5 heuristics * 25 = 125
    assert result["score"] == 125
    assert len(result["matches"]) == 5
    assert not any("Found Negative Constraints" in s for s in result["suggestions"])

def test_poor_prompt():
    analyzer = PromptAnalyzer()
    prompt = "fix this code"
    result = analyzer.analyze(prompt)

    assert result["score"] == 0
    assert len(result["matches"]) == 0
    assert len(result["suggestions"]) == 5 # All missing

def test_negative_constraints():
    analyzer = PromptAnalyzer()
    prompt = "Do not use global variables. Don't forget to comment."
    result = analyzer.analyze(prompt)

    # -10 penalty
    assert result["score"] == -10
    assert any("Found Negative Constraints" in s for s in result["suggestions"])

def test_mixed_prompt():
    analyzer = PromptAnalyzer()
    prompt = """
    Act as a teacher.
    Provide the answer in JSON.
    Do not be verbose.
    """
    result = analyzer.analyze(prompt)

    # Persona (+25) + Structured Output (+25) - Negative (-10) = 40
    assert result["score"] == 40
    assert "Persona Adoption" in result["matches"]
    assert "Structured Output" in result["matches"]
    assert any("Found Negative Constraints" in s for s in result["suggestions"])

def test_empty_prompt():
    analyzer = PromptAnalyzer()
    result = analyzer.analyze("")
    assert result["score"] == 0
    assert result["suggestions"] == ["Prompt is empty."]
