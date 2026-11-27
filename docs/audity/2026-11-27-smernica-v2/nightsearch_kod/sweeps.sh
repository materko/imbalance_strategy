#!/bin/bash
cd /Users/martin/IBS
PY=.venv/bin/python
P=tester/profiles/NOCNE2_B_stabilny_entry.json
C="--strategy ibsentry --profile $P --pair MNQ/USD --engine multicharts --timeframe 3m --timerange 20250904-20260904 --fee 0 --wallet 10000 --goal winrate"
SZ="fvgMinSize=2,4,6,8,10,15,20,30"
for tf in 5m 15m 30m 60m; do
  offs=""; for o in 5m 15m 30m 60m; do [ $o != $tf ] && offs="$offs --set fvgUse$o=false"; done
  $PY -m tester.webapp.cli sweep $C --set fvgUse$tf=true $offs --param $SZ --note "IBS Entry Zone: FVG len z $tf + SD zony, velkost 2-30 b." | tail -14
  $PY -m tester.webapp.cli sweep $C --set enableZoneDetection=false --set fvgUse$tf=true $offs --param $SZ --note "IBS Entry Zone: LEN FVG z $tf (SD zony vypnute), velkost 2-30 b." | tail -14
done
$PY -m tester.webapp.cli sweep $C --set fvgUse30m=true --set fvgUse60m=true --param "fvgMinSize=0.1@atr,0.25@atr,0.5@atr,0.75@atr,1@atr,1.5@atr,2@atr,3@atr" --note "IBS Entry Zone: FVG velkost v ATR, vsetky 4 TF" | tail -14
$PY -m tester.webapp.cli sweep $C --set enableZoneDetection=false --set fvgUse30m=true --set fvgUse60m=true --param "fvgMinSize=0.1@atr,0.25@atr,0.5@atr,0.75@atr,1@atr,1.5@atr,2@atr,3@atr" --note "IBS Entry Zone: LEN FVG (SD vypnute), velkost v ATR, vsetky 4 TF" | tail -14
$PY -m tester.webapp.cli sweep $C --set enableZoneDetection=false --set fvgUse30m=true --set fvgUse60m=true --set fvgMinSize=4 --param zoneValidHours=1,2,3,4,6,8,12,24 --note "IBS Entry Zone: LEN FVG, platnost zony 1-24 h" | tail -14
echo SWEEPS_DONE
