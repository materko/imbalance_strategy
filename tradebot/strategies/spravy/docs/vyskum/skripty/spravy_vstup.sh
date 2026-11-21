#!/bin/zsh
# SPRÁVY: kedy vstúpiť po správe — 5/10/15/30/45/60 min, TREND a FADE zvlášť, 5 okien
cd /Users/martin/document/IBS
for mode in TREND FADE; do
 for x in 5 10 15 30 45 60; do
  for w in 20211001-20221001 20221001-20231001 20231001-20241001 20240904-20250904 20250904-20260904; do
   if [[ $mode == TREND ]]; then sets=(--set fadeEvents= --set trendFrom=0 --set trendTo=$x)
   else sets=(--set trendEvents= --set fadeFrom=0 --set fadeTo=$x); fi
   .venv/bin/python -m tester.webapp.cli run --strategy spravy --profile mgc_databento_5m --pair MGC/USD --engine multicharts \
     --timeframe 5m --fee 1.755e-05 --timerange $w "${sets[@]}" \
     --note "SPRAVY vstup: $mode, vstup ${x} min po sprave (noha T->T+$x), 1 kontrakt, MGC 5m $w" >/dev/null 2>&1 || echo "CHYBA $mode $x $w"
  done
 done
done
echo HOTOVO
