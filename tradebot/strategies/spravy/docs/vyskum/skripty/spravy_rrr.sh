#!/bin/zsh
# SPRÁVY 2.0: RRR po pravidlách — každé pravidlo samostatne, 5 variantov cieľa/stopu, 5 okien
cd /Users/martin/document/IBS
typeset -A U; U[1]=FOMC; U[3]=CPI; U[4]=PPI; U[5]=PCE; U[6]=JOLTS
for n in 1 3 4 5 6; do
 OFF=(--set useFOMC=false --set useCPI=false --set usePPI=false --set usePCE=false --set useJOLTS=false --set use${U[$n]}=true)
 for v in "rr0_stopdnes:r${n}RR=0" "rr2_stopdnes:r${n}RR=2" "rr1.5_stopza:r${n}RR=1.5 r${n}Stop=0" "rr2_stopza:r${n}RR=2 r${n}Stop=0" "rr3_stopza:r${n}RR=3 r${n}Stop=0"; do
  name=${v%%:*}; sets=($OFF)
  for kv in ${(s: :)${v#*:}}; do sets+=(--set $kv); done
  for w in 20211001-20221001 20221001-20231001 20231001-20241001 20240904-20250904 20250904-20260904; do
   .venv/bin/python -m tester.webapp.cli run --strategy spravy --profile mgc_databento_5m --pair MGC/USD --engine multicharts \
     --timeframe 5m --fee 1.755e-05 --timerange $w "${sets[@]}" \
     --note "SPRAVY RRR: pravidlo $n ${U[$n]} $name, 1 kontrakt, MGC 5m $w" >/dev/null 2>&1 || echo "CHYBA $n $name $w"
  done
 done
done
echo HOTOVO
