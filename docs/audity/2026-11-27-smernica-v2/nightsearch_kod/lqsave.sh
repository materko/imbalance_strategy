#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
until grep -q FINAL_DONE .nightsearch/lqr05chain.log 2>/dev/null && grep -q CHAIN_DONE .nightsearch/lqbchain.log 2>/dev/null; do sleep 60; done
$PY .nightsearch/lqalt.py > .nightsearch/lqalt.log 2>&1
for R in $(grep -oE "^LQR05_ALT_[^ ]+ [0-9]{8}-[0-9]{6}-[0-9a-f]{6}" .nightsearch/lqalt.log | awk '{print $2}'); do $PY .nightsearch/drawcheck.py $R | tr '\n' ' '; echo; done > .nightsearch/lqaltdraw.log
$PY -m tester.webapp.cli push > .nightsearch/lqpush.log 2>&1
echo SAVE_DONE $(date +%H:%M)
