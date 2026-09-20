#!/bin/zsh
# Compute the sha256 of the GitHub release tarball and write it into the formula.
#
# Usage:
#   ./packaging/homebrew/release-sha.sh 1.0.0
#
# Requires: a tag/release v<version> already created in the GitHub repo.

set -e
VERSION="${1:?Provide a version, e.g. 1.0.0}"
USER="rafalgawlik"
REPO="morning-agent"
FORMULA="${0:A:h}/morning-agent.rb"

URL="https://github.com/$USER/$REPO/archive/refs/tags/v$VERSION.tar.gz"
echo "Downloading: $URL"
SHA=$(curl -fsSL "$URL" | shasum -a 256 | awk '{print $1}')
echo "sha256 = $SHA"

# Replace the placeholder / previous sha in the formula.
sed -i '' -E "s|^  sha256 \"[^\"]*\"|  sha256 \"$SHA\"|" "$FORMULA"
echo "Updated $FORMULA"
