#!/bin/zsh
# SPRÁVY 2.0: každé pravidlo samostatne + celok + FOMC varianty, MGC 5m, 1 kontrakt, 5 okien
cd /Users/martin/document/IBS
OFF=(--set useFOMC=false --set useCPI=false --set usePPI=false --set usePCE=false --set useJOLTS=false)
typeset -A V
V[celok]=""
V[p1_FOMC_pred]="useFOMC=true r2Event="
V[p2_FOMC_tlacovka]="useFOMC=true r1Event="
V[p3_CPI]="useCPI=true"
V[p4_PPI]="usePPI=true"
V[p5_PCE]="usePCE=true"
V[p6_JOLTS]="useJOLTS=true"
V[FOMC_pred_do_1655]="r1Hold=175 r2Event="
for name in celok p1_FOMC_pred p2_FOMC_tlacovka p3_CPI p4_PPI p5_PCE p6_JOLTS FOMC_pred_do_1655; do
 sets=()
 if [[ $name == p* ]]; then sets=($OFF); fi
 for kv in ${(s: :)V[$name]}; do sets+=(--set $kv); done
 for w in 20211001-20221001 20221001-20231001 20231001-20241001 20240904-20250904 20250904-20260904; do
  .venv/bin/python -m tester.webapp.cli run --strategy spravy --profile mgc_databento_5m --pair MGC/USD --engine multicharts \
    --timeframe 5m --fee 1.755e-05 --timerange $w "${sets[@]}" \
    --note "SPRAVY 2.0 overenie: $name, 1 kontrakt, MGC 5m $w" >/dev/null 2>&1 || echo "CHYBA $name $w"
 done
done
echo HOTOVO
