"""Archív behov (`tester.webapp.archive`) — z histórie preč, ale späť presne taký istý.

Beh je adresár so štyrmi súbormi a `trades.json` v ňom má ~250 kB; pri desaťtisícoch behov
je pracovný strom 11 GB a 132 000 súborov. Archív ich zabalí do gzipovaného JSONL.
Podmienka, bez ktorej by to bolo mazanie, nie archivovanie: **`restore` musí vrátiť presne
to, čo tam bolo**, a zmazať sa smie až po tom, ako sa zapísané dá prečítať späť.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from tester.webapp import archive
from tester.webapp.store import RunStore

TRADE = {"open_date": "2025-09-05T10:03:00+00:00", "close_date": "2025-09-05T11:00:00+00:00",
         "open_rate": 100.0, "close_rate": 102.0, "is_short": False, "profit_abs": 2.0,
         "enter_tag": "tb:1", "exit_reason": "roi"}


def _record(i: int, note: str = "") -> dict:
    return {"id": f"2026090{i}-120000-aaaa0{i}", "status": "done", "user": "t", "note": note,
            "created": f"2026-09-0{i}T10:00:00+00:00",
            "settings": {"strategy": "ibs", "pair": "BTC/USDT:USDT", "timeframe": "3m",
                         "timerange": "20250904-20260904"},
            "params": {"rrRatio": float(i)},
            "result": {"trades": 1, "pnl_pct": float(i)},
            "series": {"equity": [[1, 2.0]] * 20}}


def _store(tmp_path: Path, kolko: int = 5) -> RunStore:
    store = RunStore(tmp_path / "runs")
    for i in range(1, kolko + 1):
        store.save(_record(i, note="" if i % 2 else f"pokus {i}"),
                   trades=[TRADE] * i, log=f"log behu {i}")
    return store


def test_archiv_odlozi_beh_a_restore_ho_vrati_presne_taky_isty(tmp_path: Path):
    store = _store(tmp_path, 3)
    koren = tmp_path / "archive"
    rid = "20260902-120000-aaaa02"
    pred = {p.name: p.read_bytes() for p in (store.root / rid).iterdir()}

    plan = archive.plan(store, [{"id": rid}], root=koren)
    assert plan.ids == [rid] and plan.bytes > 0 and "1 behov" in archive.report(plan)
    assert (store.root / rid).is_dir()                      # plán nič nerobí

    assert archive.apply(store, plan, root=koren, log=lambda t: None) == \
        {"archived": 1, "failed": 0, "files": 1}
    assert not (store.root / rid).exists()                  # adresár je preč
    assert store.page("", 0, 50)[0] == 2                    # a nie je ani v histórii
    assert archive.archived(koren) == {rid: "runs-0001.jsonl.gz"}

    assert archive.restore(store, rid, root=koren) == store.root / rid
    assert {p.name: p.read_bytes() for p in (store.root / rid).iterdir()} == pred
    assert store.page("", 0, 50)[0] == 3
    assert store.get(rid)["series"]["equity"][0] == [1, 2.0]
    assert archive.forget(rid, root=koren) and archive.archived(koren) == {}


def test_maze_sa_az_po_precitani_spat(tmp_path: Path, monkeypatch):
    """Keď sa beh do archívu nedostane, jeho adresár musí ostať."""
    store = _store(tmp_path, 3)
    koren = tmp_path / "archive"
    plan = archive.plan(store, store.all(), root=koren)
    assert len(plan.ids) == 3

    monkeypatch.setattr(archive, "_ids_in", lambda subor: set())     # čítanie späť „zlyhá"
    vysledok = archive.apply(store, plan, root=koren, log=lambda t: None)
    assert vysledok["archived"] == 0 and vysledok["failed"] == 3
    assert store.page("", 0, 50)[0] == 3                             # nič sa nezmazalo


def test_nerozlustitelny_beh_nezhodi_zvysok(tmp_path: Path):
    store = _store(tmp_path, 3)
    koren = tmp_path / "archive"
    plan = archive.plan(store, store.all(), root=koren)
    (store.root / "20260902-120000-aaaa02" / "run.json").write_text("{nie json", encoding="utf-8")

    vysledok = archive.apply(store, plan, root=koren, log=lambda t: None)
    assert vysledok == {"archived": 2, "failed": 1, "files": 1}
    assert (store.root / "20260902-120000-aaaa02").is_dir()          # rozbitý ostal


def test_velky_archiv_sa_rozdeli_na_viac_suborov(tmp_path: Path, monkeypatch):
    """Jeden obrovský súbor by GitHub neprijal — po `MAX_BYTES` sa začína ďalší."""
    store = _store(tmp_path, 5)
    koren = tmp_path / "archive"
    monkeypatch.setattr(archive, "MAX_BYTES", 1)                     # každá dávka nový súbor
    vysledok = archive.apply(store, archive.plan(store, store.all(), root=koren),
                             root=koren, log=lambda t: None, batch=2)
    assert vysledok["archived"] == 5 and vysledok["files"] == 3
    mapa = archive.archived(koren)
    assert sorted(set(mapa.values())) == ["runs-0001.jsonl.gz", "runs-0002.jsonl.gz",
                                          "runs-0003.jsonl.gz"]
    assert all(archive.restore(store, rid, root=koren) is not None for rid in mapa)


def test_uz_archivovany_beh_sa_nearchivuje_druhy_raz(tmp_path: Path):
    store = _store(tmp_path, 3)
    koren = tmp_path / "archive"
    archive.apply(store, archive.plan(store, store.all(), root=koren), root=koren,
                  log=lambda t: None)
    for rid in list(archive.archived(koren)):
        archive.restore(store, rid, root=koren)
    plan = archive.plan(store, store.all(), root=koren)
    assert plan.ids == [] and len(plan.skipped) == 3

    assert archive.prune_files(koren) == 0                            # register naň ešte ukazuje
    for rid in list(archive.archived(koren)):
        archive.forget(rid, root=koren)
    assert archive.prune_files(koren) == 1 and not list(koren.glob("runs-*.jsonl.gz"))


def test_riadok_archivu_nesie_cely_beh(tmp_path: Path):
    store = _store(tmp_path, 2)
    koren = tmp_path / "archive"
    archive.apply(store, archive.plan(store, store.all(), root=koren), root=koren,
                  log=lambda t: None)
    with gzip.open(koren / "runs-0001.jsonl.gz", "rt", encoding="utf-8") as fh:
        riadky = [json.loads(r) for r in fh]
    assert [r["id"] for r in riadky] == ["20260901-120000-aaaa01", "20260902-120000-aaaa02"]
    assert riadky[0]["run"]["params"]["rrRatio"] == 1.0
    assert json.loads(riadky[0]["trades.json"]) == [TRADE]
    assert riadky[0]["log.txt"] == "log behu 1"
