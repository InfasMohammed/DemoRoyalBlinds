#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
if [[ ! -x backend/.venv/bin/python || ! -d frontend/node_modules ]] || ! command -v uv >/dev/null 2>&1; then
  echo 'Run bash scripts/setup.sh first.' >&2
  exit 1
fi
export UV_CACHE_DIR="$project_root/.runtime/uv-cache"
uv run --locked --project backend python - <<'PY'
import socket
for port in (8000, 5173):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', port))
        except OSError:
            raise SystemExit(f'Port {port} is occupied. Stop the existing app instance before starting another.')
PY
api_pid=''
ui_pid=''
cleanup() {
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
  if [[ -n "$ui_pid" ]]; then kill "$ui_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
(cd backend && exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
api_pid=$!
(cd frontend && exec node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173 --strictPort) &
ui_pid=$!
wait -n "$api_pid" "$ui_pid"
