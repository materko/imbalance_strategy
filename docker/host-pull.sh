#!/bin/sh
# git pull klonu, ktorý mountuje Docker agent alebo webapp (TRADEBOT_HUB_PULL=host, docs/HUB.md).
# Púšťa ho systemd hostiteľa: časovač pravidelne a path jednotka hneď, keď kontajner zapíše pokyn
# ⟳ z karty Hub do tester/hub_pull_request. Výsledok ide do tester/hub_pull_result: 1. riadok =
# pokyn, ktorý bol v súbore pred pullom, 2. = návratový kód (0 len keď HEAD == origin/main),
# ďalej výstup bez progress riadkov — agent ho prečíta a nahlási hubu. Mená súborov sú
# v tradebot/core/paths.py (HUB_PULL_REQUEST/RESULT/CONFLICTS).
#
#   host-pull.sh [koreň klonu]      (bez argumentu klon, v ktorom skript leží)
#
# Prečo nie `git pull --rebase --autostash` (srvnas 20.–23. 11. 2026): pull robí fast-forward cez
# `merge --ff-only`, ktorý aj s -q zapne 1 s časovač SIGALRM progress výpisu. Na FUSE (JuiceFS) signál
# preruší mkdir/open s EINTR, git to nezopakuje a checkout tisícok behov spadne v polovici: index na
# starom HEAD, strom napoly nový, nové súbory netrackované (každý ďalší pull padá na „untracked
# working tree files would be overwritten") a osirelý MERGE_AUTOSTASH. Preto:
#   - fetch a aktualizácia zvlášť, len príkazmi bez časovača (`checkout --no-progress`, `reset -q`;
#     overené cez strace na setitimer);
#   - lokálne zmeny trackovaných súborov výslovne do stashu a späť, pri konflikte stash ostáva;
#   - netrackované súbory, ktoré by kolidovali s origin/main: bajtovo zhodné (behy, ktoré tento stroj
#     už commitol) zmaže, odlišné presunie do tester/hub_pull_conflicts/<dátum>/;
#   - zvyšky po páde (starý zámok, MERGE_AUTOSTASH → stash, AUTO_MERGE, rozbitý rebase) uprace;
#   - keď aktualizácia aj tak zlyhá a lokálne commity nie sú, obnoví sa `reset --hard origin/main`.
#
# Všetko je vo funkciách a volanie s exit je na jednom riadku: aktualizácia prepíše aj tento súbor
# a sh by inak dočítal už nový.

ZAMOK_MIN=10    # zámok gitu starší ako toľko minút je po páde; mladší = práve beží iný git
POKUSY=5        # obnova `reset --hard`: koľkokrát skúsiť (aj reset môže na FUSE dostať EINTR)
TAB=$(printf '\t')

g() { git -c core.quotepath=off -c advice.detachedHead=false "$@"; }

opakuj() {      # príkaz skúsi POKUSY-krát so sleep 2
    _pokus=1
    while ! "$@"; do
        [ "$_pokus" -ge "$POKUSY" ] && return 1
        _pokus=$((_pokus + 1))
        sleep 2
    done
}

# Stash podľa oid (nie podľa poradia — iný pop mohol zlyhať a ostať navrchu). Pri konflikte
# stash ostáva a pracovný strom ide späť na HEAD: zmeny sú celé v stashi a agent nesmie bežať
# nad súbormi so značkami konfliktu.
vrat_stash() {
    _n=0
    while _s=$(g rev-parse -q --verify "stash@{$_n}" 2>/dev/null); do
        if [ "$_s" = "$1" ]; then
            g stash pop -q "stash@{$_n}" && return 0
            g reset -q --hard HEAD
            echo "POZOR: lokálne zmeny sa po aktualizácii nedali vrátiť (konflikt) — ostávajú v stash@{$_n}" \
                 "($(g log -1 --format=%s "$1")); pozri git stash show -p stash@{$_n}"
            return 1
        fi
        _n=$((_n + 1))
    done
    echo "POZOR: stash $1 sa nenašiel"
    return 1
}

# Netrackované súbory, ktoré sú v cieli ($1) ako blob: zhodné zmaže, odlišné presunie do zálohy ($2).
uprac_kolizie() {
    _tmp=$(mktemp -d) || return 1
    g ls-files --others --exclude-standard > "$_tmp/netrack" || { rm -rf "$_tmp"; return 1; }
    if [ ! -s "$_tmp/netrack" ]; then rm -rf "$_tmp"; return 0; fi
    g ls-tree -r "$1" > "$_tmp/strom" || { rm -rf "$_tmp"; return 1; }
    # ls-tree: "<mode> blob <oid>\t<cesta>"; cesty v úvodzovkách (git ich tak píše pri \t, \n, ", \) vynechá
    awk -F "$TAB" 'NR == FNR { u[$0] = 1; next }
                   ($2 in u) && $2 !~ /^"/ { split($1, a, " "); if (a[2] == "blob") print a[3] "\t" $2 }' \
        "$_tmp/netrack" "$_tmp/strom" > "$_tmp/kolizie"
    if [ ! -s "$_tmp/kolizie" ]; then rm -rf "$_tmp"; return 0; fi
    cut -f2 "$_tmp/kolizie" | g hash-object --stdin-paths > "$_tmp/hashe" || { rm -rf "$_tmp"; return 1; }
    if [ "$(wc -l < "$_tmp/kolizie")" -ne "$(wc -l < "$_tmp/hashe")" ]; then
        echo "hash-object nevrátil hash pre každý kolidujúci súbor"; rm -rf "$_tmp"; return 1
    fi
    : > "$_tmp/rovnake"; : > "$_tmp/ine"
    paste "$_tmp/kolizie" "$_tmp/hashe" | awk -F "$TAB" -v r="$_tmp/rovnake" -v i="$_tmp/ine" \
        '$1 == $3 { print $2 > r; next } { print $2 > i }'
    _chyba=0
    if [ -s "$_tmp/rovnake" ]; then
        tr '\n' '\0' < "$_tmp/rovnake" | xargs -0 rm -f -- || _chyba=1
        echo "zmazané netrackované súbory zhodné s origin/main: $(wc -l < "$_tmp/rovnake")"
    fi
    if [ -s "$_tmp/ine" ]; then
        echo "POZOR: netrackované súbory odlišné od origin/main ($(wc -l < "$_tmp/ine")) presunuté do ${2#"$PWD"/}:"
        head -n 20 "$_tmp/ine" | sed 's/^/  /'
        while IFS= read -r _c; do
            mkdir -p "$2/$(dirname "$_c")" && mv -f "$_c" "$2/$_c" || { echo "nepodarilo sa presunúť $_c"; _chyba=1; }
        done < "$_tmp/ine"
    fi
    rm -rf "$_tmp"
    return "$_chyba"
}

aktualizuj() {
    repo=$1
    cd "$repo" || return 1
    gd=$(g rev-parse --absolute-git-dir) || return 1
    datum=$(date +%Y%m%d-%H%M%S)
    vratit=""       # oid stashov na vrátenie po aktualizácii, najnovší prvý
    chyba=0
    if ! g config user.email > /dev/null 2>&1; then     # stash a rebase sú commity, chcú identitu
        GIT_AUTHOR_NAME=host-pull GIT_AUTHOR_EMAIL=host-pull@localhost
        GIT_COMMITTER_NAME=host-pull GIT_COMMITTER_EMAIL=host-pull@localhost
        export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
    fi

    # -- zvyšky po predošlom páde --------------------------------------------------------------- #
    _cerstve=$(find "$gd" -path "$gd/objects" -prune -o -name '*.lock' -type f ! -mmin +"$ZAMOK_MIN" -print 2>/dev/null)
    if [ -n "$_cerstve" ]; then
        echo "beží iný git (zámok mladší ako $ZAMOK_MIN min: ${_cerstve#"$gd"/}) — skúsim nabudúce"
        return 1
    fi
    for _z in $(find "$gd" -path "$gd/objects" -prune -o -name '*.lock' -type f -print 2>/dev/null); do
        rm -f "$_z" && echo "zmazaný starý zámok ${_z#"$gd"/}"
    done
    if [ -d "$gd/rebase-merge" ] || [ -d "$gd/rebase-apply" ]; then
        _pred=$(g rev-parse -q --verify refs/stash 2>/dev/null)
        g rebase --quit && echo "ukončený rozbitý rebase (git rebase --quit)"
        _po=$(g rev-parse -q --verify refs/stash 2>/dev/null)
        [ -n "$_po" ] && [ "$_po" != "$_pred" ] && vratit="$_po $vratit"
    fi
    if [ -f "$gd/MERGE_AUTOSTASH" ]; then
        _oid=$(cat "$gd/MERGE_AUTOSTASH")
        if g cat-file -e "$_oid^{commit}" 2> /dev/null &&
           g stash store -q -m "host-pull $datum: osirelý MERGE_AUTOSTASH" "$_oid"; then
            rm -f "$gd/MERGE_AUTOSTASH"
            vratit="$_oid $vratit"
            echo "osirelý MERGE_AUTOSTASH uložený do stashu ($_oid)"
        else
            mv -f "$gd/MERGE_AUTOSTASH" "$gd/MERGE_AUTOSTASH.$datum" &&
                echo "POZOR: MERGE_AUTOSTASH ukazuje na neplatný commit — odložený do .git/MERGE_AUTOSTASH.$datum"
        fi
    fi
    [ -f "$gd/AUTO_MERGE" ] && rm -f "$gd/AUTO_MERGE" && echo "zmazaný osirelý AUTO_MERGE"

    # -- fetch ---------------------------------------------------------------------------------- #
    if ! opakuj g fetch -q --no-progress origin "+refs/heads/main:refs/remotes/origin/main"; then
        echo "git fetch zlyhal"
        chyba=1
    fi
    ciel=$(g rev-parse -q --verify "refs/remotes/origin/main^{commit}") || { echo "chýba origin/main"; return 1; }

    # -- aktualizácia --------------------------------------------------------------------------- #
    if [ "$(g rev-parse -q --verify 'HEAD^{commit}')" = "$ciel" ]; then
        echo "už aktuálne"
    else
        uprac_kolizie "$ciel" "$konflikty/$datum" || chyba=1
        g update-index -q --refresh > /dev/null 2>&1
        if ! g diff-index --quiet HEAD --; then
            if g stash push -q -m "host-pull $datum: lokálne zmeny pred aktualizáciou"; then
                vratit="$(g rev-parse -q --verify refs/stash) $vratit"
                echo "lokálne zmeny trackovaných súborov odložené do stashu"
            else
                echo "git stash push zlyhal — neaktualizujem"
                chyba=1
            fi
        fi
        if ! g diff-index --quiet HEAD --; then
            :   # lokálne zmeny sa nepodarilo odložiť — nič neprepisovať
        elif g merge-base --is-ancestor HEAD "$ciel"; then
            _vetva=$(g symbolic-ref -q --short HEAD)
            if [ -n "$_vetva" ]; then
                g checkout -q --no-progress -B "$_vetva" "$ciel"     # oid, nie ref: upstream sa nemení
            else
                g checkout -q --no-progress --detach "$ciel"
            fi || {
                echo "aktualizácia zlyhala — obnova: git reset --hard origin/main"
                if opakuj g reset -q --hard "$ciel"; then echo "obnova prešla"; else echo "obnova zlyhala"; chyba=1; fi
            }
        elif g merge-base --is-ancestor "$ciel" HEAD; then
            echo "HEAD má $(g rev-list --count "$ciel..HEAD") lokálnych commitov nad origin/main (nepushnuté) — nesťahujem nič"
        else
            echo "lokálne commity ($(g rev-list --count "$ciel..HEAD")) — rebase na origin/main"
            g rebase -q --no-autostash "$ciel" || {
                g rebase --abort
                echo "rebase zlyhal — ostáva pôvodný stav, lokálne commity treba vyriešiť ručne"
            }
        fi
    fi

    for _oid in $vratit; do
        vrat_stash "$_oid" || chyba=1
    done
    [ -f "$gd/MERGE_HEAD" ] || rm -f "$gd/AUTO_MERGE"     # stash pop ho (git 2.45) nechá aj po čistom merge
    _odlozene=$(g stash list | grep -c 'host-pull')
    [ "$_odlozene" -gt 0 ] && echo "v stashi ostáva $_odlozene odložených zmien z host-pull (git stash list)"

    _head=$(g rev-parse -q --verify 'HEAD^{commit}')
    if [ "$_head" != "$ciel" ]; then
        echo "HEAD $(g rev-parse --short HEAD) ≠ origin/main $(g rev-parse --short "$ciel")"
        return 1
    fi
    echo "HEAD = origin/main $(g rev-parse --short "$ciel")"
    [ "$chyba" -eq 0 ] || return 3
    return 0
}

main() {
    repo=$(cd "${1:-$(dirname "$0")/..}" && pwd) || return 1
    req="$repo/tester/hub_pull_request"
    out="$repo/tester/hub_pull_result"
    konflikty="$repo/tester/hub_pull_conflicts"
    hotovy="-"
    # pokyn, ktorý prišiel počas pullu (path jednotka sa vtedy znova nespustí), vybaví ďalšie kolo
    while pokyn=$(cat "$req" 2>/dev/null); [ "$pokyn" != "$hotovy" ]; do
        vystup=$( (aktualizuj "$repo") 2>&1 )
        kod=$?
        # bez \r a progress riadkov („Updating files:  45% (123/456)"), nanajvýš 200 riadkov
        vystup=$(printf '%s\n' "$vystup" | tr '\r' '\n' | grep -v -E '[0-9]{1,3}% \([0-9]+/[0-9]+\)' |
                 grep -v '^[[:space:]]*$' | tail -n 200)
        printf '%s\n%s\n%s\n' "$pokyn" "$kod" "$vystup" > "$out.tmp" && mv -f "$out.tmp" "$out"
        [ -n "$vystup" ] && printf '%s\n' "$vystup"
        hotovy=$pokyn
        posledny=$kod
    done
    return "${posledny:-0}"
}

main "$@"; exit $?
