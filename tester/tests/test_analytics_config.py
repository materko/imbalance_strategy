"""Z akej konfigurácie tie obchody sú.

Analytika, prop výzva aj meranie počítajú nad **zliatymi** obchodmi z viacerých behov.
Kým je to tá istá konfigurácia na rôznych oknách alebo trhoch, je to v poriadku. Keď nie,
zlieva sa dokopy niekoľko rôznych stratégií a výsledok nehovorí o žiadnej z nich — presne
tak vznikli neplatné čísla v REZIM_filtre_btcusdt_2026-09-10.md.
"""

from __future__ import annotations

import pytest

from tester import analytics as an


def beh(run_id: str, *, profil: str = "profil_a.json", **params):
    zaklad = {"rrRatio": 5.0, "minSlDistance": 0.2, "tradeDirection": "Long only"}
    return {"id": run_id, "status": "done",
            "settings": {"profile": profil, "pair": "BTC/USDT:USDT", "timeframe": "3m"},
            "params": {**zaklad, **params}}


def test_rovnaka_konfiguracia_na_roznych_oknach_je_v_poriadku():
    """Presne na toto sa behy zlievajú — okná a trhy sa za rozdiel nepovažujú."""
    c = an.config_spread([beh("r1"), beh("r2"), beh("r3")])

    assert c["severity"] == "ok"
    assert not c["mixed"]
    assert c["differing"] == {}
    assert "tú istú konfiguráciu" in c["note"]


def test_rozne_profily_su_chyba():
    c = an.config_spread([beh("r1", profil="a.json"),
                          beh("r2", profil="b.json", rrRatio=3.0)])

    assert c["severity"] == "chyba"
    assert "NIE SÚ jedna konfigurácia" in c["note"]
    assert "rrRatio" in c["differing"]


def test_jeden_profil_s_inymi_cislami_je_len_pozor():
    """`--set` alebo prepočet prahov na ATR v matici — zvyčajne zámer, nie chyba."""
    c = an.config_spread([beh("r1", rrRatio=4.0), beh("r2", rrRatio=6.0)])

    assert c["severity"] == "pozor"
    assert c["differing"]["rrRatio"] == [4.0, 6.0]
    assert "profilu profil_a.json" in c["note"]


def test_jeden_beh_nema_s_cim_porovnavat():
    c = an.config_spread([beh("r1")])

    assert c["severity"] == "ok"
    assert c["differing"] == {}


def test_velkostne_polia_sa_porovnaju_aj_ked_su_slovniky():
    """Prahy z matice sú `{"value","unit"}`, nie holé čísla."""
    c = an.config_spread([beh("r1", minImbSizePoints={"value": 0.028, "unit": "atr"}),
                          beh("r2", minImbSizePoints={"value": 0.112, "unit": "atr"})])

    assert c["severity"] == "pozor"
    assert len(c["differing"]["minImbSizePoints"]) == 2


def test_rozne_typy_v_jednom_parametri_nepadnu():
    """Holé číslo v jednom behu a slovník v druhom sa porovnať musí, nie spadnúť."""
    c = an.config_spread([beh("r1", minImbSizePoints=2.5),
                          beh("r2", minImbSizePoints={"value": 0.028, "unit": "atr"})])

    assert c["mixed"]


def test_vymenuje_sa_najviac_par_parametrov():
    """Zoznam dvadsiatich rozdielov nikto nečíta."""
    a = beh("r1", **{f"p{i}": i for i in range(20)})
    b = beh("r2", **{f"p{i}": i + 1 for i in range(20)})
    c = an.config_spread([a, b])

    assert len(c["differing"]) <= an.MAX_DIFFS
    assert c["severity"] == "pozor"


def test_bez_behov_sa_nic_netvrdi():
    c = an.config_spread([])

    assert c["severity"] == "ok"
    assert c["note"] == ""
