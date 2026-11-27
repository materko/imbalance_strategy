#!/bin/sh
# Používateľ 18. 10. 2026: 19. 10. o 22:00 pokračovať v Silver Bullet tam, kde sa skončilo (gl_state.json),
# v utorok 20. 10. ráno po nahratí výsledkov testy zastaviť (gl_stop_after_morning).
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-19" ] || exit 0
printf '# Stratégie v testovaní podľa smernice (zmena = reštart glsearch netreba, číta sa každé kolo)\nsilverbullet\n' > gl_active.txt
touch gl_stop_after_morning
for p in $(pgrep -f "glsearch.py|glhyper.py"); do
  for c in $(pgrep -P "$p"); do kill -CONT "$c"; kill -TERM "$c"; done
  kill -CONT "$p"; kill -TERM "$p"
done
rm -f gl_paused
echo "$(date) Silver Bullet znova spustené (pokračuje z gl_state), v utorok ráno stop" >> dash/morning.log
launchctl unload ~/Library/LaunchAgents/sk.tradebot.sbresume.plist; rm -f ~/Library/LaunchAgents/sk.tradebot.sbresume.plist
