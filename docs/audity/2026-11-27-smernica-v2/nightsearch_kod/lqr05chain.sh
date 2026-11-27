#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
LQ_RRS=0.5 LQ_MIN_TR=200 LQ_MAX_TR=300 LQ_SCORE=wr LQ_MODE=sweep TL_SEED=lqseed_r05.jsonl $PY .nightsearch/liqsearch.py 1.5 lqr05.jsonl 5y > .nightsearch/lqr05.log 2>&1
echo CHAIN_DONE $(date +%H:%M)
LQ_RRS=0.5 LQ_MIN_TR=200 LQ_MAX_TR=300 LQ_SCORE=wr LQ_TAG=LQR05 LQ_F1=nic.jsonl LQ_F5=lqr05.jsonl $PY .nightsearch/lqfinal.py > .nightsearch/lqr05final.log 2>&1
for R in $(grep -oE "^LQR05_[^ ]+ \['[0-9]{8}-[0-9]{6}-[0-9a-f]{6}" .nightsearch/lqr05final.log | grep -oE "[0-9]{8}-[0-9]{6}-[0-9a-f]{6}"); do $PY .nightsearch/drawcheck.py $R | tr '\n' ' '; echo; done > .nightsearch/lqr05draw.log
echo FINAL_DONE $(date +%H:%M)
