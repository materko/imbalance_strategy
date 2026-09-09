#!/usr/bin/env bash
# Surové Dukascopy dáta -> dáta pre Tester (webapp) aj pre MultiCharts (macOS / Linux).
# Windows: dukas-import.ps1. Podrobne: docs/DATA.md.
#
#   ./dukas-import.sh ~/dukas/NAS100_M1_10Y.csv --symbol NAS100
#   ./dukas-import.sh ~/dukas/NAS100_M1_10Y.csv --symbol NAS100 --from 2021-01-01
#   ./dukas-import.sh ~/dukas/EURUSD_M1.csv --symbol EURUSD --point-value 100000 --tick 0.00001
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
    exec "$PY" -m tester.dukas_import --help
fi
exec "$PY" -m tester.dukas_import "$@"
