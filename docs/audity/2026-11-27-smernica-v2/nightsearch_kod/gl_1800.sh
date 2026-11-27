#!/bin/sh
# Používateľ 26. 10. 2026: SD ZÓNY EURUSD — prvé kolo výsledkov o 18:00 (to isté ako ranná obnova), potom klasicky ráno 6:00.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-26" ] || exit 0
echo "$(date) prvé kolo EURUSD o 18:00 — ranná obnova mimo poradia" >> dash/morning.log
rm -f ~/Library/LaunchAgents/sk.tradebot.eurusd1800.plist
/bin/sh ./glmorning.sh
