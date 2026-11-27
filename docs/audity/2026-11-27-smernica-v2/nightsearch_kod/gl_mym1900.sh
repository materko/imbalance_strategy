#!/bin/sh
# Používateľ 12. 11. 2026: MYM (Micro Dow) — ladenie odznova + smernica (príkaz z MacBooku, iCloud MACMINI-PRIKAZY),
# spustiť o 19:00 po dobehnutí NOA ES / NOA MGC / MTK ORB (koniec 18:00, výsledky 18:30). Testy MYM najneskôr do nedele 15. 11. 18:00.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-11-12" ] || exit 0
{
  echo "=== $(date '+%d. %m. %H:%M') MYM: prepínam testy na Micro Dow"
  # počkať, kým dobehne nahrávanie z 18:30
  i=0; while pgrep -f glmorning.sh >/dev/null && [ $i -lt 180 ]; do sleep 20; i=$((i + 1)); done
  cp gl_active.txt gl_active.txt.bak_noa_mtkorb
  printf '%s\n' ibsentrymym noamym wprmym sweepengulfmym tmrmym lliqmym sigmamym nocponmym > gl_active.txt
  echo 2026-11-15T18:00 > gl_local_stop_at.txt
  echo 2026-11-15T18:00 > gl_stop_at.txt
  # staré procesy (pozastavené od 18:00) ukončiť — slučky ich spustia znova s novým zoznamom
  for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py"); do
    for c in $(pgrep -P "$p"); do kill -CONT "$c"; kill "$c"; done
    kill -CONT "$p"; kill "$p"
  done
  rm -f gl_paused gl_hub_off gl_hub_only
  sleep 40
  sh gl_watchdog.sh
  sleep 120
  pgrep -fl "glsearch.py|glhyper.py|glhub.py"
  tail -5 glhub.log
  echo "hotovo $(date '+%H:%M')"
} >> gl_mym1900.log 2>&1
launchctl unload "$HOME/Library/LaunchAgents/sk.tradebot.mym1900.plist"
