#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
# sweep uz dobehol
LQ_MODE=breakout $PY .nightsearch/liqsearch.py 1.5 lqb1.jsonl > .nightsearch/lqb1.log 2>&1
LQ_MODE=breakout TL_SEED=lqb1.jsonl $PY .nightsearch/liqsearch.py 2.9 lqb5.jsonl 5y > .nightsearch/lqb5.log 2>&1
LQ_TAG=LQB LQ_F1=lqb1.jsonl LQ_F5=lqb5.jsonl $PY .nightsearch/lqfinal.py > .nightsearch/lqbfinal.log 2>&1
echo CHAIN_DONE $(date +%H:%M)
