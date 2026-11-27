#!/bin/sh
# Hľadanie SPX sila + DAILY OPEN (8.–10. 10. 2026): beží do MK_DEADLINE, pri páde sa spustí znova.
cd /Users/martin/IBS/.nightsearch
while [ $(date +%s) -lt $WK_DEADLINE ]; do
  ../.venv/bin/python wksearch.py >> mksearch.log 2>&1
  echo "koniec behu $(date)" >> mksearch.log
  sleep 20
done
