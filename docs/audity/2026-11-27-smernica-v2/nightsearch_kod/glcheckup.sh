#!/bin/sh
# Krok 7 smernice: analytika (cli checkup) na profile PREŠIEL SMERNICAMI č. 1 danej stratégie.
# glcheckup.sh <kľúč> <meno profilu bez .json>
cd /Users/martin/IBS || exit 1
K=$1; P=$2; D=$(date +%F)
F=.nightsearch/checkup/${K}_${P}_$D.json
cp tester/profiles/$P.json "$F"
PAIR=$(cd .nightsearch && ../.venv/bin/python -c "import glsearch as G;print(G.instr(\"$K\")[1])" 2>/dev/null || echo MNQ/USD)
FEE=$(cd .nightsearch && ../.venv/bin/python -c "import glsearch as G;print(G.fee(\"$K\"))" 2>/dev/null || echo 1.755e-05)
TF=$(python3 -c "import json;print(json.load(open('$F'))['_timeframe'])")
TITLE=$(python3 -c "import json;print(json.load(open('$F'))['_title'].split(':')[0].replace('PREŠIEL SMERNICAMI — ',''))")
.venv/bin/python -m tester.webapp.cli checkup --strategy $K --profile "$F" --pair "$PAIR" --engine multicharts --timeframe $TF \
  --fee $FEE --wallet 60000 --note "Smernica krok 7: analytika $TITLE (PREŠIEL SMERNICAMI)" > .nightsearch/checkup/$K.log 2>&1
echo "$K hotovo: $(grep -c 'done' .nightsearch/checkup/$K.log) okien"
