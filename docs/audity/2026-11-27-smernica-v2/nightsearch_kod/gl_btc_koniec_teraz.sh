#!/bin/sh
# Používateľ 15. 11. 2026: po dobehnutí testov BTC (ne 22. 11. 18:00) výsledky BTC na stránku a push, potom hneď
# smernica EUR (7 kópií …eur na 6E) do ne 29. 11. 18:00. Na webapp nič automaticky — BTC aj EUR vyberieme s používateľom.
cd /Users/martin/IBS/.nightsearch || exit 1
# 21. 11. používateľ: BTC ukončiť hneď, EUR zapnúť dnes
{
  echo "=== $(date '+%d. %m. %H:%M') BTC: koniec testov, nahrávanie"
  [ -f gl_paused ] || sh glpause.sh stop
  /bin/sh ./glmorning.sh
  (cd .. && .venv/bin/python -m tester.webapp.cli push)
  echo "=== $(date '+%d. %m. %H:%M') EUR: prepínam testy na 6E (používateľ 15. 11. 2026)"
  cp gl_active.txt gl_active.txt.bak_btc
  printf '%s\n' asiasweepeur mtkzoneeur lliqeur silverbulleteur wpreur ibsentryeur sweepengulfeur ibret ibretmgc ibretmym > gl_active.txt   # 21. 11.: IB RETRACE beží ďalej
  echo 2026-11-29T05:45 > gl_local_stop_at.txt   # 21. 11. používateľ: v ne 29. 11. ráno 6:00 testy stop, finálne výsledky
  echo 2026-11-29T05:45 > gl_stop_at.txt
  for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py"); do
    for c in $(pgrep -P "$p"); do kill -CONT "$c"; kill "$c"; done
    kill -CONT "$p"; kill "$p"
  done
  ../.venv/bin/python gl_btc_seed.py     # východiská pre kľúče z gl_active (všeobecné, nielen BTC)
  rm -f gl_planned.txt gl_paused gl_hub_off gl_hub_only
  sleep 40
  sh gl_watchdog.sh
  sleep 120
  pgrep -fl "glsearch.py|glhyper.py|glhub.py"
  echo "=== $(date '+%d. %m. %H:%M') stránka výsledkov so záložkou EURUSD"
  ../.venv/bin/python gldash.py && ./glcopy.sh
  sleep 3600
  echo "=== $(date '+%d. %m. %H:%M') stránka výsledkov — prvé výsledky EUR"
  ../.venv/bin/python gldash.py && ./glcopy.sh
  echo "hotovo $(date '+%H:%M')"
} >> gl_btc_koniec.log 2>&1
launchctl unload "$HOME/Library/LaunchAgents/sk.tradebot.btckoniec.plist"
