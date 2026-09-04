#!/usr/bin/env bash
# Stiahne sviečkové dáta pre obe burzy (macOS / Linux). Windows: download-data.ps1
#
# Timeframy (ARCHITECTURE_port.md §7):
#   3m = timeframe stratégie (signály; *MaxBars limity sú v BAROCH)
#   5m = zoneDetectionTF - detekcia SD zón
#   1m = timeframe_detail pre backtest
#
# Coinbase NEVIE 3m (ccxt ponúka len 1m/5m/15m/30m/1h/2h/6h/1d). Sťahujú sa len
# oficiálne TF - 3m si z 1m poskladá samotná Freqtrade stratégia. Na disk sa
# žiadny umelý timeframe neukladá.
#
#   ./platforms/freqtrade/scripts/download-data.sh
#   TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/download-data.sh
#   SKIP_COINBASE=1 DAYS=180 ./platforms/freqtrade/scripts/download-data.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FT="$REPO/platforms/freqtrade"
USERDIR="$FT/user_data"
PY="$REPO/.venv/bin/python"

[[ -x "$PY" ]] || { echo "Chyba .venv - spusti najprv ./platforms/freqtrade/scripts/setup.sh" >&2; exit 1; }

DAYS="${DAYS:-60}"
if [[ -n "${TIMERANGE:-}" ]]; then
    RANGE=(--timerange "$TIMERANGE")
else
    RANGE=(--days "$DAYS")
fi
ERASE_ARG=()
[[ "${ERASE:-0}" == "1" ]] && ERASE_ARG=(--erase)

download() {
    local label="$1" config="$2"; shift 2
    echo ""
    echo "=== $label ==="
    echo "timeframes: $*"
    "$PY" -m freqtrade download-data \
        --config "$FT/$config" \
        --userdir "$USERDIR" \
        --timeframes "$@" \
        "${RANGE[@]}" "${ERASE_ARG[@]}"
}

if [[ "${SKIP_BINANCE:-0}" != "1" ]]; then
    download "Binance BTC/USDT:USDT (futures)" config.binance.json 1m 3m 5m
fi

if [[ "${SKIP_COINBASE:-0}" != "1" ]]; then
    download "Coinbase BTC/USD (spot, referencne)" config.coinbase.json 1m 5m
    echo "Coinbase 3m sa nestahuje - burza ho neponuka. Strategia si ho poskladá z 1m."
fi

echo ""
echo "=== Co je stiahnute ==="
"$PY" -m freqtrade list-data --userdir "$USERDIR" --config "$FT/config.binance.json"
"$PY" -m freqtrade list-data --userdir "$USERDIR" --config "$FT/config.coinbase.json"
