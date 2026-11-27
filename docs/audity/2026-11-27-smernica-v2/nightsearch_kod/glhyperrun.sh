#!/bin/sh
# Hyperopt lokálnych optím — beží donekonečna, pri páde sa spustí znova (pokračuje z hyper_state.json).
cd /Users/martin/IBS/.nightsearch
while true; do
  ../.venv/bin/python glhyper.py >> glhyper.log 2>&1
  echo "koniec behu $(date)" >> glhyper.log
  sleep 30
done
