#!/usr/bin/env bash
# Postaví Python prostredie pre Freqtrade vetvu portu (macOS / Linux).
#
# Windows ekvivalent: setup.ps1
# MultiCharts na macOS nebeží - je to Windows aplikácia. Na Macu sa dá robiť
# jadro (tradebot/), testy a celá Freqtrade vetva.
#
#   ./platforms/freqtrade/scripts/setup.sh
#   PYTHON=python3.12 ./platforms/freqtrade/scripts/setup.sh
#   RECREATE=1 ./platforms/freqtrade/scripts/setup.sh

set -euo pipefail

PYTHON="${PYTHON:-python3}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV="$REPO/.venv"

echo "Repozitar: $REPO"

if [[ "${RECREATE:-0}" == "1" && -d "$VENV" ]]; then
    echo "Mazem existujuci venv..."
    rm -rf "$VENV"
fi

if [[ ! -d "$VENV" ]]; then
    echo "Vytvaram venv v $VENV"
    "$PYTHON" -m venv "$VENV"
fi

PY="$VENV/bin/python"
[[ -x "$PY" ]] || { echo "Nenasiel som $PY" >&2; exit 1; }

echo "Aktualizujem pip..."
"$PY" -m pip install --upgrade pip --quiet

# macOS: freqtrade potrebuje na TA-Lib prelozeny C kniznicny balik.
if [[ "$(uname -s)" == "Darwin" ]] && ! brew list ta-lib >/dev/null 2>&1; then
    echo ""
    echo "POZN: na macOS treba najprv nativnu kniznicu TA-Lib:"
    echo "      brew install ta-lib"
    echo "Ak instalacia nizsie spadne na ta-lib, spusti to a zopakuj."
    echo ""
fi

echo "Instalujem freqtrade (chvilu to trva)..."
"$PY" -m pip install freqtrade

echo "Instalujem lokalny balik tradebot (editovatelne)..."
"$PY" -m pip uninstall -y ibs >/dev/null 2>&1 || true   # stary nazov balika (pred premenovanim na tradebot)
"$PY" -m pip install -e "$REPO[dev]"

echo ""
"$PY" -m freqtrade --version
"$PY" -m pytest "$REPO" -q

echo ""
echo "Hotovo. Dalsi krok:"
echo "  ./platforms/freqtrade/scripts/download-data.sh"
