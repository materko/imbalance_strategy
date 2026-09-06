#!/usr/bin/env bash
# Backtest s 1m detailom (macOS / Linux). Windows: backtest.ps1
#
# --timeframe-detail 1m je zámerné rozhodnutie (ARCHITECTURE_port.md §7): signály
# sa generujú na uzavretých 3m sviečkach ako v TradingView, ale SL/TP sa vnútri
# sviečky prehráva po 1m krokoch. Stratégiu NIKDY nespúšťaj priamo na 1m -
# všetky *MaxBars limity sú v baroch, nie v minútach.
#
#   ./platforms/freqtrade/scripts/backtest.sh
#   TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/backtest.sh
#   CONFIG=config.coinbase.json ./platforms/freqtrade/scripts/backtest.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FT="$REPO/platforms/freqtrade"
USERDIR="$FT/user_data"
PY="$REPO/.venv/bin/python"

STRATEGY="${STRATEGY:-IBSImbalanceStrategy}"
CONFIG="${CONFIG:-config.binance.json}"
TIMEFRAME_DETAIL="${TIMEFRAME_DETAIL:-1m}"

[[ -x "$PY" ]] || { echo "Chyba .venv - spusti najprv ./platforms/freqtrade/scripts/setup.sh" >&2; exit 1; }

if [[ ! -f "$USERDIR/strategies/$STRATEGY.py" ]]; then
    echo "Strategia $STRATEGY este neexistuje ($USERDIR/strategies/$STRATEGY.py)." >&2
    echo "Adapter sa pise v kroku 4 - viz docs/ARCHITECTURE_port.md par. 8." >&2
    exit 1
fi

# --cache none je POVINNE. Freqtrade cachuje vysledok podla hashu suboru
# strategie, ale nase nastavenia su v profile mimo neho (TRADEBOT_PROFILE), takze
# zmena profilu cache nezneplatni a dostanes ticho stary vysledok.
ARGS=(-m freqtrade backtesting
      --config "$FT/$CONFIG"
      --userdir "$USERDIR"
      --strategy "$STRATEGY"
      --cache none)

[[ "${NO_DETAIL:-0}" == "1" ]] || ARGS+=(--timeframe-detail "$TIMEFRAME_DETAIL")
[[ -n "${TIMERANGE:-}" ]] && ARGS+=(--timerange "$TIMERANGE")
[[ "${EXPORT:-0}" == "1" ]] && ARGS+=(--export signals)

exec "$PY" "${ARGS[@]}"
