#!/bin/sh
# IBS Entry Zone s vyšším RR na hube — glrr.py skončí sám, keď sú všetky úlohy hotové (pri páde sa spustí znova).
cd /Users/martin/IBS/.nightsearch
until ../.venv/bin/python glrr.py >> glrr.log 2>&1 && grep -q "glrr koniec" glrr.log; do sleep 30; done
