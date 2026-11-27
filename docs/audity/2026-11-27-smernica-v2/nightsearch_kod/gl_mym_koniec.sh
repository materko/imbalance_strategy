#!/bin/sh
# Používateľ 12. 11. 2026: po dobehnutí testov MYM (ne 15. 11. 18:00) to isté ako pri NOA MGC / MTK ORB — výsledky na stránku,
# výsledky MYM len na stránku výsledkov (na webapp vyberie používateľ), analytika, push. Posudky AI dopíše Claude v ďalšej relácii.
# Používateľ 13. 11. 2026: potom hneď testy BTC (8 kópií na BTCUSDT.P) do ne 22. 11. 18:00.
cd /Users/martin/IBS/.nightsearch || exit 1
[ "$(date +%Y-%m-%d)" = "2026-11-15" ] || exit 0
{
  echo "=== $(date '+%d. %m. %H:%M') MYM: koniec testov, nahrávanie"
  [ -f gl_paused ] || sh glpause.sh stop
  /bin/sh ./glmorning.sh
  (cd .. && .venv/bin/python -m tester.webapp.cli push)
  echo "=== $(date '+%d. %m. %H:%M') BTC: prepínam testy na BTCUSDT.P (používateľ 13. 11. 2026)"
  cp gl_active.txt gl_active.txt.bak_mym
  printf '%s\n' noabtc dailyopenbtc onbiasorbbtc flashorbbtc silverbulletbtc rangebtc tmrbtc sweepengulfbtc > gl_active.txt
  echo 2026-11-22T18:00 > gl_local_stop_at.txt
  echo 2026-11-22T18:00 > gl_stop_at.txt
  for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py"); do
    for c in $(pgrep -P "$p"); do kill -CONT "$c"; kill "$c"; done
    kill -CONT "$p"; kill "$p"
  done
  ../.venv/bin/python gl_btc_seed.py
  rm -f gl_planned.txt gl_paused gl_hub_off gl_hub_only
  sleep 40
  sh gl_watchdog.sh
  sleep 120
  pgrep -fl "glsearch.py|glhyper.py|glhub.py"
  # Používateľ 14. 11. 2026: po štarte testov BTC nahrať stránku výsledkov so záložkou BTC — hneď a o hodinu s prvými výsledkami
  echo "=== $(date '+%d. %m. %H:%M') stránka výsledkov so záložkou BTC"
  ../.venv/bin/python gldash.py && ./glcopy.sh
  sleep 3600
  echo "=== $(date '+%d. %m. %H:%M') stránka výsledkov — prvé výsledky BTC"
  ../.venv/bin/python gldash.py && ./glcopy.sh
  echo "hotovo $(date '+%H:%M')"
} >> gl_mym_koniec.log 2>&1
launchctl unload "$HOME/Library/LaunchAgents/sk.tradebot.mymkoniec.plist"
