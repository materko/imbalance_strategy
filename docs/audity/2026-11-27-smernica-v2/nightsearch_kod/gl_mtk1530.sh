#!/bin/sh
# MTK RANGE (va80): koniec testovania 8. 11. 2026 15:30 — zastaviť testy a nahrať výsledky ako ráno (stránka, webapp, iCloud).
cd /Users/martin/IBS/.nightsearch
{
  echo "=== $(date '+%d. %m. %H:%M') MTK RANGE: koniec testov, nahrávanie"
  sh glpause.sh stop
  sh glmorning.sh
  echo "hotovo $(date '+%H:%M')"
} >> gl_mtk1530.log 2>&1
launchctl unload "$HOME/Library/LaunchAgents/sk.tradebot.mtk1530.plist"
