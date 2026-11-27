#!/bin/sh
cd /Users/martin/IBS || exit 1
for k in noabtc dailyopenbtc onbiasorbbtc flashorbbtc silverbulletbtc rangebtc tmrbtc sweepengulfbtc; do
  P=$(ls tradebot/strategies/$k/configs/*.json | head -1); TF=$(python3 -c "import json;print(json.load(open('$P'))['_timeframe'])")
  nice .venv/bin/python -m tester.webapp.cli checkup --strategy $k --profile "$P" --pair BTC/USDT:USDT --engine multicharts \
    --timeframe $TF --fee 2e-4 --wallet 60000 --note "Základná analytika $k (BTC východisko, maker 0,02 %)" > .nightsearch/btc_screen/checkup_$k.log 2>&1
  echo "$k $(ls -la tradebot/strategies/$k/docs/ANALYTIKA.md 2>/dev/null | awk '{print $6,$7,$8}')"
done
echo hotovo
