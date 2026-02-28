#!/usr/bin/env bash
# Clone FreeCAD source at the version specified in .FREECAD_VERSION
# into vendor/FreeCAD/ (gitignored). Used by Claude for source lookups.
#
# Usage:
#   ./scripts/setup-freecad-source.sh          # use version from .FREECAD_VERSION
#   ./scripts/setup-freecad-source.sh 1.0.2    # override version

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/.FREECAD_VERSION"
TARGET_DIR="$REPO_ROOT/vendor/FreeCAD"
FREECAD_REPO="https://github.com/FreeCAD/FreeCAD.git"

# Resolve version
if [[ "${1:-}" != "" ]]; then
    VERSION="$1"
elif [[ -f "$VERSION_FILE" ]]; then
    VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
else
    echo "Error: no version specified and .FREECAD_VERSION not found." >&2
    exit 1
fi

echo "FreeCAD version: $VERSION"
echo "Target: $TARGET_DIR"

if [[ -d "$TARGET_DIR/.git" ]]; then
    CURRENT_TAG="$(git -C "$TARGET_DIR" describe --tags --exact-match 2>/dev/null || echo "unknown")"
    if [[ "$CURRENT_TAG" == "$VERSION" ]]; then
        echo "Already at $VERSION — nothing to do."
        exit 0
    fi
    echo "Updating from $CURRENT_TAG to $VERSION..."
    git -C "$TARGET_DIR" fetch --depth=1 origin "refs/tags/$VERSION:refs/tags/$VERSION"
    git -C "$TARGET_DIR" checkout "$VERSION"
    echo "Done."
else
    mkdir -p "$(dirname "$TARGET_DIR")"
    echo "Cloning FreeCAD $VERSION (shallow)..."
    git clone --depth 1 --branch "$VERSION" "$FREECAD_REPO" "$TARGET_DIR"
    echo "Done."
fi
