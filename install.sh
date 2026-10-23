#!/usr/bin/env bash
set -euo pipefail

REPO="taylorbrook/MAX-MSP_CC_Framework"
RELEASE_URL="https://github.com/${REPO}/releases/latest/download/framework.tar.gz"

# ---------------------------------------------------------------------------
# Dependency check (review IN-06): Python 3.10+, the Python packages the DSP
# simulation, smoke tests and pre-flight gate need, and git (Rule #7
# auto-commits every save). Warnings only; returns 1 when Python 3.10+ is
# missing. Uses only shell builtins, python3 and git.
# ---------------------------------------------------------------------------

check_deps() {
  local info ok=0
  if ! command -v git >/dev/null 2>&1; then
    echo "WARNING: git not found. The framework commits every patch save (Rule #7); install git."
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "WARNING: Python 3 not found. The framework requires Python 3.10+ for the validation engine."
    return 1
  fi
  # Prints "<major>.<minor> <1 if >= 3.10 else 0> <comma-separated missing modules>"
  info=$(python3 -c '
import sys
missing = []
for m in ("numpy", "scipy", "pytest"):
    try:
        __import__(m)
    except Exception:
        missing.append(m)
print("%d.%d %d %s" % (sys.version_info[0], sys.version_info[1],
                       int(sys.version_info >= (3, 10)), ",".join(missing)))
' 2>/dev/null) || info=""
  if [ -z "$info" ]; then
    echo "WARNING: python3 did not run. The framework requires Python 3.10+ for the validation engine."
    return 1
  fi
  set -- $info
  if [ "$2" != "1" ]; then
    echo "WARNING: Python 3.10+ required. Found Python $1"
    ok=1
  fi
  if [ -n "${3:-}" ]; then
    echo "WARNING: Python packages missing: ${3//,/, } (needed by the DSP simulation, smoke tests and the DSP pre-flight gate; validation works without them)."
    echo "  Install them from the project directory: python3 -m pip install -r requirements-dev.txt"
  fi
  return $ok
}

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------

if [ $# -eq 0 ]; then
  echo "Usage: install.sh <project-name>" >&2
  echo "       install.sh --check-deps   (only check Python, its packages and git)" >&2
  echo "" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash -s my-project" >&2
  exit 1
fi

if [ "$1" = "--check-deps" ]; then
  check_deps
  exit $?
fi

PROJECT_NAME="$1"

if [ -d "$PROJECT_NAME" ]; then
  echo "Error: Directory '${PROJECT_NAME}' already exists." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Cleanup on failure
# ---------------------------------------------------------------------------

cleanup() {
  if [ -d "$PROJECT_NAME" ]; then
    rm -rf "$PROJECT_NAME"
  fi
}
trap cleanup ERR

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

echo ""
echo "Creating MAX/MSP Claude Code Framework in ${PROJECT_NAME}..."
echo ""

mkdir -p "$PROJECT_NAME"
curl -fsSL "$RELEASE_URL" | tar xz -C "$PROJECT_NAME" --strip-components=1

# Create the patches directory. No active-project pointer is written: a fresh install has no active project until /max-new or /max-switch sets one.
mkdir -p "${PROJECT_NAME}/patches"

# Initialize git repo
git init "$PROJECT_NAME" > /dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Dependency check (warnings only: the install itself is complete)
# ---------------------------------------------------------------------------

check_deps || true

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "Done! Your MAX/MSP Claude Code Framework project is ready."
echo ""
echo "Next steps:"
echo "  cd ${PROJECT_NAME}"
echo "  claude"
echo "  /max-new my-first-patch"
echo ""
echo "Prerequisites:"
echo "  - Claude Code (https://docs.anthropic.com/en/docs/claude-code)"
echo "  - MAX 9 (https://cycling74.com/products/max)"
echo "  - Python 3.10+ (for the validation engine)"
echo ""
