#!/bin/sh
# git pull klonu, ktorý mountuje Docker agent alebo webapp (TRADEBOT_HUB_PULL=host, docs/HUB.md).
# Púšťa ho systemd hostiteľa: časovač pravidelne a path jednotka hneď, keď kontajner zapíše pokyn
# ⟳ z karty Hub do tester/hub_pull_request. Výsledok ide do tester/hub_pull_result: 1. riadok =
# pokyn, ktorý bol v súbore pred pullom, 2. = návratový kód git pull, ďalej jeho výstup — agent
# ho prečíta a nahlási hubu. Mená súborov sú v tradebot/core/paths.py (HUB_PULL_REQUEST/RESULT).
#
#   host-pull.sh [koreň klonu]      (bez argumentu klon, v ktorom skript leží)
#
# Celé je vo funkcii: pull môže prepísať aj tento súbor a sh by inak dočítal už nový.

main() {
    repo=${1:-$(cd "$(dirname "$0")/.." && pwd)}
    req="$repo/tester/hub_pull_request"
    out="$repo/tester/hub_pull_result"
    hotovy="-"
    # pokyn, ktorý prišiel počas pullu (path jednotka sa vtedy znova nespustí), vybaví ďalšie kolo
    while pokyn=$(cat "$req" 2>/dev/null); [ "$pokyn" != "$hotovy" ]; do
        vystup=$(git -C "$repo" pull -q --rebase --autostash origin main 2>&1)
        kod=$?
        printf '%s\n%s\n%s\n' "$pokyn" "$kod" "$vystup" > "$out.tmp" && mv -f "$out.tmp" "$out"
        [ -n "$vystup" ] && printf '%s\n' "$vystup"
        hotovy=$pokyn
        posledny=$kod
    done
    return "${posledny:-0}"
}

main "$@"
exit $?
