"""Verzia kódu pre hub: ktorý commit zadávateľ má a či ho má aj počítajúci agent.

Rovnaký beh na inom commite dá iné čísla, takže výpočet nesie **verziu kódu zadávateľa**
(krátky commit) a agent ju pred behom overí:

- `version()`      — commit, na ktorom klon stojí (`git rev-parse --short HEAD`),
- `has_version(c)` — je commit `c` v histórii HEAD? (`git merge-base --is-ancestor`),
- `pull()`         — `git pull --rebase --autostash origin main`, to isté, čo Pull vo webapp
                     (`tester.webapp.gitsync`),
- `dirty_code()`   — necommitnuté zmeny v kóde (nie v histórii behov): taký klon posiela
                     verziu, ktorá jeho kód nepopisuje, a CLI na to upozorní.

Verzia je commit celého repozitára, nie číslo stratégie — stratégie, jadro aj adaptéry
žijú v jednom strome a menia sa spolu.
"""

from __future__ import annotations

import subprocess
from typing import Any

from tradebot.core.paths import REPO

__all__ = ["version", "has_version", "pull", "dirty_code"]

#: Čo sa nepovažuje za kód: história behov, profily a analytiky testera idú cez Push.
_DATA_PREFIXES = ("tester/runs/", "tester/profiles/", "tester/analytics/", "data_archive/", "docs/")


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


def has_version(commit: str | None) -> bool:
    """Je `commit` v histórii HEAD? Prázdna požiadavka = nič sa nechce, teda áno."""
    if not commit:
        return True
    try:
        r = _git("merge-base", "--is-ancestor", commit, "HEAD")
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def pull() -> dict[str, Any]:
    """Pull `origin main` s rebase a autostash — cez `gitsync`, nech je to jedna cesta."""
    from ..webapp import gitsync

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
