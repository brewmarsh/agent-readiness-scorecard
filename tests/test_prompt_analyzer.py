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
    assert results["results"]["negative_constraints"] is True # No negative constraints found
    assert len(results["improvements"]) == 0

def test_prompt_analyzer_low_score():
    analyzer = PromptAnalyzer()
    # Negative constraints like "Don't" are only flagged in lists and not in first 20%
    text = "x" * 100 + "\n* Don't fail."
    results = analyzer.analyze(text)
    assert results["results"]["negative_constraints"] is False
    assert results["score"] == 0 # 4 missing (100) - 10 penalty = 0 clamped

def test_negative_constraints_all_keywords():
    analyzer = PromptAnalyzer()
    # All keywords should follow the list rule to reduce false positives
    padding = "y" * 100
    assert analyzer.analyze(padding + "\n* Do not fail.")["results"]["negative_constraints"] is False
    assert analyzer.analyze(padding + "\n* Never fail.")["results"]["negative_constraints"] is False
    assert analyzer.analyze(padding + "\n* Not allowed.")["results"]["negative_constraints"] is False

    # Outside lists, they should be ignored
    assert analyzer.analyze(padding + "\nI do not like this.")["results"]["negative_constraints"] is True
    assert analyzer.analyze(padding + "\nNever say never.")["results"]["negative_constraints"] is True
    assert analyzer.analyze(padding + "\nIt is not working.")["results"]["negative_constraints"] is True

def test_delimiter_variants():
    analyzer = PromptAnalyzer()
    assert analyzer.analyze("```\ncode\n```")["results"]["delimiter_hygiene"] is True
    assert analyzer.analyze("'''\ncode\n'''")["results"]["delimiter_hygiene"] is True
    assert analyzer.analyze("<tag>data</tag>")["results"]["delimiter_hygiene"] is True

def test_cot_relaxed_variants():
    analyzer = PromptAnalyzer()
    assert analyzer.analyze("Make a Plan.")["results"]["cognitive_scaffolding"] is True
    assert analyzer.analyze("Step 1: Init.")["results"]["cognitive_scaffolding"] is True
    assert analyzer.analyze("Phase 1: Start.")["results"]["cognitive_scaffolding"] is True
