from agent_readiness_scorecard.analyzers.python import PythonAnalyzer
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python3 check_metrics.py <filepath>")
    sys.exit(1)

filepath = sys.argv[1]
analyzer = PythonAnalyzer()
stats = analyzer.get_function_stats(filepath)
print(json.dumps(stats, indent=2))
