"""Chudý klon pre počítanie: sťahuj kód, nie cudziu históriu behov a archív, čo netreba.

    python -m tester.hub sparse                       # čo je nastavené
    python -m tester.hub sparse --no-history          # bez cudzích behov (6 GB)
    python -m tester.hub sparse --data binance        # archív len z binance (namiesto 2 GB)
    python -m tester.hub sparse --no-data             # žiadny archív (dáta už mám zložené)
    python -m tester.hub sparse --off                 # späť celý strom

Repozitár nesie aj **dáta**: `data/archive/` (2 GB sviečok po rokoch) a `tester/runs/`
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

import ast
import subprocess
from typing import Any

from tradebot.core.paths import REPO

__all__ = ["build_rules", "apply", "show", "off", "migrate_legacy", "hub_rules_at", "BALLAST", "HUB_RULES"]

#: Adresáre, ktoré počítajúci agent nepotrebuje ani raz: cudzia história behov a všetko,
#: čo sa z nej odvodzuje. Vlastné behy si píše sám (nie sú v gite, kým ich nepushne).
BALLAST = ("/tester/runs/**", "/tester/archive/**", "/tester/analytics/**",
           "/tester/sweeps/**")

#: Hub nepočíta nič — nepotrebuje ani archív, ani behy, ani prepisy do iných jazykov (`ports/` jadra aj stratégií).
#: Ani živé dáta v gite: tie pushuje vlastný plugin `livedata` z vlastného stromu a vlastného klonu.
#: Staré cesty (`data_archive/`, `data_live/`, `csharp/`) ostávajú, kým ich má niektorý klon v histórii,
#: aby hub po presune pod `data/` a `tradebot/` nestiahol 2 GB sviečok (docs/DIRECTORIES.md).
HUB_RULES = ("/*", "!/data/**", "!/tradebot/core/ports/**", "!/tradebot/strategies/*/ports/**",
             "!/data_archive/**", "!/data_live/**", "!/csharp/**",
             *(f"!{p}" for p in BALLAST))


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
        rules.append("!/data/archive/**")
        for zdroj in data:
            zdroj = zdroj.strip().strip("/")
            if zdroj:
                rules.append(f"/data/archive/tester/{zdroj}/**")
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


#: Cesty pred presunom pod `data/` (27. 10. 2026) → nové (docs/DIRECTORIES.md).
LEGACY_PATHS = (("/data_archive/", "/data/archive/"), ("/data_live/", "/data/live/"))


def migrate_legacy(repo: str | None = None) -> dict[str, Any] | None:
    """Klon s pravidlami na staré cesty prepne na nové; `None`, keď nie je čo meniť.

    Bez toho by agent s `--data binance` po presune archívu pod `data/archive/` mal v strome celý
    archív (pravidlo `/*` zahrnie nový `data/`) a staré pravidlo by už nič nevyraďovalo.
    """
    rules = show(repo)["rules"]
    nove = []
    for r in rules:
        for stare, nova in LEGACY_PATHS:
            r = r.replace(stare, nova)
        nove.append(r)
    if not rules or nove == rules:
        return None
    return apply(nove, filter_blobs=False, repo=repo)


def hub_rules_at(rev: str = "FETCH_HEAD", repo: str | None = None) -> list[str] | None:
    """`HUB_RULES` tak, ako sú v commite `rev` — `None`, keď sa nedajú zistiť.

    Klon hubu musí dostať pravidlá nového commitu **pred** `reset --hard` naň: reset so starými stiahne
    a zapíše všetko, čo nový commit pridal mimo starého výberu (27. 10. 2026 po presune pod `data/` 1,8 GB
    sviečok). Zo súboru sa vykonajú len priradenia konštánt (MENO = …), modul sa neimportuje — v `rev`
    môže závisieť od kódu, ktorý v strome ešte nie je.
    """
    r = _git("show", f"{rev}:tester/hub/sparse.py", repo=repo)
    if r.returncode != 0:
        return None
    try:
        konstanty = [n for n in ast.parse(r.stdout).body if isinstance(n, ast.Assign)
                     and all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets)]
        ns: dict[str, Any] = {"__builtins__": {}}
        exec(compile(ast.Module(body=konstanty, type_ignores=[]), "sparse.py", "exec"), ns)  # noqa: S102
    except Exception:   # noqa: BLE001 — čokoľvek iné ako čisté konštanty: pravidlá nepoznám
        return None
    rules = ns.get("HUB_RULES")
    if not isinstance(rules, (tuple, list)) or not rules or not all(isinstance(x, str) for x in rules):
        return None
    return list(rules)


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
