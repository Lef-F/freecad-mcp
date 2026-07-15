#!/usr/bin/env bash
# Clone CAD-tooling source (ezdxf, QCAD) into vendor/ (gitignored) for Claude source lookups,
# mirroring scripts/setup-freecad-source.sh. Versions pinned in .EZDXF_VERSION / .QCAD_VERSION.
#
# Usage: ./scripts/setup-cad-sources.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

clone_one() {
  local name="$1" url="$2" ver="$3"
  local target="$REPO_ROOT/vendor/$name"
  if [[ -d "$target/.git" ]]; then
    echo "[$name] already present ($(git -C "$target" rev-parse --short HEAD)) — skip"; return
  fi
  mkdir -p "$REPO_ROOT/vendor"
  if [[ -n "$ver" && "$ver" != "default" ]]; then
    echo "[$name] cloning tag $ver (shallow)..."
    if ! git clone --depth 1 --branch "$ver" "$url" "$target" 2>/dev/null; then
      echo "[$name] tag '$ver' not found — cloning default branch instead..."
      git clone --depth 1 "$url" "$target"
    fi
  else
    echo "[$name] cloning default branch (shallow)..."
    git clone --depth 1 "$url" "$target"
  fi
  echo "[$name] -> $(git -C "$target" rev-parse --short HEAD)  $(git -C "$target" describe --tags 2>/dev/null || true)"
}

clone_one ezdxf https://github.com/mozman/ezdxf.git "$(tr -d '[:space:]' < "$REPO_ROOT/.EZDXF_VERSION" 2>/dev/null || echo default)"
clone_one qcad  https://github.com/qcad/qcad.git    "$(tr -d '[:space:]' < "$REPO_ROOT/.QCAD_VERSION"  2>/dev/null || echo default)"
echo "Done. Sources in vendor/ezdxf, vendor/qcad (gitignored)."
