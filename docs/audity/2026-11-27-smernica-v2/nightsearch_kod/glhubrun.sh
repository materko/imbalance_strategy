#!/bin/sh
# Hľadanie podľa smernice na TradeHube — beží donekonečna, pri páde sa spustí znova (pokračuje z hub_state.json).
cd /Users/martin/IBS/.nightsearch
while true; do
  ../.venv/bin/python glhub.py >> glhub.log 2>&1
  echo "koniec behu $(date)" >> glhub.log
  sleep 30
done
