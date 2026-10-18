"""Behy, ktoré agent spočítal pre niekoho iného — po odovzdaní von z histórie a po čase preč.

    tester/hub_delivered/<run_id>/          adresár behu, presunutý z `tester/runs/`
    tester/hub_delivered/points/<id>.json   bod celku (mriežka, overenie víťaza) vybratý zo `sweeps/`

### Prečo
Agent počíta vo vlastnom runneri, takže beh vznikne v **jeho** `tester/runs/` s tým istým id,
s akým ho hub vráti zadávateľovi. Zadávateľ ho commitne a pushne — a `git pull` na stroji
agenta spadne („untracked working tree files would be overwritten by merge"), lebo ten istý
súbor tam leží mimo gitu. Na srvnas tak webapp týždeň stála na starom kóde.

Beh patrí zadávateľovi a ten ho má, keď ho hub prijal. Agent si preto po úspešnom
odovzdaní (`HubAgent._upload_finished`) svoju kópiu presunie sem (gitignored) a po
`KEEP_DAYS` dňoch ju zmaže (`purge`). Výpočet, ktorý si agent zadal sám sebe, a výpočet,
ktorý hub neprijal (`undelivered`), ostávajú v histórii.

Staré behy spred tejto zmeny upratuje `foreign` + `retire` raz po štarte agenta: len tie,
ktoré git nesleduje (commitnutý beh by sa v gite ukázal ako zmazaný).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

from tradebot.core.env import getenv
from tradebot.core.paths import HUB_DELIVERED

__all__ = ["KEEP_DAYS", "root_for", "retire", "purge", "foreign"]

log = logging.getLogger(__name__)

#: Koľko dní si agent odovzdané behy ešte drží (keby ich zadávateľ predsa hľadal).
#: `TRADEBOT_HUB_DELIVERED_DAYS`; 0 = zmazať hneď pri ďalšom upratovaní.
KEEP_DAYS = float(getenv("HUB_DELIVERED_DAYS") or 14)

POINTS = "points"


def root_for(store: Any) -> Path:
    """Kam odkladať behy zo `store`: pri skutočnej histórii `HUB_DELIVERED`, pri inom
    sklade (testy) vedľa neho — test nesmie siahnuť na `tester/hub_delivered/`."""
    from tradebot.core import paths

    if Path(store.root).resolve() == Path(paths.RUNS_DIR).resolve():
        return Path(HUB_DELIVERED)
    return Path(store.root).parent / "hub_delivered"


def retire(store: Any, run_ids: Iterable[str], root: Path | str | None = None) -> list[str]:
    """Presunie behy (a body celkov) z histórie `store` do `root`. Vráti id, ktoré presunul."""
    ciel = Path(root) if root else root_for(store)
    out: list[str] = []
    for run_id in run_ids:
        d = Path(store.root) / run_id
        if d.is_dir():
            ciel.mkdir(parents=True, exist_ok=True)
            novy = ciel / run_id
            if novy.exists():
                shutil.rmtree(novy)
            shutil.move(str(d), str(novy))
            os.utime(novy)  # vek sa počíta od odovzdania, nie od behu
            for p in (store.chart_cache / f"{run_id}.json.gz", store.chart_cache / f"{run_id}.check.json"):
                p.unlink(missing_ok=True)   # lokálna cache kresieb, dá sa prepočítať
            store._cache.pop(run_id, None)
            store.index.forget(run_id)
            out.append(run_id)
            continue
        bod = store.batches.remove_point(run_id) if store.batches is not None else None
        if bod is not None:
            (ciel / POINTS).mkdir(parents=True, exist_ok=True)
            (ciel / POINTS / f"{run_id}.json").write_text(
                json.dumps(bod, ensure_ascii=False, default=str), encoding="utf-8")
            out.append(run_id)
    return out


def purge(root: Path | str, days: float | None = None, now: float | None = None) -> int:
    """Zmaže odovzdané behy staršie než `days` dní. Vráti, koľko ich zmazal."""
    ciel = Path(root)
    hranica = (now if now is not None else time.time()) - 86400.0 * (KEEP_DAYS if days is None else days)
    n = 0
    for d in (ciel, ciel / POINTS):
        try:
            polozky = list(os.scandir(d))
        except OSError:
            continue
        for e in polozky:
            if e.name == POINTS and d == ciel:
                continue
            try:
                if e.stat().st_mtime >= hranica:
                    continue
                if e.is_dir():
                    shutil.rmtree(e.path)
                else:
                    os.unlink(e.path)
                n += 1
            except OSError as exc:
                log.warning("hub agent: odovzdaný beh %s sa nepodarilo zmazať: %s", e.name, exc)
    return n


def _tracked(path: Path) -> set[str] | None:
    """Prvé zložky ciest, ktoré git v `path` sleduje; `None`, keď sa to nedá zistiť.

    Git sa púšťa z koreňa repozitára, ktorý `path` obsahuje (`REPO`, v testoch rodič s `.git`),
    nie z `path`: v Docker kontajneri je `tester/` samostatný mount a git by sa v ňom zastavil
    na hranici súborového systému („not a git repository")."""
    from tradebot.core.paths import REPO

    path = Path(path).resolve()
    koren = next((d for d in (Path(REPO).resolve(), *path.parents, path) if (d / ".git").exists()
                  and (d == path or d in path.parents)), None)
    if koren is None:
        return None
    rel = path.relative_to(koren).as_posix()
    try:
        r = subprocess.run(["git", "ls-files", "-z", "--", rel or "."], cwd=str(koren),
                           capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    predpona = f"{rel}/" if rel and rel != "." else ""
    return {p[len(predpona):].split("/", 1)[0]
            for p in r.stdout.decode("utf-8", "replace").split("\0") if p.startswith(predpona) and p}


def foreign(store: Any, agent: str, keep: Iterable[str] = ()) -> list[str]:
    """Behy a body, ktoré tento agent spočítal pre iného zadávateľa a git ich nesleduje.

    `keep` sú id, ktoré ešte nemajú ísť preč (rozpočítané, neodovzdané). Keď git nevie
    povedať, čo sleduje, nevráti nič — radšej nič nepresunúť ako presunúť commitnutý beh."""
    keep = set(keep)

    def cudzi(rec: dict[str, Any]) -> bool:
        hub = (rec.get("settings") or {}).get("hub") or {}
        return (hub.get("agent") == agent and bool(hub.get("submitter"))
                and hub.get("submitter") != agent and rec.get("id") not in keep)

    out: list[str] = []
    sledovane = _tracked(Path(store.root))
    if sledovane is not None:
        out += [r["id"] for r in store.search(f"settings.hub.agent={agent}")
                if cudzi(r) and r["id"] not in sledovane]
    if store.batches is not None and Path(store.batches.root).is_dir():
        sledovane = _tracked(Path(store.batches.root))
        if sledovane is not None:
            for data in store.batches.files():
                if f"{data.get('kind')}-{data.get('id')}.json" in sledovane:
                    continue
                for p in data.get("points") or []:
                    rec = store.batches.expand(data, p)
                    if cudzi(rec):
                        out.append(rec["id"])
    return out
