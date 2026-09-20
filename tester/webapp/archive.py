"""Archív behov — `cli archive`. Beh z histórie odíde, ale nestratí sa.

    tester/archive/runs-0001.jsonl.gz    celé behy, riadok na beh, gzip
    tester/archive/index.json            ktorý beh je v ktorom súbore

Načo: história rástla po behoch a jeden beh je adresár so štyrmi súbormi, z toho
`trades.json` ~250 kB. Pri 37 852 behoch je to 11 GB a 132 000 súborov v pracovnom
strome — `git status` sa vlečie, klon testera trvá večnosť a zálohovať sa to nedá.
Zabalené do gzipovaného JSONL je z toho rádovo desatina a pár súborov.

Čo sa archivuje: **celý beh** — `run.json` (config, nastavenia, výsledok, equity krivka),
`trades.json`, `plan.json` aj `log.txt`. `restore` z toho vyrobí presne ten istý adresár,
takže archivovanie je vratné. Kresby grafu sa neriešia: tie sú lokálna cache a prepočítajú
sa (`tester.webapp.replay`).

Poradie pri vykonaní je ako v `prune` — **najprv zapíš a prečítaj späť, potom maž**. Keby
sa niečo pokazilo uprostred, ostane viac, nie menej: beh bude v archíve aj v histórii.

Čo archív **nespraví**: nezmenší `.git`. Staré objekty v histórii gitu ostávajú, zmenší sa
pracovný strom a to, čo sa klonuje ďalej. Zmenšiť klon by chcelo prepis histórie gitu — to
je samostatné rozhodnutie, nie vec tohto nástroja.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from tradebot.core.paths import ARCHIVE_DIR

from .store import PLAN_FILE, RunStore

__all__ = ["Plan", "plan", "report", "apply", "restore", "archived"]

#: Nad koľko bajtov (zabalených) sa začne písať ďalší súbor. GitHub odmieta súbory nad
#: 100 MB a diff veľkého súboru je aj tak na nič, takže radšej viac menších. Dávka sa
#: nerozdeľuje, takže súbor môže prerásť o jednu dávku — do stovky megabajtov ďaleko.
MAX_BYTES = 40_000_000

#: Súbory behu, ktoré idú do archívu. `chart.json.gz` nie — je to lokálna cache.
FILES = ("trades.json", PLAN_FILE, "log.txt")


def _index_path() -> Path:
    return Path(ARCHIVE_DIR) / "index.json"


def archived(root: Path | None = None) -> dict[str, str]:
    """`{run_id: súbor archívu}` — čo už je odložené."""
    p = Path(root) / "index.json" if root else _index_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("runs", {}) if isinstance(data, dict) else {}


@dataclass
class Plan:
    """Čo by `apply` odložilo."""

    ids: list[str] = field(default_factory=list)
    bytes: int = 0
    #: behy, ktoré sú v archíve už teraz (preskočia sa)
    skipped: list[str] = field(default_factory=list)


def _dir_size(d: Path) -> int:
    total = 0
    try:
        for e in d.iterdir():
            try:
                total += e.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return total


def plan(store: RunStore, records: Iterable[dict[str, Any]], root: Path | None = None) -> Plan:
    """Plán archivovania pre vybrané behy — nič nezapisuje."""
    uz = archived(root)
    out = Plan()
    for rec in records:
        run_id = rec.get("id")
        if not run_id or not (store.root / run_id).is_dir():
            continue
        if run_id in uz:
            out.skipped.append(run_id)
            continue
        out.ids.append(run_id)
        out.bytes += _dir_size(store.root / run_id)
    out.ids.sort()
    return out


def report(p: Plan) -> str:
    riadky = [f"na archiváciu: {len(p.ids)} behov, {p.bytes / 1e9:,.2f} GB".replace(",", " ")]
    if p.skipped:
        riadky.append(f"už v archíve (preskočí sa): {len(p.skipped)}")
    if p.ids:
        riadky.append(f"najstarší {p.ids[0]}, najnovší {p.ids[-1]}")
    return "\n".join(riadky)


def _record_of(store: RunStore, run_id: str) -> dict[str, Any] | None:
    """Celý beh do jedného riadku archívu — presne to, čo leží v jeho adresári."""
    d = store.root / run_id
    try:
        run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    riadok: dict[str, Any] = {"id": run_id, "run": run}
    for meno in FILES:
        p = d / meno
        if not p.exists():
            continue
        try:
            riadok[meno] = p.read_text(encoding="utf-8")
        except OSError:
            return None
    return riadok


def _next_file(root: Path) -> Path:
    """Súbor, do ktorého sa pripisuje — nový, keď posledný prerástol `MAX_BYTES`."""
    existujuce = sorted(root.glob("runs-*.jsonl.gz"))
    if existujuce and existujuce[-1].stat().st_size < MAX_BYTES:
        return existujuce[-1]
    cislo = int(existujuce[-1].stem.split("-")[1].split(".")[0]) + 1 if existujuce else 1
    return root / f"runs-{cislo:04d}.jsonl.gz"


def _write_index(root: Path, mapa: dict[str, str]) -> None:
    with open(root / "index.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"version": 1, "runs": dict(sorted(mapa.items()))}, fh,
                  ensure_ascii=False, indent=1)
        fh.write("\n")


def apply(store: RunStore, p: Plan, root: Path | None = None,
          log: Callable[[str], None] = print, batch: int = 500) -> dict[str, int]:
    """Odlož behy do archívu a až po overení zmaž ich adresáre."""
    root = Path(root) if root else Path(ARCHIVE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    mapa = archived(root)
    hotovo, chyby = 0, 0
    zvysok = [i for i in p.ids if i not in mapa]
    while zvysok:
        subor = _next_file(root)
        davka, zvysok = zvysok[:batch], zvysok[batch:]
        zapisane: list[str] = []
        with gzip.open(subor, "at", encoding="utf-8", newline="\n") as fh:
            for run_id in davka:
                riadok = _record_of(store, run_id)
                if riadok is None:
                    chyby += 1
                    continue
                fh.write(json.dumps(riadok, ensure_ascii=False, default=str) + "\n")
                zapisane.append(run_id)
        # Prečítaj späť, čo sa práve zapísalo — až potom sa smie mazať.
        v_subore = _ids_in(subor)
        for run_id in zapisane:
            if run_id not in v_subore:
                chyby += 1
                continue
            mapa[run_id] = subor.name
            store.delete(run_id)
            hotovo += 1
        _write_index(root, mapa)
        log(f"{subor.name}: {len(zapisane)} behov, ostáva {len(zvysok)}")
    return {"archived": hotovo, "failed": chyby, "files": len(list(root.glob("runs-*.jsonl.gz")))}


def _ids_in(subor: Path) -> set[str]:
    out: set[str] = set()
    try:
        with gzip.open(subor, "rt", encoding="utf-8") as fh:
            for riadok in fh:
                try:
                    out.add(json.loads(riadok)["id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        pass
    return out


def restore(store: RunStore, run_id: str, root: Path | None = None) -> Path | None:
    """Vráť archivovaný beh späť do histórie — adresár bude presne ako predtým."""
    root = Path(root) if root else Path(ARCHIVE_DIR)
    subor = archived(root).get(run_id)
    if subor is None:
        return None
    try:
        with gzip.open(root / subor, "rt", encoding="utf-8") as fh:
            for riadok in fh:
                try:
                    data = json.loads(riadok)
                except json.JSONDecodeError:
                    continue
                if data.get("id") != run_id:
                    continue
                d = store.root / run_id
                d.mkdir(parents=True, exist_ok=True)
                with open(d / "run.json", "w", encoding="utf-8", newline="\n") as out:
                    json.dump(data["run"], out, ensure_ascii=False, indent=2, default=str)
                    out.write("\n")
                for meno in FILES:
                    if meno in data:
                        (d / meno).write_text(data[meno], encoding="utf-8", newline="")
                store.index.put(run_id)
                return d
    except OSError:
        return None
    return None


def forget(run_id: str, root: Path | None = None) -> bool:
    """Vyhoď beh z registra archívu (po `restore`, keď má zase žiť v histórii).

    Riadok v `.jsonl.gz` ostáva — prepisovať kvôli jednému behu celý súbor sa neoplatí
    a `restore` aj tak ide cez register.
    """
    root = Path(root) if root else Path(ARCHIVE_DIR)
    mapa = archived(root)
    if run_id not in mapa:
        return False
    del mapa[run_id]
    _write_index(root, mapa)
    return True


def prune_files(root: Path | None = None) -> int:
    """Zmaž súbory archívu, na ktoré už register neukazuje (po hromadnom `restore`)."""
    root = Path(root) if root else Path(ARCHIVE_DIR)
    pouzite = set(archived(root).values())
    zmazane = 0
    for p in root.glob("runs-*.jsonl.gz"):
        if p.name not in pouzite:
            p.unlink()
            zmazane += 1
    return zmazane
