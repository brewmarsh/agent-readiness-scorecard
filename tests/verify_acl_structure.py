from agent_scorecard.analyzer import calculate_acl

def verify():
    # File A (flat, long): Depth=1, Complexity=1, LOC=200
    acl_a = calculate_acl(complexity=1.0, loc=200, depth=1)

    # File B (short, deeply nested): Depth=5, Complexity=2, LOC=20
    acl_b = calculate_acl(complexity=2.0, loc=20, depth=5)

    print(f"Flat/Long File ACL: {acl_a}")   # Expected: (1*2) + (1*1.5) + (200/50) = 2 + 1.5 + 4 = 7.5
    print(f"Short/Nested File ACL: {acl_b}") # Expected: (5*2) + (2*1.5) + (20/50) = 10 + 3 + 0.4 = 13.4

    assert acl_a < acl_b
    print("Verification Successful: Flat/Long files score better than Short/Nested files.")

if __name__ == "__main__":
    verify()
