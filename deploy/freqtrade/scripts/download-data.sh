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
#   ./deploy/freqtrade/scripts/download-data.sh
#   TIMERANGE=20260801-20260905 ./deploy/freqtrade/scripts/download-data.sh
#   SKIP_COINBASE=1 DAYS=180 ./deploy/freqtrade/scripts/download-data.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FT="$REPO/deploy/freqtrade"
USERDIR="$FT/user_data"
PY="$REPO/.venv/bin/python"

[[ -x "$PY" ]] || { echo "Chyba .venv - spusti najprv ./deploy/freqtrade/scripts/setup.sh" >&2; exit 1; }

DAYS="${DAYS:-60}"
if [[ -n "${TIMERANGE:-}" ]]; then
    RANGE=(--timerange "$TIMERANGE")
else
    RANGE=(--days "$DAYS")
fi
ERASE_ARG=()
[[ "${ERASE:-0}" == "1" ]] && ERASE_ARG=(--erase)

# Sviecky nepatria do userdiru Freqtradu, ale do spolocneho data/<zdroj>/ - z toho
# istého stromu ich cita aj emulator MultiCharts (tester/engines.py).
download() {
    # `datadir` je to, co dostane Freqtrade: pri futures o uroven vyssie (podadresar
    # `futures/` si doplni sam), pri spote priamo na `spot/`. Na disku je to sumerne.
    local label="$1" config="$2" datadir="$3"; shift 3
    echo ""
    echo "=== $label ==="
    echo "timeframes: $*"
    "$PY" -m freqtrade download-data \
        --config "$FT/$config" \
        --userdir "$USERDIR" \
        --datadir "$REPO/data/tester/$datadir" \
        --timeframes "$@" \
        "${RANGE[@]}" "${ERASE_ARG[@]}"
}

if [[ "${SKIP_BINANCE:-0}" != "1" ]]; then
    download "Binance BTC/USDT:USDT (futures)" config.binance.json binance 1m 3m 5m
    download "Binance BTC/USDT + ETH/USDT (spot)" config.binance.spot.json binance/spot 1m 3m 5m 15m
fi

if [[ "${SKIP_COINBASE:-0}" != "1" ]]; then
    download "Coinbase BTC/USD (spot, referencne)" config.coinbase.json coinbase/spot 1m 5m
    echo "Coinbase 3m sa nestahuje - burza ho neponuka. Strategia si ho poskladá z 1m."
fi

echo ""
echo "=== Co je stiahnute ==="
"$PY" -m freqtrade list-data --userdir "$USERDIR" --datadir "$REPO/data/tester/binance" --config "$FT/config.binance.json"
"$PY" -m freqtrade list-data --userdir "$USERDIR" --datadir "$REPO/data/tester/coinbase/spot" --config "$FT/config.coinbase.json"

echo
echo "=== Delim na rocne subory pre git ==="
"$PY" -m tester.data_archive split
echo
echo "Commituj len data_archive/tester/ - pracovne subory"
echo "v data/ su v .gitignore. Po klonovani sa poskladaju prikazom:"
echo "  python -m tester.data_archive merge"
