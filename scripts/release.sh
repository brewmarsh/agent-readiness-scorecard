#!/bin/bash

# Exit on any error
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Usage: ./scripts/release.sh v0.1.0"
  exit 1
fi

# 1. Ensure git is clean
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Error: Your git working directory is not clean. Commit or stash changes first."
  exit 1
fi

# 2. Tag the release
echo "🏷️  Tagging version $VERSION..."
git tag -a "$VERSION" -m "Release $VERSION"

# 3. Clean previous builds
echo "🧹 Cleaning old builds..."
rm -rf dist/ build/ *.egg-info

# 4. Build the package
echo "📦 Building package..."
python -m build

# 5. Verify the artifact
echo "🔍 Verifying build..."
ls -lh dist/

echo "✅ Done! To push this release to GitHub, run:"
echo "   git push origin $VERSION"
