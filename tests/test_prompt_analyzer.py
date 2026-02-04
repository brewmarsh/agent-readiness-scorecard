import pytest
from src.agent_scorecard.prompt_analyzer import PromptAnalyzer

def test_prompt_analyzer_perfect():
    """Test a prompt that satisfies all positive heuristics without penalties."""
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
    
    # 4 positive heuristics * 25 = 100
    assert results["score"] == 100
    assert results["results"]["role_definition"] is True
    assert results["results"]["cognitive_scaffolding"] is True
    assert results["results"]["delimiter_hygiene"] is True
    assert results["results"]["few_shot"] is True
    # Negative constraints should be True because the key tracks "No issue found"
    assert results["results"]["negative_constraints"] is True 
    assert len(results["improvements"]) == 0

def test_prompt_analyzer_low_score_clamping():
    """Test that scores are clamped to 0 when penalties exceed positive points."""
    analyzer = PromptAnalyzer()
    # No positive heuristics found, 1 negative constraint penalty (-10)
    text = "Do the task. Don't fail."
    results = analyzer.analyze(text)
    
    # 0 - 10 = -10, clamped to 0
    assert results["score"] == 0
    assert results["results"]["role_definition"] is False
    assert results["results"]["negative_constraints"] is False
    # 4 missing positive improvements + 1 negative constraint improvement = 5
    assert len(results["improvements"]) == 5

def test_prompt_analyzer_mixed_heuristics():
    """Test a mix of matches and penalties."""
    analyzer = PromptAnalyzer()
    text = "You are a teacher. Reasoning is important. Never lie."
    results = analyzer.analyze(text)
    
    # Role (+25) + Scaffolding (+25) - Negative Constraint (-10) = 40
    assert results["score"] == 40
    assert results["results"]["role_definition"] is True
    assert results["results"]["cognitive_scaffolding"] is True
    assert results["results"]["delimiter_hygiene"] is False
    assert results["results"]["few_shot"] is False
    assert results["results"]["negative_constraints"] is False

def test_empty_prompt():
    """Test handling of empty or whitespace strings."""
    analyzer = PromptAnalyzer()
    
    # Test empty string
    res_empty = analyzer.analyze("")
    assert res_empty["score"] == 0
    assert "Prompt is empty." in res_empty["improvements"]
    
    # Test whitespace string
    res_space = analyzer.analyze("   ")
    assert res_space["score"] == 0
    assert "Prompt is empty." in res_space["improvements"]

def test_delimiter_variants():
    """Verify different delimiter patterns are recognized."""
    analyzer = PromptAnalyzer()
    
    assert analyzer.analyze("```python\nprint()```")["results"]["delimiter_hygiene"] is True
    assert analyzer.analyze("--- section ---")["results"]["delimiter_hygiene"] is True
    assert analyzer.analyze("<instructions>do this</instructions>")["results"]["delimiter_hygiene"] is True