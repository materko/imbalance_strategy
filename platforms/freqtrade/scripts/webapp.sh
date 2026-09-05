#!/usr/bin/env bash
# Webová aplikácia pre testerov (macOS / Linux). Windows: webapp.ps1
#
#   ./platforms/freqtrade/scripts/webapp.sh
#   IBS_WEB_PORT=9000 ./platforms/freqtrade/scripts/webapp.sh
#
# Viď docs/WEBAPP.md.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$REPO/.venv/Scripts/python.exe"
[[ -x "$PY" ]] || { echo "Chyba .venv - spusti najprv ./platforms/freqtrade/scripts/setup.sh" >&2; exit 1; }

cd "$REPO"
exec "$PY" -m ibs.webapp
