# Agent Scorecard

A tool to analyze codebases for AI-Agent Friendliness.

## Usage

    agent-score [path]
    agent-score --help

## Scoring

- Lines of Code: -1 point per 10 lines over 200.
- Complexity: -5 points if average complexity > 10.
- Type Hints: -20 points if < 50% functions have type hints.
