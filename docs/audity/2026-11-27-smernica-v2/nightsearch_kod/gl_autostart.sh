#!/bin/sh
# Po reštarte Macu znova spustí slučky testov (22. 10. 2026 Mac mini reštartoval a testy stáli celú noc).
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH   # Mono (C# jadro) pre webapp aj testy — 16. 11. 2026 bez neho padali behy C#
export TRADEBOT_NATIVE_WORKERS=3   # C# procesy webapp (hyperopt TKS ich bral 10 a preťažil Mac mini) — 17. 11. 2026
# Nič nespustí, keď sú testy pozastavené (gl_paused) alebo už bežia.
cd /Users/martin/IBS/.nightsearch || exit 1
sleep 60
# webapp (26. 10. 2026: po reštarte Macu nebežala a ranná kontrola aj hodinová kontrola ju potrebujú)
curl -s -o /dev/null -m 10 http://127.0.0.1:8765/api/meta || (cd .. && NO_BROWSER=1 nohup ./webapp.sh > /tmp/webapp.log 2>&1 &)
[ -f gl_paused ] && exit 0
if [ ! -f gl_hub_only ]; then   # gl_hub_only: počíta len hub (používateľ 8. 11. 2026)
  pgrep -f glrun.sh >/dev/null || nohup caffeinate -i ./glrun.sh >/dev/null 2>&1 &
  pgrep -f glhyperrun.sh >/dev/null || nohup caffeinate -i ./glhyperrun.sh >/dev/null 2>&1 &
fi
pgrep -f glhubrun.sh >/dev/null || nohup caffeinate -i ./glhubrun.sh >/dev/null 2>&1 &
echo "$(date) autostart testov po štarte Macu" >> dash/morning.log
