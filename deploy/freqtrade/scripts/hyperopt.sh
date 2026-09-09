#!/usr/bin/env bash
# Hyperopt s priestorom, ktory strategia odporucuje (jej `hyperopt_cls.SUGGESTED`).
# Vlastny priestor sa zadava priamo prikazom, nie tymto obalom:
#
#   PY -m tester.webapp.cli hyperopt --param rrRatio=2:8:0.5 --param slLookback=5:40:1 \
#      --goal break_even --min-trades 15 --timerange 20250904-20260904
#
# Podrobnosti a ako nastavit hranice: docs/HYPEROPT.md
#
#   ./deploy/freqtrade/scripts/hyperopt.sh 20250904-20260904 200
set -euo pipefail

TIMERANGE="${1:?pouzitie: hyperopt.sh <timerange> [epochs] [goal]}"
EPOCHS="${2:-200}"
GOAL="${3:-break_even}"

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
py="$repo/.venv/bin/python"
[ -x "$py" ] || py="$repo/.venv/Scripts/python.exe"

cd "$repo"
exec "$py" -m tester.webapp.cli hyperopt --suggested \
    --timerange "$TIMERANGE" --epochs "$EPOCHS" --goal "$GOAL" \
    --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
    --note "hyperopt: odporucany priestor, okno $TIMERANGE"
