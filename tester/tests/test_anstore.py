"""História analytiky — čo sa uloží, čo nie a prečo per stratégia.

Kľúčové je, že sa ukladá **záver, nie obchody**: tie ostávajú v behoch, na ktoré sa
záznam odkazuje. Keby sa kopírovali sem, tá istá vec by bola v repozitári dvakrát.
"""

from __future__ import annotations

import json

import pytest

from tester.webapp.anstore import AnalyticsStore


def report(strategy: str = "ibs", **kw):
    zaklad = {
        "strategy": strategy,
        "headline": "Najhorsia skupina je 'proti trendu'.",
        "trades": 140,
        "break_even_pct": 0.114,
        "winrate": 35.0,
        "pairs": ["BTC/USDT:USDT"],
        "runs": [{"id": "r1", "pair": "BTC/USDT:USDT"}, {"id": "r2", "pair": "BTC/USDT:USDT"}],
        "splits": [{"title": "S trendom", "buckets": [{"label": "proti", "trades": 41}]}],
    }
    return {**zaklad, **kw}


@pytest.fixture
def store(tmp_path):
    return AnalyticsStore(tmp_path)


def test_ulozi_sa_zaver_a_odkaz_na_behy(store):
    hlavicka = store.save(report(), strategy="ibs", note="skúška")

    z = store.get(hlavicka["id"])
    assert z["run_ids"] == ["r1", "r2"]
    assert z["note"] == "skúška"
    assert z["report"]["splits"]                      # rozdelenia ostavaju
    assert z["trades"] == 140 and z["pairs"] == ["BTC/USDT:USDT"]
    assert z["strategy"] == "ibs"


def test_zoznam_je_per_strategia(store):
    store.save(report("ibs"), strategy="ibs")
    store.save(report("demo_breakout"), strategy="demo_breakout")

    assert [x["strategy"] for x in store.list("ibs")] == ["ibs"]
    assert [x["strategy"] for x in store.list("demo_breakout")] == ["demo_breakout"]
    assert len(store.list()) == 2                     # bez filtra su obe


def test_zoznam_je_od_najnovsej(store):
    prva = store.save(report(), strategy="ibs", note="prvá")
    druha = store.save(report(), strategy="ibs", note="druhá")

    ids = [x["id"] for x in store.list("ibs")]
    assert ids.index(druha["id"]) < ids.index(prva["id"])


def test_hlavicka_v_zozname_nenesie_cely_report(store):
    store.save(report(), strategy="ibs")
    polozka = store.list("ibs")[0]

    assert "report" not in polozka
    assert polozka["runs"] == 2                       # v zozname je pocet, nie zoznam
    assert polozka["break_even_pct"] == 0.114


def test_velke_pole_sa_do_historie_neuklada(store):
    """Histogramy a krivky sú desiatky kilobajtov a to, čo z nich plynie, je vo verdikte."""
    r = report(nulltest={"nulls": {"anytime": {"sigma": 4.2, "histogram": [1] * 40,
                                               "sample": [0.1] * 600}}},
               portfolio={"verdict": "ok", "curve": [[1, 2]] * 5000})
    z = store.get(store.save(r, strategy="ibs")["id"])

    assert "histogram" not in z["report"]["nulltest"]["nulls"]["anytime"]
    assert "sample" not in z["report"]["nulltest"]["nulls"]["anytime"]
    assert z["report"]["nulltest"]["nulls"]["anytime"]["sigma"] == 4.2
    assert "curve" not in z["report"]["portfolio"]
    assert z["report"]["portfolio"]["verdict"] == "ok"


def test_zmazanie(store):
    an_id = store.save(report(), strategy="ibs")["id"]

    assert store.delete(an_id)
    assert store.get(an_id) is None
    assert not store.delete(an_id)


def test_neznamy_zaznam_je_None(store):
    assert store.get("neexistuje") is None


def test_prazdny_sklad_nepadne(store):
    assert store.list("ibs") == []


# --------------------------------------------------------------------------- #
# webapp
# --------------------------------------------------------------------------- #


@pytest.fixture
def klient(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import tester.webapp.app as app_mod

    monkeypatch.setattr(app_mod, "AnalyticsStore", lambda: AnalyticsStore(tmp_path))
    return TestClient(app_mod.create_app())


def test_endpoint_ulozi_a_vrati_per_strategiu(klient):
    r = klient.post("/api/analytics/history", json={"report": report(), "note": "test"})
    assert r.status_code == 200
    an_id = r.json()["id"]

    zoznam = klient.get("/api/analytics/history?strategy=ibs").json()["items"]
    assert [x["id"] for x in zoznam] == [an_id]
    assert klient.get("/api/analytics/history?strategy=demo_breakout").json()["items"] == []

    detail = klient.get(f"/api/analytics/history/{an_id}").json()
    assert detail["report"]["headline"]


def test_endpoint_odmietne_report_bez_behov(klient):
    r = klient.post("/api/analytics/history", json={"report": report(runs=[])})

    assert r.status_code == 422


def test_endpoint_odmietne_neznamu_strategiu(klient):
    r = klient.post("/api/analytics/history", json={"report": report("neexistuje")})

    assert r.status_code == 422


def test_neznamy_zaznam_je_404(klient):
    assert klient.get("/api/analytics/history/neexistuje").status_code == 404
    assert klient.delete("/api/analytics/history/neexistuje").status_code == 404


# --------------------------------------------------------------------------- #
# posudok od AI
# --------------------------------------------------------------------------- #


def test_posudok_sa_ulozi_a_nesie_odtlacok_cisel(store):
    an_id = store.save(report(), strategy="ibs")["id"]

    out = store.set_posudok(an_id, "  Toto je posudok.  ", user="tester")

    z = store.get(an_id)
    assert z["posudok"] == "Toto je posudok."
    assert z["posudok_stamp"] == z["numbers"]
    assert z["posudok_user"] == "tester"
    assert out["has_posudok"] and not out["posudok_stale"]


def test_posudok_k_inym_cislam_je_oznaceny_za_stary(store):
    """Nie je nepravdivý, len starý — a o mesiac to musí byť vidieť."""
    an_id = store.save(report(), strategy="ibs")["id"]
    store.set_posudok(an_id, "posudok")

    # čísla sa prepočítali: iná vzorka, ten istý záznam
    z = store.get(an_id)
    z["numbers"] = "inecislo"
    store._path(an_id).write_text(json.dumps(z, ensure_ascii=False), encoding="utf-8")

    assert store.list("ibs")[0]["posudok_stale"] is True


def test_bez_posudku_sa_zaznam_netvari_ze_ho_ma(store):
    store.save(report(), strategy="ibs")

    assert store.list("ibs")[0]["has_posudok"] is False


def test_posudok_k_neznamemu_zaznamu_je_None(store):
    assert store.set_posudok("neexistuje", "text") is None


def test_zadanie_nesie_cisla_aj_otazky():
    from tester.webapp import anstore

    text = anstore.zadanie(report())

    assert "140" in text                       # pocet obchodov
    assert "0.114" in text                     # break-even
    for i in range(1, len(anstore.POSUDOK_OTAZKY) + 1):
        assert f"{i}." in text


def test_zadanie_zhrnie_aj_verdikty_ostatnych_testov():
    """Posudok má vidieť aj to, čo hovorí decay, náhoda a syntetický trh."""
    from tester.webapp import anstore

    text = anstore.zadanie(report(decay={"verdict": "DRZI"},
                                  synthetic={"verdict": "ENGINE OK: ..."}))

    assert "DRZI" in text
    assert "ENGINE OK" in text


def test_endpoint_ulozi_posudok_a_vrati_zadanie(klient):
    an_id = klient.post("/api/analytics/history", json={"report": report()}).json()["id"]

    z = klient.get(f"/api/analytics/history/{an_id}/zadanie").json()
    assert z["questions"] and "140" in z["text"]

    out = klient.post(f"/api/analytics/history/{an_id}/posudok",
                      json={"text": "posudok od AI"}).json()
    assert out["has_posudok"]
    assert klient.get(f"/api/analytics/history/{an_id}").json()["posudok"] == "posudok od AI"


def test_posudok_k_neznamej_analytike_je_404(klient):
    assert klient.post("/api/analytics/history/nic/posudok", json={"text": "x"}).status_code == 404
    assert klient.get("/api/analytics/history/nic/zadanie").status_code == 404
