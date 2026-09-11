#!/usr/bin/env bash
# Databento export (CME futures po kontraktoch) -> front-month 1m pre Tester aj MultiCharts (macOS / Linux).
# Windows: bento-import.ps1. Podrobne: docs/DATA.md.
#
#   ./bento-import.sh ~/bento/glbx-mdp3.ohlcv-1m.csv --symbol MNQ
#   ./bento-import.sh ~/bento/glbx-mdp3.ohlcv-1m.csv --symbol MNQ --from 2020-01-01
#
# Bez parametrov vypíše nápovedu so všetkými prepínačmi.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$REPO/.venv/Scripts/python.exe"   # Git Bash na Windows
if [[ ! -x "$PY" ]]; then
    echo "Chyba .venv - spusti najprv deploy/freqtrade/scripts/setup.sh" >&2
    exit 1
fi

cd "$REPO"
if [[ $# -eq 0 ]]; then
    exec "$PY" -m tester.bento_import --help
fi
exec "$PY" -m tester.bento_import "$@"
