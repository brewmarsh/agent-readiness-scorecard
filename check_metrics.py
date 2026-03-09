from agent_readiness_scorecard.analyzers.python import PythonAnalyzer
import json

analyzer = PythonAnalyzer()
stats = analyzer.get_function_stats("scripts/process_scorecard.py")
print(json.dumps(stats, indent=2))
