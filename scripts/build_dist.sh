#!/usr/bin/env bash
# See infrared/legacydrone.yaml (Publish / Publish main snapshot) and Makefile build / build-dev.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:?usage: build_dist.sh release|dev}"

TMP="$(mktemp -d)"
cp pyproject.toml "$TMP/"
[[ -f uv.lock ]] && cp uv.lock "$TMP/" || true

cleanup() {
  [[ -f "$TMP/pyproject.toml" ]] && cp "$TMP/pyproject.toml" pyproject.toml
  [[ -f "$TMP/uv.lock" ]] && cp "$TMP/uv.lock" uv.lock || true
  rm -rf "$TMP"
}
trap cleanup EXIT

version_release() {
  if [[ -n "${VERSION:-}" ]]; then
    echo "$VERSION"
    return 0
  fi
  local tag
  tag="$(git describe --exact-match --tags HEAD 2>/dev/null || true)"
  if [[ -z "$tag" ]]; then
    echo "make build: set VERSION=1.2.3 or checkout a release tag (git describe --exact-match failed)" >&2
    exit 1
  fi
  echo "${tag#v}"
}

version_dev() {
  git fetch --tags --force 2>/dev/null || true
  local sha base
  # Drone sets DRONE_COMMIT_SHA; local runs use HEAD.
  sha="${DRONE_COMMIT_SHA:-$(git rev-parse HEAD)}"
  base="$(git describe --tags --abbrev=0 2>/dev/null || true)"
  base="${base#v}"
  [[ -n "$base" ]] || base="0.0.0"
  echo "${base}+git.${sha}"
}

case "$MODE" in
  release) ver="$(version_release)" ;;
  dev) ver="$(version_dev)" ;;
  *) echo "build_dist.sh: unknown mode '$MODE' (use release or dev)" >&2; exit 1 ;;
esac

echo "==> uv version $ver"
uv version "$ver" --frozen

echo "==> uv build --no-sources"
uv build --no-sources

echo "Done. Artifacts in dist/; pyproject.toml + uv.lock reverted."
