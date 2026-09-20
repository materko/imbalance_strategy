"""Chudý klon pre počítanie: sťahuj kód, nie cudziu históriu behov a archív, čo netreba.

    python -m tester.hub sparse                       # čo je nastavené
    python -m tester.hub sparse --no-history          # bez cudzích behov (6 GB)
    python -m tester.hub sparse --data binance        # archív len z binance (namiesto 2 GB)
    python -m tester.hub sparse --no-data             # žiadny archív (dáta už mám zložené)
    python -m tester.hub sparse --off                 # späť celý strom

Repozitár nesie aj **dáta**: `data_archive/` (2 GB sviečok po rokoch) a `tester/runs/`
(história behov, dnes cez 6 GB). Tester ich chce, agent, ktorý len počíta, z nich
potrebuje nanajvýš archív toho, na čom počíta — a hub nič z toho. Každý `git pull` ich
pritom ťahá všetkým.

Riešenie sú dve nastavenia gitu naraz:

- **sparse-checkout** (zoznam pravidiel nižšie) povie, čo má byť v pracovnom strome,
- **partial clone** (`remote.origin.partialclonefilter=blob:none`) povie, že obsah
  súborov mimo neho sa **ani nesťahuje**; keby ho niekto predsa potreboval, git si ho
  dotiahne sám.

Bez toho druhého by sa všetko stiahlo a len by sa nezapísalo na disk.

**Čo už v klone je, sa nezmaže z `.git`** — chudé je až to, čo pribudne. A pozor: to, čo
sa vyradí, **zmizne z pracovného stromu** (`tester/runs/` prestane byť v histórii webapp).
Na stroji, ktorý je aj tester, sa preto `--no-history` nedáva.
"""

from __future__ import annotations

import subprocess
from typing import Any

from tradebot.core.paths import REPO

__all__ = ["build_rules", "apply", "show", "off", "BALLAST", "HUB_RULES"]

#: Adresáre, ktoré počítajúci agent nepotrebuje ani raz: cudzia história behov a všetko,
#: čo sa z nej odvodzuje. Vlastné behy si píše sám (nie sú v gite, kým ich nepushne).
BALLAST = ("/tester/runs/**", "/tester/archive/**", "/tester/analytics/**",
           "/tester/sweeps/**", "/projekty/**")

#: Hub nepočíta nič — nepotrebuje ani archív, ani behy, ani C# jadro.
HUB_RULES = ("/*", "!/data_archive/**", "!/csharp/**", *(f"!{p}" for p in BALLAST))


def _git(*args: str, repo: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo or str(REPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=300)


def build_rules(data: list[str] | None = None, history: bool = True) -> list[str]:
    """Pravidlá sparse-checkoutu (non-cone; posledné pravidlo, ktoré sadne, platí).

    `data` = zoznam zdrojov archívu, ktoré chcem (`["binance"]`), `[]` = žiadny archív,
    `None` = celý. `history=False` vyradí cudziu históriu behov a analytík.
    """
    rules = ["/*"]
    if data is not None:
        rules.append("!/data_archive/**")
        for zdroj in data:
            zdroj = zdroj.strip().strip("/")
            if zdroj:
                rules.append(f"/data_archive/tester/{zdroj}/**")
    if not history:
        rules += [f"!{p}" for p in BALLAST]
    return rules


def apply(rules: list[str] | tuple[str, ...], *, filter_blobs: bool = True,
          repo: str | None = None) -> dict[str, Any]:
    """Nastaví pravidlá a (ak sa chce) aj to, že sa vyradené súbory ani nesťahujú."""
    kroky: list[subprocess.CompletedProcess] = []
    if filter_blobs:
        kroky.append(_git("config", "remote.origin.promisor", "true", repo=repo))
        kroky.append(_git("config", "remote.origin.partialclonefilter", "blob:none", repo=repo))
    kroky.append(_git("sparse-checkout", "init", "--no-cone", repo=repo))
    r = subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "--stdin"],
                       cwd=repo or str(REPO), input="\n".join(rules) + "\n",
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600)
    kroky.append(r)
    vystup = "\n".join((k.stdout + k.stderr).strip() for k in kroky if (k.stdout + k.stderr).strip())
    return {"ok": all(k.returncode == 0 for k in kroky), "rules": list(rules), "output": vystup}


def off(repo: str | None = None) -> dict[str, Any]:
    """Späť celý strom: pravidlá preč a nové súbory sa zase sťahujú celé."""
    kroky = [_git("sparse-checkout", "disable", repo=repo),
             _git("config", "--unset", "remote.origin.partialclonefilter", repo=repo),
             _git("config", "--unset", "remote.origin.promisor", repo=repo)]
    # `--unset` bez existujúceho kľúča vráti 5 — to nie je chyba.
    ok = kroky[0].returncode == 0 and all(k.returncode in (0, 5) for k in kroky[1:])
    return {"ok": ok, "output": "\n".join((k.stdout + k.stderr).strip() for k in kroky
                                          if (k.stdout + k.stderr).strip())}


def show(repo: str | None = None) -> dict[str, Any]:
    """Čo je nastavené: pravidlá (ak sú) a či sa vyradený obsah sťahuje."""
    r = _git("sparse-checkout", "list", repo=repo)
    rules = [line for line in r.stdout.splitlines() if line.strip()] if r.returncode == 0 else []
    f = _git("config", "--get", "remote.origin.partialclonefilter", repo=repo)
    return {"on": bool(rules), "rules": rules, "filter": f.stdout.strip() or None}
