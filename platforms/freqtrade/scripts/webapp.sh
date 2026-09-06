#!/usr/bin/env bash
# Webová aplikácia pre testerov bez Dockeru (macOS / Linux). Windows: webapp.ps1
#
# Stačí Python 3.11+ a git (na macOS aj `brew install ta-lib`, viď docs/RUNNING.md §B).
# Ak chýba .venv, skript ho sám postaví cez setup.sh (prvýkrát ~10 minút). Ak chýbajú
# pracovné dáta, webapp ich pri štarte zloží z data_archive/. Po štarte otvorí prehliadač.
#
#   ./platforms/freqtrade/scripts/webapp.sh
#   TRADEBOT_WEB_PORT=9000 ./platforms/freqtrade/scripts/webapp.sh
#   NO_BROWSER=1 ./platforms/freqtrade/scripts/webapp.sh
#
# Viď docs/WEBAPP.md.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$REPO/.venv/Scripts/python.exe"   # Git Bash na Windows
if [[ ! -x "$PY" ]]; then
    echo "Chyba .venv - staviam prostredie (prvykrat ~10 minut)..."
    "$HERE/setup.sh"
    PY="$REPO/.venv/bin/python"
    [[ -x "$PY" ]] || PY="$REPO/.venv/Scripts/python.exe"
    [[ -x "$PY" ]] || { echo "setup.sh nevytvoril venv" >&2; exit 1; }
fi

export TRADEBOT_WEB_HOST="${TRADEBOT_WEB_HOST:-127.0.0.1}"
export TRADEBOT_WEB_PORT="${TRADEBOT_WEB_PORT:-8765}"
URL="http://$TRADEBOT_WEB_HOST:$TRADEBOT_WEB_PORT"
echo "IBS webapp: $URL  (Ctrl+C ukonci)"

if [[ "${NO_BROWSER:-0}" != "1" ]]; then
    (
        for _ in $(seq 1 60); do
            if curl -fs "$URL/api/queue" >/dev/null 2>&1; then
                if command -v open >/dev/null; then open "$URL"
                elif command -v xdg-open >/dev/null; then xdg-open "$URL"
                fi
                break
            fi
            sleep 1
        done
    ) &
fi

cd "$REPO"
exec "$PY" -m tradebot.webapp
