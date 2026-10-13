#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first; see the README for your platform.' >&2
  exit 1
fi
uv --version
node --version
mkdir -p .runtime
export UV_CACHE_DIR="$project_root/.runtime/uv-cache"
uv sync --locked --project backend
cd frontend
npm ci --cache "$project_root/.runtime/npm-cache" --no-audit --no-fund
npm run build
