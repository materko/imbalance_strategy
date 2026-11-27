#!/bin/sh
# Používateľ 12. 11. 2026: výsledky bežiacich testov (NOA ES, NOA MGC, MTK ORB; koniec 18:00) nahrať aj dnes o 18:30 — to isté ako ranná obnova.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-11-12" ] || exit 0
echo "$(date) NOA ES / NOA MGC / MTK ORB — nahrávanie o 18:30 mimo poradia" >> dash/morning.log
/bin/sh ./glmorning.sh
launchctl unload "$HOME/Library/LaunchAgents/sk.tradebot.r1830.plist"
