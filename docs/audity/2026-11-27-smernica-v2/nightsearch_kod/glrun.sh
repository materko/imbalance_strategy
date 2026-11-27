#!/bin/sh
# Hľadanie podľa smernice — beží donekonečna, pri páde sa spustí znova (pokračuje z gl_state.json).
cd /Users/martin/IBS/.nightsearch
while true; do
  ../.venv/bin/python glsearch.py >> glsearch.log 2>&1
  echo "koniec behu $(date)" >> glsearch.log
  sleep 30
done
