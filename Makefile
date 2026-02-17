.PHONY: audit security-scan lint-prompts

# Run all quality and security checks
audit: security-scan lint-prompts
	@echo "✅ Audit complete. Code is safe to push."

# Check for known vulnerabilities in dependencies and code
security-scan:
	@echo "🔍 Running Bandit (SAST)..."
	bandit -r src/ -ll
	@echo "🔍 Running Safety (Dependency Check)..."
	safety check

# Lint your internal agent prompts
lint-prompts:
	@echo "📝 Validating internal prompts..."
	agent-score check-prompts src/agent_scorecard/prompts/*.txt
