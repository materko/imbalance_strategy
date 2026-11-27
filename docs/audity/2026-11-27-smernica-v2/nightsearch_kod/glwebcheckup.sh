#!/bin/sh
# Výkon (cli checkup na 5 oknách) pre profily webapp z tester/webapp_vyber.json, ktorým chýba (zoznam webvyber_checkup.txt).
# --no-write: dokument ANALYTIKA.md stratégie (posudok k nastaveniu č. 1) ostáva.
cd /Users/martin/IBS || exit 1
while read K P; do
  case $K in ibsentryesnet|nyvaesnet) PAIR=ES/USD;; fibomgcnet|sigmamgcnet|spravynet|spravy|noamgcnet|mtkorbnet) PAIR=MGC/USD;;
    *mymnet) PAIR=MYM/USD;;
    *) PAIR=$(cd .nightsearch && ../.venv/bin/python -c "import glsearch as G;print(G.instr('$K')[1])" 2>/dev/null || echo MNQ/USD);; esac
  F=$(.venv/bin/python -c "from tester.webapp import profiles as P;print(P.all_paths('$K')['$P'])")
  FEE=$(cd .nightsearch && ../.venv/bin/python -c "import glsearch as G;print(G.fee('$K'))" 2>/dev/null || echo 1.755e-05)   # BTC maker 0,02 % (16. 11. 2026)
  IP=$(.venv/bin/python -c "import json;from tradebot.core.types import INSTRUMENTS as I;print(I[json.load(open('$F'))['_instrument']].symbol)" 2>/dev/null)
  [ -n "$IP" ] && PAIR=$IP   # trh podľa profilu (16. 11. 2026: C# kópie a staré profily dostávali MNQ)
  TF=$(python3 -c "import json;print(json.load(open('$F')).get('_timeframe','3m'))")
  case $K in spravy*) SIZE="";; *) SIZE="--set fixedQty=true --set qty=1 --set skipOverRisk=false";; esac   # SPRÁVY: vlastné riziko z profilu
  echo "$(date +%H:%M) $K $P $PAIR $TF"
  .venv/bin/python -m tester.webapp.cli checkup --strategy $K --profile "$P" --pair "$PAIR" --engine multicharts --timeframe $TF \
    --fee $FEE --wallet 60000 --no-write $SIZE --note "Smernica krok 7: Výkon pre webapp (1 kontrakt) — $P" > /dev/null 2>&1 || echo "  ZLYHAL"
done < .nightsearch/webvyber_checkup.txt
echo "hotovo $(date +%H:%M)"
