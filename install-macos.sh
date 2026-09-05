#!/bin/bash
# Inštalácia IBS Backtestera na macOS jedným príkazom:
#
#   curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash
#
# Čo spraví (a na čo sa spýta):
#   1. overí Xcode Command Line Tools (git) a Homebrew - ak chýbajú, ponúkne inštaláciu
#   2. cez Homebrew doinštaluje python@3.12 a ta-lib (Freqtrade ich potrebuje)
#   3. spýta sa, KAM repozitár klonovať a ako sa má priečinok volať
#   4. spýta sa na meno testera (ukladá sa ku každému behu vo webapp)
#   5. naklonuje repozitár (alebo aktualizuje existujúci), postaví .venv, zloží dáta
#   6. dá na Plochu "IBS Backtester.command" a ponúkne spustenie webapp
#
# Skript beží aj cez `curl | bash` - otázky číta z terminálu (/dev/tty), nie zo stdin.
# Je idempotentný: opakované spustenie len aktualizuje, čo treba.
# Písané pre systémový bash 3.2 (macOS), žiadne bash 4 konštrukcie.

set -euo pipefail

REPO_URL_HTTPS="https://github.com/materko/imbalance_strategy.git"
REPO_URL_SSH="git@github.com:materko/imbalance_strategy.git"
PY_FORMULA="python@3.12"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[32m✔\033[0m %s\n' "$*"; }
warn()  { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()   { printf '\n\033[31mCHYBA:\033[0m %s\n' "$*" >&2; exit 1; }

ask() {  # ask "otázka" "default" -> odpoveď v $REPLY (z /dev/tty, funguje aj cez curl | bash)
    local q="$1" def="${2:-}"
    if [ -n "$def" ]; then printf '%s [%s]: ' "$q" "$def" > /dev/tty; else printf '%s: ' "$q" > /dev/tty; fi
    IFS= read -r REPLY < /dev/tty || REPLY=""
    [ -n "$REPLY" ] || REPLY="$def"
}

yesno() {  # yesno "otázka" "Y|N"
    local q="$1" def="${2:-Y}" a
    if [ "$def" = "Y" ]; then printf '%s [Y/n]: ' "$q" > /dev/tty; else printf '%s [y/N]: ' "$q" > /dev/tty; fi
    IFS= read -r a < /dev/tty || a=""
    [ -n "$a" ] || a="$def"
    case "$a" in y|Y|a|A|yes|ano) return 0 ;; *) return 1 ;; esac
}

[ "$(uname -s)" = "Darwin" ] || die "Tento skript je pre macOS. Na Windows použi webapp.cmd, na Linuxe platforms/freqtrade/scripts/setup.sh."

bold "IBS Backtester - inštalácia na macOS"
echo

# ---------------------------------------------------------------------------- #
# 1. Xcode Command Line Tools (git, kompilátor pre pip balíky)
# ---------------------------------------------------------------------------- #
if ! xcode-select -p >/dev/null 2>&1; then
    warn "Chýbajú Xcode Command Line Tools (git, kompilátor)."
    if yesno "Spustiť ich inštaláciu teraz? (otvorí sa systémové okno)" Y; then
        xcode-select --install 2>/dev/null || true
        echo
        echo "Po dokončení inštalácie v systémovom okne spusti tento skript znova."
        exit 0
    else
        die "Bez Command Line Tools sa nedá pokračovať."
    fi
fi
ok "Xcode Command Line Tools: $(git --version)"

# ---------------------------------------------------------------------------- #
# 2. Homebrew
# ---------------------------------------------------------------------------- #
if ! command -v brew >/dev/null 2>&1; then
    # Apple Silicon inštaluje do /opt/homebrew, ktorý nemusí byť v PATH tohto shellu
    if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"
    fi
fi
if ! command -v brew >/dev/null 2>&1; then
    warn "Chýba Homebrew (správca balíkov)."
    if yesno "Nainštalovať Homebrew? (oficiálny skript, vypýta si heslo do macOS)" Y; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/tty
        if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"
        fi
        command -v brew >/dev/null 2>&1 || die "Homebrew sa nenainštaloval. Otvor nový terminál a spusti skript znova."
    else
        die "Bez Homebrew sa nedá nainštalovať TA-Lib ani Python."
    fi
fi
ok "Homebrew: $(brew --prefix)"

# ---------------------------------------------------------------------------- #
# 3. Python 3.12 + TA-Lib
# ---------------------------------------------------------------------------- #
bold "Balíky cez Homebrew"
for f in "$PY_FORMULA" ta-lib; do
    if brew list --versions "$f" 2>/dev/null | grep -q .; then
        ok "$f už je nainštalovaný"
    else
        echo "  inštalujem $f ..."
        brew install "$f"
    fi
done
PYTHON_BIN="$(brew --prefix "$PY_FORMULA")/bin/python3.12"
[ -x "$PYTHON_BIN" ] || die "Nenašiel som $PYTHON_BIN"
ok "Python: $("$PYTHON_BIN" --version)"

# ---------------------------------------------------------------------------- #
# 4. Kam a ako klonovať
# ---------------------------------------------------------------------------- #
echo
bold "Umiestnenie"
ask "Do ktorého priečinka repozitár klonovať" "$HOME/Projects"
PARENT="${REPLY/#\~/$HOME}"
ask "Ako sa má priečinok repozitára volať" "imbalance_strategy"
NAME="$REPLY"
TARGET="$PARENT/$NAME"

echo
if yesno "Použiť SSH namiesto HTTPS na klonovanie? (len ak máš na GitHube SSH kľúč)" N; then
    REPO_URL="$REPO_URL_SSH"
else
    REPO_URL="$REPO_URL_HTTPS"
fi

echo
bold "Tester"
DEFAULT_NAME="$(git config --global user.name 2>/dev/null || true)"
[ -n "$DEFAULT_NAME" ] || DEFAULT_NAME="$(id -F 2>/dev/null || whoami)"
ask "Meno testera (ukladá sa ku každému behu a ako autor commitov)" "$DEFAULT_NAME"
TESTER="$REPLY"
DEFAULT_MAIL="$(git config --global user.email 2>/dev/null || true)"
ask "E-mail pre git commity (len do histórie behov)" "${DEFAULT_MAIL:-$(whoami)@$(hostname -s).local}"
TESTER_MAIL="$REPLY"

# ---------------------------------------------------------------------------- #
# 5. Klon / aktualizácia
# ---------------------------------------------------------------------------- #
echo
bold "Repozitár"
mkdir -p "$PARENT"
if [ -d "$TARGET/.git" ]; then
    ok "$TARGET už existuje - aktualizujem (git pull)"
    git -C "$TARGET" pull --rebase --autostash
else
    [ -e "$TARGET" ] && die "$TARGET existuje, ale nie je to git repozitár. Zvoľ iné meno priečinka."
    echo "  git clone $REPO_URL $TARGET"
    git clone "$REPO_URL" "$TARGET" < /dev/tty
fi
git -C "$TARGET" config user.name "$TESTER"
git -C "$TARGET" config user.email "$TESTER_MAIL"
ok "git identita v repozitári: $TESTER <$TESTER_MAIL>"

# ---------------------------------------------------------------------------- #
# 6. Python prostredie, dáta
# ---------------------------------------------------------------------------- #
echo
bold "Python prostredie (freqtrade + ibs, prvýkrát ~10 minút)"
PYTHON="$PYTHON_BIN" "$TARGET/platforms/freqtrade/scripts/setup.sh"

echo
bold "Dáta"
"$TARGET/.venv/bin/python" -m ibs.tools.data_archive merge

# ---------------------------------------------------------------------------- #
# 7. Spúšťač na Ploche + štart
# ---------------------------------------------------------------------------- #
LAUNCHER="$HOME/Desktop/IBS Backtester.command"
if [ -d "$HOME/Desktop" ]; then
    cat > "$LAUNCHER" <<EOF
#!/bin/bash
# Dvojklik spustí IBS Backtester (webapp) a otvorí prehliadač. Ctrl+C v tomto okne ho ukončí.
export IBS_USER="$TESTER"
cd "$TARGET" && exec ./webapp.sh
EOF
    chmod +x "$LAUNCHER"
    ok "Na Ploche je spúšťač: IBS Backtester.command"
fi

echo
bold "Hotovo."
echo "  Repozitár:   $TARGET"
echo "  Spustenie:   dvojklik na 'IBS Backtester.command' na Ploche, alebo:"
echo "               cd \"$TARGET\" && ./webapp.sh"
echo "  Aktualizácia: cd \"$TARGET\" && git pull    (alebo tento skript znova)"
echo "  Návod:       $TARGET/docs/WEBAPP.md"
echo

if yesno "Spustiť webapp teraz?" Y; then
    export IBS_USER="$TESTER"
    cd "$TARGET"
    exec ./webapp.sh
fi
