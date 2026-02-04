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
    # Note: 'Don't' must be in a list/imperative format to trigger the context-aware penalty
    text = "x" * 100 + "\n* Don't fail."
    results = analyzer.analyze(text)
    
    # 0 - 10 = -10, clamped to 0
    assert results["score"] == 0
    assert results["results"]["role_definition"] is False
    assert results["results"]["negative_constraints"] is False
    # 4 missing positive improvements + 1 negative constraint improvement = 5
    assert len(results["improvements"]) == 5

def test_negative_constraints_context_awareness():
    """Verify that negative constraints are only flagged in imperative contexts (lists)."""
    analyzer = PromptAnalyzer()
    padding = "y" * 100
    
    # Case 1: Flagged in a list
    assert analyzer.analyze(padding + "\n* Do not fail.")["results"]["negative_constraints"] is False
    assert analyzer.analyze(padding + "\n* Never fail.")["results"]["negative_constraints"] is False

    # Case 2: Ignored in descriptive prose (Reduced false positives)
    assert analyzer.analyze(padding + "\nI do not like this.")["results"]["negative_constraints"] is True
    assert analyzer.analyze(padding + "\nIt is not working.")["results"]["negative_constraints"] is True

def test_empty_prompt():
    """Test handling of empty or whitespace strings."""
    analyzer = PromptAnalyzer()
    
    res_empty = analyzer.analyze("")
    assert res_empty["score"] == 0
    assert "Prompt is empty." in res_empty["improvements"]
    
    res_space = analyzer.analyze("    ")
    assert res_space["score"] == 0
    assert "Prompt is empty." in res_space["improvements"]

def test_delimiter_variants():
    """Verify different delimiter patterns are recognized."""
    analyzer = PromptAnalyzer()
    
    # Triple quotes
    assert analyzer.analyze("'''\ncode\n'''")["results"]["delimiter_hygiene"] is True
    # Markdown code blocks
    assert analyzer.analyze("```python\nprint()```")["results"]["delimiter_hygiene"] is True
    # XML-style tags
    assert analyzer.analyze("<instructions>do this</instructions>")["results"]["delimiter_hygiene"] is True

def test_cot_relaxed_variants():
    """Verify variations of Chain-of-Thought phrasing."""
    analyzer = PromptAnalyzer()
    assert analyzer.analyze("Make a Plan.")["results"]["cognitive_scaffolding"] is True
    assert analyzer.analyze("Step 1: Init.")["results"]["cognitive_scaffolding"] is True
    assert analyzer.analyze("Phase 1: Start.")["results"]["cognitive_scaffolding"] is True