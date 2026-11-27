#!/bin/sh
# Každú hodinu (launchd sk.tradebot.watchdog, používateľ 24. 10. 2026: „každú hodinu skontroluj, či bežia testy,
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH   # Mono (C# jadro) pre webapp aj testy — 16. 11. 2026 bez neho padali behy C#
export TRADEBOT_NATIVE_WORKERS=3   # C# procesy webapp — 17. 11. 2026
# keď niečo padne, vždy ich obnov“). Bez AI — len kontrola procesov a obnova:
#   * webapp na 127.0.0.1:8765 odpovedá, inak sa spustí znova,
#   * slučky testov (glrun / glhyperrun / glhubrun) bežia, inak sa spustia (nie pri gl_paused),
#   * zastavené procesy (SIGSTOP) mimo rannej obnovy sa pustia ďalej,
#   * hľadanie bez zápisu do logu viac ako 90 minút sa reštartuje (slučka ho spustí znova, stav ostáva v gl_state.json),
#   * siroty multiprocessing (rodič = 1) po páde sa ukončia.
cd /Users/martin/IBS/.nightsearch || exit 1
LOG=dash/watchdog.log
log() { echo "$(date '+%d. %m. %H:%M') $*" >> "$LOG"; }
pgrep -f glmorning.sh >/dev/null && { log "ranná obnova beží — kontrola preskočená"; exit 0; }

# webapp
if ! curl -s -o /dev/null -m 10 http://127.0.0.1:8765/api/meta; then
  (cd .. && NO_BROWSER=1 nohup ./webapp.sh > /tmp/webapp.log 2>&1 &)
  log "webapp neodpovedala — spustená znova"
fi

# glwr (používateľ 10. 11. 2026: vyšší winrate pri RR 1 → 0,75 → 0,5 na hube) — beží, kým nie je wr_stop
if [ ! -f wr_stop ] && ! pgrep -f glwrrun.sh >/dev/null; then
  nohup caffeinate -i ./glwrrun.sh >/dev/null 2>&1 &
  log "glwrrun.sh nebežala — spustená"
fi

# koniec lokálnych testov v termíne (používateľ 10. 11. 2026: MTK ZONE na Mac mini do 11. 11. 18:00) — gl_local_stop_at.txt
if [ -f gl_local_stop_at.txt ] && [ ! -f gl_paused ] && [ "$(date '+%Y-%m-%dT%H:%M')" \> "$(cat gl_local_stop_at.txt)" ]; then
  ./glpause.sh stop
  log "termín $(cat gl_local_stop_at.txt) — testy zastavené (gl_paused)"
fi
[ -f gl_paused ] && { log "testy pozastavené (gl_paused) — nič nespúšťam"; exit 0; }

# gl_hub_only (používateľ 8. 11. 2026): počíta len hub, Mac mini nie — beží len slučka glhub
LOOPS="glrun.sh glhyperrun.sh glhubrun.sh"; [ -f gl_hub_only ] && LOOPS=glhubrun.sh
for loop in $LOOPS; do
  if ! pgrep -f "$loop" >/dev/null; then
    nohup caffeinate -i ./$loop >/dev/null 2>&1 &
    log "$loop nebežala — spustená"
  fi
done

for p in $(pgrep -f 'glsearch.py|glhyper.py|glhub.py'); do
  if [ "$(ps -o stat= -p $p | cut -c1)" = "T" ]; then
    kill -CONT $p; pkill -CONT -P $p
    log "proces $p bol zastavený mimo rannej obnovy — pustený ďalej"
  fi
done

if [ -f glsearch.log ] && [ -n "$(find glsearch.log -mmin +90)" ]; then
  for p in $(pgrep -f 'Python glsearch.py'); do pkill -P $p; kill $p; done
  log "hľadanie 90 min bez zápisu do logu — reštartované"
fi

n=0
for p in $(ps -A -o pid=,ppid=,command= | awk '$2==1 && /multiprocessing/ && /glsearch|glhyper|spawn_main|resource_tracker/ {print $1}'); do
  kill $p 2>/dev/null && n=$((n + 1))
done
[ $n -gt 0 ] && log "ukončených sirôt multiprocessing: $n"
log "ok — slučky $(for l in glrun.sh glhyperrun.sh glhubrun.sh; do pgrep -f "$l" >/dev/null && echo $l; done | wc -l | tr -d ' ') / 3, záťaž $(uptime | sed 's/.*averages: //')"
