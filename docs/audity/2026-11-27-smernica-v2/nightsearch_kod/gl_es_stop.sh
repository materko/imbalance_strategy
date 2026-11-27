#!/bin/sh
# Používateľ 22. 10. 2026: IBS EZ ES testovať do nedele 25. 10. 18:00, potom zastaviť.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-25" ] || exit 0
./glpause.sh stop; rm -f gl_stop_at.txt
echo "$(date) IBS EZ ES zastavené (do nedele 25. 10. 18:00)" >> dash/morning.log
launchctl unload ~/Library/LaunchAgents/sk.tradebot.esstop.plist; rm -f ~/Library/LaunchAgents/sk.tradebot.esstop.plist
