#!/bin/sh
# Ranný pull webapp o 5:30 (používateľ 31. 10. 2026, týždeň do 8. 11.): pull, reštart webapp, overenie stratégií v /api/meta.
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH   # Mono (C# jadro) pre webapp aj testy — 16. 11. 2026 bez neho padali behy C#
export TRADEBOT_NATIVE_WORKERS=3   # C# procesy webapp — 17. 11. 2026
cd /Users/martin/IBS || exit 1
LOG=/Users/martin/IBS/.nightsearch/gl_pull0530.log
{
  echo "=== $(date '+%d. %m. %H:%M') pull"
  .venv/bin/python -m tester.webapp.cli pull 2>&1 | tail -5
  pkill -f "tester.webapp$"; sleep 3
  NO_BROWSER=1 nohup ./webapp.sh >/dev/null 2>&1 &
  for i in $(seq 1 60); do curl -s -o /dev/null localhost:8765/api/meta && break; sleep 2; done
  .venv/bin/python - <<'PY'
import json, urllib.request
from tradebot.strategies import STRATEGIES
m = json.load(urllib.request.urlopen("http://localhost:8765/api/meta"))
s = json.dumps(m)
missing = [k for k in STRATEGIES if f'"{k}"' not in s]
print("webapp beží; chýba v /api/meta:", missing or "nič")
PY
} >> "$LOG" 2>&1
