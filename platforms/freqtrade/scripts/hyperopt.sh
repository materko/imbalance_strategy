#!/usr/bin/env bash
# Preladi prahy strategie hyperoptom. Podrobnosti su v hyperopt.ps1.
#
#   ./platforms/freqtrade/scripts/hyperopt.sh 20250901-20260904 300
#   IBS_PROFILE=btcusdt_3m_binance_hyper ./platforms/freqtrade/scripts/hyperopt.sh 20260601-20260904 200
set -euo pipefail

TIMERANGE="${1:?pouzitie: hyperopt.sh <timerange> [epochs] [loss]}"
EPOCHS="${2:-300}"
LOSS="${3:-CalmarHyperOptLoss}"

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ft="$repo/platforms/freqtrade"
py="$repo/.venv/bin/python"
[ -x "$py" ] || py="$repo/.venv/Scripts/python.exe"

export IBS_PROFILE="${IBS_PROFILE:-btcusdt_3m_binance_hyper}"
echo "Profil: $IBS_PROFILE"
echo "Okno:   $TIMERANGE   epoch: $EPOCHS   loss: $LOSS"
echo
echo "POZOR: pri 10 parametroch a radovo stovkach obchodov je pretrenovanie realne."
echo "Vysledok VZDY over na inom okne, nez na akom si ladil."
echo

exec "$py" -m freqtrade hyperopt \
    --config "$ft/config.binance.json" \
    --userdir "$ft/user_data" \
    --strategy IBSImbalanceStrategy \
    --hyperopt-loss "$LOSS" \
    --timerange "$TIMERANGE" \
    --epochs "$EPOCHS" \
    --spaces buy sell
