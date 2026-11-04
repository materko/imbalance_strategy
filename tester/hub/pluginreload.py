"""Aktualizácia pluginov bez reštartu procesu (docs/HUB.md, „Pluginy“ — „Nový kód pluginu“).

Plugin hubu (`tester/hub/plugins/<meno>/`) aj plugin agenta (`tester/hub/agent_plugins/<meno>/`) je
celý vo svojom adresári. Keď nový commit mení **len** súbory v adresároch pluginov (a k tomu nanajvýš
súbory, ktoré proces nenačítava — dokumenty, testy, história behov), rozhranie medzi procesom a pluginom
ostalo rovnaké a stačí ten plugin načítať znova: zastaviť jeho vlákno, zahodiť jeho moduly zo
`sys.modules`, naimportovať ich z disku a spustiť nový. Rozhranie = všetko mimo adresárov pluginov
(`base.py` a `__init__.py` v koreni balíka pluginov, jadro, knižnice) — jeho zmena ide po starom:
hub drain + reštart, agent reštart.

    zmeny = changed_files("abc123", "def456")
    mena = plugin_only(zmeny, AGENT_PLUGINS)     # {"telegram"} alebo None
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from types import ModuleType
from typing import Iterable

from tradebot.core.paths import REPO

__all__ = ["HUB_PLUGINS", "AGENT_PLUGINS", "NEUTRAL_PREFIXES", "changed_files", "plugin_only", "reload_package"]

#: Adresáre pluginov v repozitári (s lomkou na konci, ako ich vypíše `git diff --name-only`).
HUB_PLUGINS = "tester/hub/plugins/"
AGENT_PLUGINS = "tester/hub/agent_plugins/"

#: Čo bežiaci proces hubu ani agenta nenačítava — zmena tu plugin-only aktualizáciu nezastaví.
NEUTRAL_PREFIXES = ("docs/", "tester/tests/", "tester/runs/", "tester/profiles/", "tester/analytics/",
                    "tester/archive/", "data/live/")
NEUTRAL_SUFFIXES = (".md",)


def changed_files(old: str, new: str, *, remote_side: bool = False) -> list[str] | None:
    """Súbory zmenené medzi commitmi `old` a `new`; `None`, keď sa to nedá zistiť (commit chýba).
    `remote_side` = len zmeny na strane `new` od spoločného predka (`old...new`) — lokálne nepushnuté
    commity (história behov z webapp) sa nepočítajú, `git pull --rebase` ich len presadí navrch."""
    if not old or not new:
        return None
    rozsah = [f"{old}...{new}"] if remote_side else [old, new]
    try:
        r = subprocess.run(["git", "diff", "--name-only", "--no-renames", *rozsah], cwd=str(REPO),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [line.strip().replace("\\", "/") for line in r.stdout.splitlines() if line.strip()]


def _neutral(path: str) -> bool:
    return path.startswith(NEUTRAL_PREFIXES) or path.endswith(NEUTRAL_SUFFIXES)


def plugin_only(files: Iterable[str] | None, prefix: str) -> set[str] | None:
    """Mená pluginov pod `prefix`, ktorých sa zmena týka, keď je **všetko** ostatné neutrálne; inak `None`
    (zmenilo sa rozhranie alebo iný kód — treba reštart). Súbor priamo v `prefix` (`base.py`, `__init__.py`)
    je rozhranie. Prázdna množina = zmenilo sa len neutrálne (nič načítať netreba)."""
    if files is None:
        return None
    mena: set[str] = set()
    for f in files:
        if f.startswith(prefix):
            zvysok = f[len(prefix):]
            meno, sep, _ = zvysok.partition("/")
            if not sep or not meno or meno.startswith(("_", ".")):
                return None
            mena.add(meno)
        elif not _neutral(f):
            return None
    return mena


def reload_package(name: str) -> ModuleType:
    """Zahodí balík `name` a všetky jeho podmoduly zo `sys.modules` a naimportuje ho znova z disku.
    Staré objekty (inštancia pluginu) držia staré moduly, kým ich host nepustí."""
    for mod in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
        del sys.modules[mod]
    importlib.invalidate_caches()
    return importlib.import_module(name)
