#!/bin/sh
# Vyšší winrate pri pevnom RR na hube (glwr.py) — beží donekonečna, pri páde znova (pokračuje z wr_state.json).
cd /Users/martin/IBS/.nightsearch
while [ ! -f wr_stop ]; do
  ../.venv/bin/python glwr.py >> glwr.log 2>&1
  echo "koniec behu $(date)" >> glwr.log
  sleep 30
done
