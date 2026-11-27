#!/bin/sh
# Používateľ 28. 10. 2026: M2 testovať do piatka 30. 10. 18:00 — vtedy nahrať výsledky a testy zastaviť (len tento raz).
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-30" ] || exit 0
echo "$(date) 30. 10. 18:00 — koniec testov M2: nahratie výsledkov a zastavenie" >> dash/morning.log
launchctl unload ~/Library/LaunchAgents/sk.tradebot.fri1800.plist 2>/dev/null
rm -f ~/Library/LaunchAgents/sk.tradebot.fri1800.plist
touch gl_stop_after_morning          # glmorning.sh: po nahratí testy zastaví natrvalo (gl_paused)
/bin/sh ./glmorning.sh
echo "$(date) testy M2 zastavené (gl_paused)" >> dash/morning.log
