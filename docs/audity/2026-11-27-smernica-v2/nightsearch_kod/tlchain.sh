#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
# 1. faza bezi (do ~21:00); potom pokracovanie z toho isteho suboru do 23:30
while pgrep -f "tlsearch.py 1.5 tl1.jsonl" >/dev/null; do sleep 30; done
H1=$(python3 -c "import time,datetime;n=datetime.datetime.now();t=n.replace(hour=23,minute=30,second=0);print(max(0.1,(t-n).total_seconds()/3600))")
$PY .nightsearch/tlsearch.py $H1 tl1.jsonl >> .nightsearch/tl1.log 2>&1
# 2. faza: pat rokov, start z najlepsich z 1. fazy, do 06:15
H2=$(python3 -c "import datetime;n=datetime.datetime.now();t=(n+datetime.timedelta(days=1)).replace(hour=6,minute=15,second=0) if n.hour>=12 else n.replace(hour=6,minute=15,second=0);print(max(0.1,(t-n).total_seconds()/3600))")
TL_SEED=tl1.jsonl $PY .nightsearch/tlsearch.py $H2 tl5.jsonl 5y > .nightsearch/tl5.log 2>&1
echo CHAIN_DONE $(date +%H:%M)
