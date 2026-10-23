#!/usr/bin/env bash
# Print one version's section of CHANGELOG.md: the lines after its
# "## [X.Y.Z]" heading up to (not including) the next "## [" heading.
#
# release.yml uses the output as the GitHub release body, and
# tests/test_release.py runs this file, so it is the single definition of the
# release notes.
#
# Usage: scripts/release_notes.sh VERSION [CHANGELOG]
#   VERSION is X.Y.Z (a leading "v" is stripped). Exits 1 when the changelog
#   has no section for VERSION, 2 on a usage error.
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: scripts/release_notes.sh VERSION [CHANGELOG]" >&2
  exit 2
fi

VERSION="${1#v}"
CHANGELOG="${2:-$(dirname -- "${BASH_SOURCE[0]}")/../CHANGELOG.md}"

awk -v heading="## [$VERSION]" '
  /^## \[/ {
    if (found) exit
    if (index($0, heading) == 1) { found = 1; next }
  }
  found { print }
  END { if (!found) exit 1 }
' "$CHANGELOG"
