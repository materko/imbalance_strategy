"""Index histórie behov (`tester.webapp.index`) — stránka bez čítania celej histórie.

Prečo vznikol: `RunStore.all()` parsoval pri každom dopyte všetky `run.json`. Pri 37 852
behoch (11 GB) to bolo 30 s procesora na prvý zoznam, 24 GB v pamäti a sekundové zamrznutia
na zbere odpadkov — a to kvôli päťdesiatim riadkom na stránke. Odvodený sqlite index vracia
priamo tú stránku.

Podmienka, na ktorej celé zrýchlenie stojí: **index musí odpovedať presne to isté, čo
prehľadanie súborov**. To sa tu kontroluje dopyt po dopyte proti zálohovej ceste
(`RunStore._scan`), lebo tá je definíciou správania.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tester.webapp.store import RunStore, _match, parse_query

DOPYTY = [
    "", "strategy=ibs", "strategy=orb", "pair~ETH", "pair=ETH/USDT:USDT", "tf=5m", "tf=3",
    "pnl>0", "pnl>=0", "pnl<-1", "trades>15", "pf>1.1", "wr>50", "status=done", "status!=done",
    "seansa", "NY", "note~seansa", "note=2025", "id~aaaa", "user~tester", "engine=freqtrade",
    "profile~btc", "rrRatio>=4", "useStructureFilter=true", "strategy=orb pnl>0 tf=3m",
    "strategy=ibs trades>15 seansa", "nieco-co-tam-nie-je",
]


def _record(i: int) -> dict:
    return {
        "id": f"2026090{i}-12000{i}-aaaa0{i}", "status": "done" if i % 4 else "failed",
        "created": f"2026-09-0{i}T10:00:00+00:00", "user": f"tester{i % 2}",
        "note": "NY seansa" if i % 2 else f"ranný beh {i}",
        "settings": {"strategy": "ibs" if i % 2 else "orb", "timeframe": "3m" if i % 3 else "5m",
                     "pair": "BTC/USDT:USDT" if i < 5 else "ETH/USDT:USDT",
                     "timerange": "20250904-20260904", "profile": f"btcusdt_{i}",
                     "engine": "freqtrade" if i % 2 else "multicharts", "fee": 0.0005},
        "params": {"rrRatio": float(i), "useStructureFilter": i % 2 == 0, "_meta": 1},
        "result": {"trades": 10 + i, "pnl_pct": float(i) - 3.0, "profit_factor": 1.0 + i / 10,
                   "winrate": 40.0 + i * 3, "max_drawdown_pct": float(i)},
        # equity krivka: to je to, čo sa do indexu nekopíruje
        "series": {"equity": [[1000 + j, 100.0] for j in range(50)], "market": []},
    }


def _store(tmp_path: Path, kolko: int = 9) -> RunStore:
    store = RunStore(tmp_path / "runs")
    for i in range(1, kolko + 1):
        store.save(_record(i), trades=[], log="")
    return store


# --------------------------------------------------------------------------- #
# to isté, čo súbory
# --------------------------------------------------------------------------- #


def test_index_odpoveda_to_iste_co_prehladanie_suborov(tmp_path: Path):
    store = _store(tmp_path)
    zo_suborov = store._scan()
    assert len(zo_suborov) == 9
    for q in DOPYTY:
        conds = parse_query(q)
        cakane = sorted(r["id"] for r in zo_suborov if all(_match(r, c) for c in conds))
        assert sorted(r["id"] for r in store.search(q)) == cakane, q
        assert store.page(q, 0, 50)[0] == len(cakane), q


def test_stranka_je_zoradena_od_najnovsieho_a_total_pocita_vsetky(tmp_path: Path):
    store = _store(tmp_path)
    total, prva = store.page("", 0, 4)
    assert total == 9 and [r["id"] for r in prva] == [r["id"] for r in store.all()[:4]]
    assert [r["id"] for r in prva] == sorted((r["id"] for r in prva), reverse=True)
    _, druha = store.page("", 4, 4)
    _, posledna = store.page("", 8, 4)
    assert len(druha) == 4 and len(posledna) == 1
    assert not ({r["id"] for r in prva} & {r["id"] for r in druha})
    assert store.page("", 100, 4) == (9, [])


def test_zoznam_nenesie_equity_krivku_ale_detail_behu_ano(tmp_path: Path):
    store = _store(tmp_path, 2)
    assert all("series" not in r for r in store.all())
    assert all("series" not in r for r in store.page("", 0, 50)[1])
    rec = store.get("20260901-120001-aaaa01")
    assert len(rec["series"]["equity"]) == 50        # detail číta súbor, nie index
    assert rec["params"]["rrRatio"] == 1.0


def test_hladanie_nad_parametrami_stratégie_dofiltruje_python(tmp_path: Path):
    """`rrRatio` sqlite nepozná — musí prejsť zvyškom podmienok, nie ich zahodiť."""
    store = _store(tmp_path)
    sql, hodnoty, zvysok = store.index.where(parse_query("strategy=ibs rrRatio>=5"))
    assert zvysok == [("rrRatio", ">=", "5")] and "strategy" in sql
    assert [r["params"]["rrRatio"] for r in store.search("strategy=ibs rrRatio>=5")] == [9.0, 7.0, 5.0]


# --------------------------------------------------------------------------- #
# disk je pravda
# --------------------------------------------------------------------------- #


def test_pribudnuty_zmazany_a_prepisany_beh_sa_do_indexu_dostanu(tmp_path: Path):
    store = _store(tmp_path, 3)
    assert store.page("", 0, 50)[0] == 3

    store.save(_record(4), trades=[], log="")                       # cez sklad
    assert store.page("", 0, 50)[0] == 4

    cudzi = _record(5)                                              # cudzí proces, bez skladu
    (store.root / cudzi["id"]).mkdir()
    (store.root / cudzi["id"] / "run.json").write_text(json.dumps(cudzi), encoding="utf-8")
    assert store.page("", 0, 50)[0] == 5                            # nový adresár sa nájde hneď

    cudzi["note"] = "prepisane cudzim procesom"                     # prepis existujúceho
    (store.root / cudzi["id"] / "run.json").write_text(json.dumps(cudzi), encoding="utf-8")
    store.index.sync(force=True)
    assert store.page("note~prepisane", 0, 50)[0] == 1

    assert store.delete(cudzi["id"]) and store.page("", 0, 50)[0] == 4
    import shutil

    shutil.rmtree(store.root / "20260901-120001-aaaa01")            # zmazanie mimo skladu
    assert store.page("", 0, 50)[0] == 3


def test_rozbity_run_json_nezhodi_zoznam(tmp_path: Path):
    store = _store(tmp_path, 3)
    (store.root / "20260902-120002-aaaa02" / "run.json").write_text("{nie json", encoding="utf-8")
    store.index.sync(force=True)
    assert store.page("", 0, 50)[0] == 2 and len(store._scan()) == 2


def test_index_sa_da_kedykolvek_zahodit_a_postavi_sa_znova(tmp_path: Path):
    store = _store(tmp_path, 3)
    assert store.index.path.exists()
    store.index.close()
    for p in store.index.path.parent.glob("runs.sqlite3*"):
        p.unlink()
    assert store.page("", 0, 50)[0] == 3 and store.index.path.exists()


def test_ina_verzia_schemy_postavi_index_odznova(tmp_path: Path):
    store = _store(tmp_path, 3)
    store.index.close()
    with sqlite3.connect(store.index.path) as conn:
        conn.execute("UPDATE meta SET v = '0' WHERE k = 'schema'")
        conn.execute("DELETE FROM runs")
    assert store.page("", 0, 50)[0] == 3          # stará tabuľka zahodená, behy prečítané nanovo


def test_ked_index_nefunguje_cita_sa_z_suborov(tmp_path: Path):
    store = _store(tmp_path, 4)
    store.index.close()
    store.index.ok = False                        # napr. len na čítanie namontovaný disk
    assert store.page("strategy=ibs", 0, 50)[0] == 2
    assert len(store.all()) == 4 and len(store.search("pnl>0")) == 1


def test_cela_historia_sa_v_pamati_nedrzi(tmp_path: Path):
    """Cache celých záznamov je ohraničená — kedysi rástla do celej histórie (24 GB)."""
    from tester.webapp import store as store_mod

    store = _store(tmp_path, 9)
    for _ in range(3):
        for rec in store.all():
            store.get(rec["id"])
    assert len(store._cache) <= store_mod.CACHE_RUNS
    store_mod.CACHE_RUNS, povodne = 3, store_mod.CACHE_RUNS
    try:
        store._cache.clear()
        for rec in store.all():
            store.get(rec["id"])
        assert len(store._cache) == 3
    finally:
        store_mod.CACHE_RUNS = povodne


def test_stary_kluc_strategie_v_historii_patri_premenovanej(tmp_path: Path):
    """Beh uložený ako `ibsninja` (pred premenovaním na `ibsnet`) sa nájde pod novým kľúčom —
    v zozname aj v indexe rovnako, disk sa nemení."""
    from tester.webapp.store import strategy_of

    store = _store(tmp_path, 2)
    rec = _record(3)
    rec["settings"]["strategy"] = "ibsninja"
    store.save(rec, trades=[], log="")
    zaznam = store.get(rec["id"])
    assert strategy_of(zaznam) == "ibsnet"
    ids = {r["id"] for r in store.all() if strategy_of(r) == "ibsnet"}
    assert ids == {rec["id"]}
    na_disku = json.loads((tmp_path / "runs" / rec["id"] / "run.json").read_text(encoding="utf-8"))
    assert na_disku["settings"]["strategy"] == "ibsninja"
