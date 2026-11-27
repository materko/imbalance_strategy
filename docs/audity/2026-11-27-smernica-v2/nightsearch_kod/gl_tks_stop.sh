#!/bin/sh
# Používateľ 18. 10. 2026: TKS testovať do pondelka 19. 10. 21:30, potom pauza; o 22:00 sa vráti Silver Bullet (gl_sb_resume.sh).
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-19" ] || exit 0
./glpause.sh stop
echo "$(date) TKS zastavené (do 19. 10. 21:30)" >> dash/morning.log
launchctl unload ~/Library/LaunchAgents/sk.tradebot.tksstop.plist; rm -f ~/Library/LaunchAgents/sk.tradebot.tksstop.plist
