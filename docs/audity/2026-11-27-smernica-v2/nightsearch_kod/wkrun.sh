#!/bin/sh
# Víkendové hľadanie: beží do WK_DEADLINE (pri páde sa samo spustí znova a pokračuje), potom tabuľky, profily, behy a push.
cd /Users/martin/IBS/.nightsearch
while [ $(date +%s) -lt $WK_DEADLINE ]; do
  ../.venv/bin/python wksearch.py >> wksearch.log 2>&1
  echo "koniec behu $(date)" >> wksearch.log
  sleep 20
done
../.venv/bin/python wkfinal.py save > wkfinal.log 2>&1
