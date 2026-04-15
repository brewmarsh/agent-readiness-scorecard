from agent_readiness_scorecard.analyzers.python import PythonAnalyzer

analyzer = PythonAnalyzer()


def check_file(filepath):
    print(f"--- {filepath} ---")
    stats = analyzer.get_function_stats(filepath)
    red = [s for s in stats if s["acl"] > 15]
    yellow = [s for s in stats if 10 < s["acl"] <= 15]

    print("Red ACL functions:")
    for s in red:
        print(f"  {s['name']}: {s['acl']:.2f} (line {s['lineno']})")

    print("Yellow ACL functions:")
    for s in yellow:
        print(f"  {s['name']}: {s['acl']:.2f} (line {s['lineno']})")
    print()


check_file("scripts/process_scorecard.py")
check_file("src/agent_readiness_scorecard/main.py")
check_file("src/agent_readiness_scorecard/report.py")
