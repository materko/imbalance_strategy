#!/bin/sh
# Jednorazové zastavenie testov (používateľ 17. 10. 2026: Silver Bullet „do zajtra rána do piatej“ (18. 10.)) — po vykonaní sa launchd úloha odstráni.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-19" ] || exit 0
./glpause.sh stop
echo "$(date) testy zastavené (Silver Bullet do 19. 10. 5:00)" >> dash/morning.log
launchctl unload ~/Library/LaunchAgents/sk.tradebot.stopmon.plist; rm -f ~/Library/LaunchAgents/sk.tradebot.stopmon.plist
