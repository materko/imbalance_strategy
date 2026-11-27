#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
LQ_SCORE=wr LQ_MODE=sweep TL_SEED=lq5.jsonl $PY .nightsearch/liqsearch.py 2.3 lqw5.jsonl 5y > .nightsearch/lqw5.log 2>&1
LQ_SCORE=wr LQ_TAG=LQW LQ_F1=nic.jsonl LQ_F5=lqw5.jsonl $PY .nightsearch/lqfinal.py > .nightsearch/lqwfinal.log 2>&1
for R in $(grep -oE "^LQW_[^ ]+ \['[0-9]{8}-[0-9]{6}-[0-9a-f]{6}" .nightsearch/lqwfinal.log | grep -oE "[0-9]{8}-[0-9]{6}-[0-9a-f]{6}"); do $PY .nightsearch/drawcheck.py $R | tr '\n' ' '; echo; done > .nightsearch/lqwdraw.log
echo CHAIN_DONE $(date +%H:%M)
