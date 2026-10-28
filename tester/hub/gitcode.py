"""Verzia kódu pre hub: ktorý commit zadávateľ má a či ho má aj počítajúci agent.

Rovnaký beh na inom commite dá iné čísla, takže výpočet nesie **verziu kódu zadávateľa**
(krátky commit) a agent ju pred behom overí:

- `version()`      — commit, na ktorom klon stojí (`git rev-parse --short HEAD`),
- `deploy_version()` — commit, ktorý nesie živé nasadenie: HEAD, alebo posledný commit z GitHubu
                     s tým istým kódom, keď má HEAD navrch len nepushnuté dáta,
- `has_commit(c)`  — pozná klon commit `c` vôbec? (prepísaný rebase už nie),
- `has_platform_code(w, i)` — má kód nainštalovaný z commitu `i` všetko z `w`, čo platformy používajú?
- `has_version(c)` — je commit `c` v histórii HEAD? (`git merge-base --is-ancestor`),
- `pull()`         — `git fetch` + `rebase --autostash origin/main`, to isté, čo Pull vo webapp
                     (`tester.webapp.gitsync`); v kontajneri (`TRADEBOT_HUB_PULL=host`) ho robí
                     hostiteľ na pokyn (`request_host_pull`, `host_pull_result`),
- `versus_main(vs)`— o koľko commitov je každá verzia za `origin/main` (karta Hub, agenti),
- `dirty_code()`   — necommitnuté zmeny v kóde (nie v histórii behov): taký klon posiela
                     verziu, ktorá jeho kód nepopisuje, a CLI na to upozorní.

Verzia je commit celého repozitára, nie číslo stratégie — stratégie, jadro aj adaptéry
žijú v jednom strome a menia sa spolu.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from tradebot.core.paths import HUB_PULL_REQUEST, HUB_PULL_RESULT, PLATFORM_CODE, REPO

__all__ = ["version", "deploy_version", "has_commit", "has_platform_code", "has_version", "is_ancestor", "on_remote", "versus_main", "pull", "pull_mode",
           "request_host_pull", "host_pull_result", "dirty_code"]

#: Čo sa nepovažuje za kód: história behov, profily a analytiky testera idú cez Push.
_DATA_PREFIXES = ("tester/runs/", "tester/profiles/", "tester/analytics/", "data/archive/", "docs/")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def version() -> str:
    """Krátky commit HEAD; prázdny reťazec mimo gitu."""
    try:
        r = _git("rev-parse", "--short", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


_deploy_cache: dict[str, str] = {}


def deploy_version() -> str:
    """Commit, ktorý ide k živému nasadeniu (`version`) a ako cieľ „Aktualizovať kód“: HEAD, ale keď má
    HEAD nad `origin/<vetva>` len nepushnuté dáta (behy a profily z webapp), tak ich spoločný predok —
    ten istý kód, ktorý už je na GitHube. Nepushnutý commit `git pull --rebase` neskôr prepíše na iný
    sha a nasadenie by navždy chcelo commit, ktorý už nikde nie je („kód: zastaraný“, hoci stroj má
    novší kód). Nepushnutý kód ostáva HEAD — to webapp hlási ako „nie je na GitHube“."""
    from tradebot.core.env import getenv

    try:
        head = _git("rev-parse", "HEAD")
        if head.returncode != 0:
            return ""
        full = head.stdout.strip()
        if full in _deploy_cache:
            return _deploy_cache[full]
        out = full[:9]
        br = getenv("GIT_BRANCH", "").strip() or "main"
        base = _git("merge-base", "HEAD", f"origin/{br}")
        if base.returncode == 0 and base.stdout.strip() != full:
            zmeny = _git("diff", "--name-only", base.stdout.strip(), full)
            if zmeny.returncode == 0 and all(c.startswith(_DATA_PREFIXES) for c in zmeny.stdout.split()):
                out = base.stdout.strip()[:9]
    except (OSError, subprocess.SubprocessError):
        return version()
    if len(_deploy_cache) > 50:
        _deploy_cache.clear()
    _deploy_cache[full] = out
    return out


def has_commit(commit: str | None) -> bool:
    """Pozná tento klon commit `commit`? (Nepushnutý commit prepísaný rebase alebo z cudzej vetvy nie.)"""
    if not commit:
        return False
    try:
        return _git("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def has_version(commit: str | None) -> bool:
    """Je `commit` v histórii HEAD? Prázdna požiadavka = nič sa nechce, teda áno."""
    if not commit:
        return True
    try:
        r = _git("merge-base", "--is-ancestor", commit, "HEAD")
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def is_ancestor(older: str | None, newer: str | None) -> bool:
    """Je `older` v histórii `newer`? (Kód nasadený z `newer` má všetko z `older` — stav `ok`, nie
    `outdated`.) Neznámy commit alebo prázdny vstup = nie."""
    if not older or not newer:
        return False
    try:
        r = _git("merge-base", "--is-ancestor", older, newer)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def has_platform_code(wanted: str | None, installed: str | None) -> bool:
    """Má platforma s kódom z `installed` všetko, čo z `wanted` potrebuje? Áno, keď je `wanted` v histórii
    `installed`, alebo keď sa medzi nimi nezmenilo nič z `PLATFORM_CODE` — commit webapp či hubu kód na
    NinjaTraderi a MT5 nezastará a „Aktualizovať kód“ by ich len zbytočne reštartoval. Neznámy commit = nie."""
    if is_ancestor(wanted, installed):
        return True
    if not wanted or not installed:
        return False
    try:
        return _git("diff", "--quiet", wanted, installed, "--", *PLATFORM_CODE).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def on_remote(commit: str | None, fetch: bool = True) -> bool | None:
    """Je `commit` na GitHube (v `origin/<vetva>`)? Agent si cieľ aktualizácie ťahá odtiaľ — commit,
    ktorý je len v tomto klone, si nestiahne. `fetch` najprv obnoví `origin/<vetva>`; `None` = nevedno
    (mimo gitu, bez `origin`)."""
    if not commit:
        return None
    from tradebot.core.env import getenv

    br = getenv("GIT_BRANCH", "").strip() or "main"
    try:
        if fetch:
            _git("fetch", "--quiet", "origin", br)
        if _git("rev-parse", "--verify", "--quiet", f"origin/{br}").returncode != 0:
            return None
        return _git("merge-base", "--is-ancestor", commit, f"origin/{br}").returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def versus_main(versions: list[str], fetch: bool = True) -> dict[str, Any] | None:
    """Ako sú `versions` (commity agentov) na tom voči `origin/<vetva>`: `{"main": krátky commit,
    "versions": {verzia: {"behind": n, "ahead": m}}}` — `behind` = koľko commitov z main nemá,
    `ahead` = koľko jeho commitov v main nie je (nepushnuté). Verzia, ktorú tento klon nepozná,
    má `None`. `None` celé = nevedno (mimo gitu, bez `origin`)."""
    from tradebot.core.env import getenv

    br = getenv("GIT_BRANCH", "").strip() or "main"
    ref = f"origin/{br}"
    try:
        if fetch:
            _git("fetch", "--quiet", "origin", br)
        r = _git("rev-parse", "--short", "--verify", "--quiet", ref)
        if r.returncode != 0:
            return None
        out: dict[str, Any] = {"main": r.stdout.strip(), "versions": {}}
        for v in dict.fromkeys(x for x in versions if x):
            za = _git("rev-list", "--count", f"{v}..{ref}")
            pred = _git("rev-list", "--count", f"{ref}..{v}")
            out["versions"][v] = ({"behind": int(za.stdout), "ahead": int(pred.stdout)}
                                  if za.returncode == 0 and pred.returncode == 0 else None)
        return out
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def pull_mode() -> str:
    """Kto robí `git pull` tohto klonu: `on` agent sám, `host` hostiteľ kontajnera na pokyn
    (`TRADEBOT_HUB_PULL=host`, `docker/host-pull.sh`), `off` hostiteľ len svojím časovačom."""
    from tradebot.core.env import getenv

    v = (getenv("HUB_PULL") or "on").strip().lower()
    if v == "host":
        return "host"
    return "off" if v in ("off", "0", "false", "no", "nie") else "on"


def pull_enabled() -> bool:
    """Ťahá agent kód sám? V kontajneri nie — kód je mount z hostiteľa, pull sa robí tam."""
    return pull_mode() == "on"


def request_host_pull(request: str) -> None:
    """Pokyn hostiteľovi „sprav git pull hneď" (⟳ na karte Hub): zapíše `request` do
    `HUB_PULL_REQUEST`; systemd path jednotka hostiteľa naň spustí `docker/host-pull.sh`."""
    HUB_PULL_REQUEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = HUB_PULL_REQUEST.with_name(HUB_PULL_REQUEST.name + ".tmp")
    tmp.write_text(request + "\n", encoding="utf-8")
    os.replace(tmp, HUB_PULL_REQUEST)


def host_pull_result(request: str) -> dict[str, Any] | None:
    """Výsledok pullu, ktorý hostiteľ spravil po pokyne `request`, alebo `None`, kým nie je.

    `HUB_PULL_RESULT` píše `docker/host-pull.sh`: prvý riadok = pokyn, ktorý bol v súbore pred
    pullom (aj pri behu z časovača), druhý = návratový kód `git pull`, zvyšok = jeho výstup."""
    try:
        riadky = HUB_PULL_RESULT.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if len(riadky) < 2 or riadky[0].strip() != request:
        return None
    vystup = "\n".join(riadky[2:]).strip()
    try:
        ok = int(riadky[1].strip()) == 0
    except ValueError:
        ok = False
    return {"ok": ok, "output": vystup or ("git pull na hostiteľovi ok" if ok else "git pull na hostiteľovi zlyhal")}


def pull() -> dict[str, Any]:
    """Pull `origin main` s rebase a autostash — cez `gitsync`, nech je to jedna cesta."""
    from ..webapp import gitsync

    if not pull_enabled():
        return {"ok": False, "output": f"git pull je na tomto agentovi vypnutý (TRADEBOT_HUB_PULL={pull_mode()}, "
                                       "kontajner) — sprav `git pull` na hostiteľovi"}
    try:
        return gitsync.pull()
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "output": f"{type(exc).__name__}: {exc}"}


def dirty_code() -> list[str]:
    """Zmenené alebo nové súbory kódu (mimo histórie behov), alebo prázdny zoznam."""
    try:
        r = _git("status", "--porcelain")
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for line in r.stdout.splitlines():
        cesta = line[3:].strip().replace("\\", "/")
        if cesta and not cesta.startswith(_DATA_PREFIXES):
            out.append(cesta)
    return out
