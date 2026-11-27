#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
$PY .nightsearch/liqsearch.py 1.5 lq1.jsonl > .nightsearch/lq1.log 2>&1
TL_SEED=lq1.jsonl $PY .nightsearch/liqsearch.py 3 lq5.jsonl 5y > .nightsearch/lq5.log 2>&1
$PY .nightsearch/lqfinal.py > .nightsearch/lqfinal.log 2>&1
echo CHAIN_DONE $(date +%H:%M)
