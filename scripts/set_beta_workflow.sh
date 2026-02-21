#!/bin/bash

# scripts/set_beta_workflow.sh
# This script configures the repository's default branch to 'beta'
# and applies branch protection to 'main' via the GitHub CLI.

set -e

# 1. Prerequisite check: Ensure the user is authenticated with GitHub CLI
echo "Checking GitHub CLI authentication status..."
gh auth status || {
  echo "❌ Authentication required. Please run 'gh auth login' to continue."
  exit 1
}
echo "✅ Authenticated."

# 2. Identify the repository
REPO_FULL_NAME=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO_FULL_NAME" ]; then
  echo "❌ Error: Could not determine the repository name. Are you inside a GitHub repository?"
  exit 1
fi
echo "Target repository: $REPO_FULL_NAME"

# 3. Set the default branch to 'beta'
# This operation is idempotent.
echo "🔄 Setting default branch to 'beta'..."
if gh repo edit "$REPO_FULL_NAME" --default-branch beta > /dev/null 2>&1; then
  echo "✅ Successfully set default branch to 'beta'."
else
  # Fallback check for idempotency: maybe it's already beta
  CURRENT_DEFAULT=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
  if [ "$CURRENT_DEFAULT" == "beta" ]; then
    echo "✅ Default branch is already set to 'beta'."
  else
    echo "⚠️ Warning: Could not set default branch to 'beta'. Ensure the branch exists on remote."
  fi
fi

# 4. Apply branch protection to the 'main' branch
# Required settings:
# - Require pull request before merging
# - Require at least 1 approving review
# - Enforce for admins
echo "🛡️ Applying branch protection to 'main'..."

# The 'gh api' PUT request to /protection is idempotent.
# We include required fields: required_status_checks, enforce_admins, required_pull_request_reviews, restrictions.
# Note: Using -f flags to build the JSON payload.
# We run the command directly in the if-statement to handle errors gracefully with 'set -e'.
if gh api -X PUT "/repos/$REPO_FULL_NAME/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  -f "required_status_checks=null" \
  -f "enforce_admins=true" \
  -f "required_pull_request_reviews[required_approving_review_count]=1" \
  -f "restrictions=null" > /dev/null 2>&1; then
  echo "✅ Successfully applied branch protection to 'main'."
else
  echo "❌ Error: Failed to apply branch protection. Check your permissions or repository settings."
  exit 1
fi

echo "🎉 Repository workflow configuration complete!"
