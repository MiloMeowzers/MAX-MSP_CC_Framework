#!/usr/bin/env bash
# Build the framework release archive: `git archive` of a committed tree with
# the MAX-MSP_CC_Framework/ prefix. Contents are governed by the export-ignore
# rules in the archived tree's .gitattributes (review I2, simplification S10).
#
# release.yml and tests/test_release.py both run this file -- it is the single
# definition of the release archive.
#
# Usage: scripts/build_release.sh OUTPUT.tar.gz [TREEISH]
#   TREEISH defaults to HEAD. Any git or tar failure exits non-zero.
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: scripts/build_release.sh OUTPUT.tar.gz [TREEISH]" >&2
  exit 2
fi

OUT_ARG="$1"
TREEISH="${2:-HEAD}"

# Resolve OUTPUT to an absolute path before changing directory.
OUT_DIR="$(dirname -- "$OUT_ARG")"
mkdir -p -- "$OUT_DIR"
OUT="$(cd -- "$OUT_DIR" && pwd -P)/$(basename -- "$OUT_ARG")"

# git archive run from a subdirectory archives only that subdirectory, so
# always run from the repository top level.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
TOP="$(git rev-parse --show-toplevel)"
cd -- "$TOP"

# Never leave a partial archive behind on failure.
trap 'rm -f -- "$OUT"' ERR

git archive --format=tar.gz --prefix=MAX-MSP_CC_Framework/ -o "$OUT" "$TREEISH"

# Integrity check: the archive must list cleanly.
tar -tzf "$OUT" > /dev/null

echo "$OUT"
