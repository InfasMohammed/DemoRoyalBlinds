#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
python3 --version
node --version
mkdir -p .runtime
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --cache-dir "$project_root/.runtime/pip-cache" -r backend/requirements.lock.txt
cd frontend
npm ci --cache "$project_root/.runtime/npm-cache" --no-audit --no-fund
npm run build
