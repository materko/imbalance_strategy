#!/bin/sh
# Štart hubu v kontajneri: kód si berie z vlastného plytkého klonu vo volume, nie
# z toho, čo je zapečené v image — inak by sa nemal ako aktualizovať (docs/HUB.md).
#
# Klon vzniká pri prvom štarte a ďalej si ho udržiava sám hub (`tester.hub.update`):
# fetch každých TRADEBOT_HUB_UPDATE minút a po zmene kódu reštart. Volume s klonom je
# jednorazový — nikto doň nepíše, takže sa vždy tvrdo prepíše na origin/<vetva>.
#
# Keď sa fetch nepodarí (výpadok siete), ide sa z toho, čo v klone je; keď klon nie je
# vôbec (prvý štart bez siete), hub nabehne z kódu v image a skúsi to pri ďalšom
# reštarte. Hub bez aktualizácie je lepší než hub, ktorý nebeží.
set -e

REPO_URL="${TRADEBOT_REPO_URL:-https://github.com/materko/imbalance_strategy.git}"
BRANCH="${TRADEBOT_HUB_BRANCH:-main}"
DIR="${TRADEBOT_HUB_CODE:-/srv/tradebot}"

git config --global --add safe.directory "$DIR" 2>/dev/null || true

# `git clone` do adresára, v ktorom je už namountovaný volume so stavom, neprejde —
# preto init + fetch + reset.
#
# Hub je len rozdeľovač práce: nepočíta, takže z repozitára nepotrebuje ani sviečky
# (`data_archive`, 2 GB), ani históriu behov (`tester/runs`, cez 6 GB). Preto plytký
# fetch (`--depth 1`), **partial clone** (`--filter=blob:none` — obsah súborov mimo
# výberu sa ani nesťahuje) a **sparse-checkout** so zoznamom z `tester/hub/sparse.py`
# (HUB_RULES). Z deviatich gigabajtov ostane pár megabajtov.
nastav_vyber() {
    git -C "$DIR" config remote.origin.promisor true
    git -C "$DIR" config remote.origin.partialclonefilter blob:none
    git -C "$DIR" sparse-checkout init --no-cone
    git -C "$DIR" sparse-checkout set --no-cone --stdin <<'PRAVIDLA'
/*
!/data_archive/**
!/csharp/**
!/tester/runs/**
!/tester/archive/**
!/tester/analytics/**
!/tester/sweeps/**
!/projekty/**
PRAVIDLA
}

stiahni() {
    if [ ! -e "$DIR/.git" ]; then
        echo "hub: klonujem $REPO_URL ($BRANCH) do $DIR" >&2
        mkdir -p "$DIR" \
            && git init -q "$DIR" \
            && git -C "$DIR" remote add origin "$REPO_URL" || return 1
    fi
    nastav_vyber || return 1
    git -C "$DIR" fetch -q --depth 1 --filter=blob:none origin "$BRANCH" \
        && git -C "$DIR" reset -q --hard FETCH_HEAD
}

if ! stiahni; then
    echo "hub: fetch z $REPO_URL zlyhal" >&2
fi

if [ -f "$DIR/tester/hub/__main__.py" ]; then
    cd "$DIR"
    export PYTHONPATH="$DIR"
    echo "hub: kod z $DIR ($(git -C "$DIR" rev-parse --short HEAD 2>/dev/null || echo '?'))" >&2
else
    echo "hub: klon nie je, idem z kodu v image (/app) — bez samoaktualizacie" >&2
    cd /app
    export PYTHONPATH=/app
fi

exec python -m tester.hub "$@"
