#!/bin/sh
# 16. 11. 2026 používateľ: profily vo webapp musia sedieť so stránkou výsledkov — prepočet karty Výkon so starými behmi
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
cd /Users/martin/IBS || exit 1
cp .nightsearch/vykon_oprava.txt .nightsearch/webvyber_checkup.txt
sh .nightsearch/glwebcheckup.sh > .nightsearch/vykon_oprava.log 2>&1
cd .nightsearch && for k in $(awk '{print $1}' vykon_oprava.txt | sort -u); do ../.venv/bin/python /private/tmp/claude-501/-Users-martin-IBS/b71b5de5-7d7c-4c94-9a99-dbafbd991bc0/scratchpad/chkall_sp.py "$k" 2>&1 | grep -E "^OK|^ZLE|^CHYBA"; done > chk2.log
echo KONIEC >> chk2.log
launchctl remove sk.tradebot.vykonoprava
