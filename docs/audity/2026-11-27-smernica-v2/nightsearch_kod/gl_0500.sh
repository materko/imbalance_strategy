#!/bin/sh
# Používateľ 26. 10. 2026: zajtra (27. 10.) nahrať výsledky už o 5:00 a potom testy zastaviť (len tento raz).
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-10-27" ] || exit 0
echo "$(date) 27. 10. 5:00 — nahratie výsledkov a zastavenie testov" >> dash/morning.log
rm -f ~/Library/LaunchAgents/sk.tradebot.stop0500.plist
touch gl_stop_after_morning          # glmorning.sh: po nahratí testy zastaví natrvalo (gl_paused)
/bin/sh ./glmorning.sh
# Pred odstávkou prúdu (27. 10. od 6:00) testy po nahratí úplne ukončiť — slučky aj procesy; stav ostáva v *_state.json,
# gl_paused zabráni autoštartu po zapnutí Macu.
for loop in glrun.sh glhyperrun.sh glhubrun.sh; do pkill -f "$loop"; done
for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py|glrr.py"); do pkill -CONT -P $p; kill -CONT $p; pkill -P $p; kill $p; done
echo "$(date) testy ukončené pred odstávkou (gl_paused ostáva)" >> dash/morning.log
