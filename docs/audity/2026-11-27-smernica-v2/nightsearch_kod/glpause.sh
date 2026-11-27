#!/bin/sh
# Pozastavenie testov (hľadanie + hyperopt aj s pracovnými procesmi) — okamžite, SIGSTOP / SIGCONT.
#   glpause.sh stop   — používateľ: „pozastav testovanie“ (zapamätá sa v gl_paused, platí aj cez ranné nahrávanie)
#   glpause.sh cont   — používateľ: „zapni testovanie“ (zruší gl_paused)
#   glpause.sh mstop  — ranné nahrávanie: pozastaví len na čas nahrávania
#   glpause.sh mcont  — ranné nahrávanie: rozbehne, LEN ak používateľ testy nepozastavil
cd /Users/martin/IBS/.nightsearch
case "$1" in
  stop)  touch gl_paused; SIG=STOP ;;
  cont)  rm -f gl_paused; SIG=CONT ;;
  mstop) SIG=STOP ;;
  mcont) [ -f gl_paused ] && exit 0; SIG=CONT ;;
  *) echo "použitie: glpause.sh stop|cont|mstop|mcont"; exit 1 ;;
esac
for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py|glrr.py"); do
  for c in $(pgrep -P "$p"); do kill -$SIG "$c" 2>/dev/null; done
  kill -$SIG "$p" 2>/dev/null
done
