"""Okolie víťaza hyperoptu — plató, alebo osamelá špička?

Hyperopt vráti jedno číslo a to číslo nehovorí nič o tom, či je stredom niečoho, alebo
náhodnou dierou v šume. Testy strážia dve veci: že susedia vzniknú správne (vždy sa mení
len jeden parameter a nikdy sa nevyjde z rozsahu) a že verdikt rozlišuje plochu od hrotu
podľa **rozptylu susedov voči intervalu víťaza** — nie podľa šírky intervalu samotného,
čo bola prvá, nefunkčná verzia.
"""

from __future__ import annotations

import pytest

from tester import plateau as pl


def zaznam(be: float | None, *, param="rrRatio", value=4.0, step=1, trades=100,
           status="done"):
    """Beh suseda v tvare, aký ukladá `RunStore`."""
    return {
        "id": f"x-{param}-{value}", "status": status,
        "settings": {"plateau": {"id": "h1", "param": param, "value": value, "step": step}},
        "result": {"break_even_pct": be, "trades": trades},
    }


def vitaz(be: float = 0.10, trades: int = 100):
    return {"id": "w", "status": "done", "settings": {}, "result": {"break_even_pct": be,
                                                                    "trades": trades}}


# --------------------------------------------------------------------------- #
# susedia
# --------------------------------------------------------------------------- #


def test_meni_sa_vzdy_len_jeden_parameter():
    """Keby sa hýbali všetky naraz, nevedelo by sa, ktorý z nich výsledok drží."""
    sus = pl.neighbours({"rrRatio": "2:8:0.5", "slLookback": "5:40:1"},
                        {"rrRatio": 4.5, "slLookback": 20})
    mena = {n.param for n in sus}
    assert mena == {"rrRatio", "slLookback"}
    assert len(sus) == 8                       # dva parametre po štyroch krokoch
    assert all(isinstance(n.value, (int, float)) for n in sus)


def test_hodnoty_mimo_rozsahu_vypadnu():
    """Víťaz na okraji rozsahu má susedov len na jednej strane — config by iné neprijal."""
    sus = pl.neighbours({"slLookback": "5:40:1"}, {"slLookback": 40})
    assert [n.value for n in sus] == [38, 39]

    sus = pl.neighbours({"rrRatio": "2:8:0.5"}, {"rrRatio": 2.0})
    assert sorted(n.value for n in sus) == [2.5, 3.0]


def test_celociselne_pole_ostane_cele():
    sus = pl.neighbours({"slLookback": "5:40:1"}, {"slLookback": 20})
    assert all(isinstance(n.value, int) for n in sus)


def test_prepinac_ma_za_susedov_ostatne_moznosti():
    """Krok pri prepínači nedáva zmysel — susedom je druhá možnosť."""
    sus = pl.neighbours({"useStructureFilter": "false,true"}, {"useStructureFilter": True})
    assert [(n.param, n.value) for n in sus] == [("useStructureFilter", False)]


def test_bez_kroku_v_plane_sa_krok_odvodi_z_rozsahu():
    sus = pl.neighbours({"rrRatio": "2,8"}, {"rrRatio": 5.0})
    assert sus                                  # zoznam dvoch hodnôt -> susedia sú tie hodnoty


def test_parameter_ktory_nie_je_vo_vitazovi_sa_preskoci():
    assert pl.neighbours({"rrRatio": "2:8:0.5"}, {"slLookback": 20}) == []


# --------------------------------------------------------------------------- #
# verdikt
# --------------------------------------------------------------------------- #


def test_tesne_okolie_je_plato():
    """Toto je ten prípad, ktorý prvá verzia hlásila ako „málo dát"."""
    susedia = [zaznam(be) for be in (0.095, 0.098, 0.102, 0.105)]
    a = pl.assess(vitaz(0.10), susedia, ci=(0.02, 0.18))

    assert a.spread == pytest.approx(0.01, abs=1e-6)
    assert a.spread_ratio == pytest.approx(0.0625, abs=1e-3)
    assert "PLATO" in a.verdict


def test_susedia_pod_intervalom_su_spicka():
    susedia = [zaznam(be) for be in (-0.05, -0.02, 0.10, -0.04)]
    a = pl.assess(vitaz(0.10), susedia, ci=(0.02, 0.18))
    assert "SPICKA" in a.verdict


def test_ked_spadne_len_cast_susedov_je_to_nejasne():
    susedia = [zaznam(0.10), zaznam(0.11), zaznam(0.09), zaznam(-0.05, param="slLookback")]
    a = pl.assess(vitaz(0.10), susedia, ci=(0.02, 0.18))
    assert "NEJASNE" in a.verdict and "slLookback" in a.verdict


def test_siroke_okolie_nie_je_ani_plato_ani_spicka():
    """Susedia držia, ale líšia sa medzi sebou skoro ako celý interval."""
    susedia = [zaznam(be) for be in (0.03, 0.07, 0.14, 0.17)]
    a = pl.assess(vitaz(0.10), susedia, ci=(0.02, 0.18))
    assert "SIROKE OKOLIE" in a.verdict


def test_malo_obchodov_povie_ze_je_ich_malo():
    susedia = [zaznam(0.10, trades=5), zaznam(0.11, trades=5)]
    a = pl.assess(vitaz(0.10, trades=5), susedia, ci=(0.02, 0.18), min_trades=10)
    assert "MALO DAT" in a.verdict


def test_jeden_sused_na_zaver_nestaci():
    a = pl.assess(vitaz(0.10), [zaznam(0.10)], ci=(0.02, 0.18))
    assert "menej nez dvaja" in a.verdict


def test_bez_intervalu_sa_nic_netvrdi():
    susedia = [zaznam(0.10), zaznam(0.11)]
    a = pl.assess(vitaz(0.10), susedia, ci=(None, None))
    assert "len na pozretie" in a.verdict


def test_vypis_je_ascii_kvoli_konzole_na_windows():
    a = pl.assess(vitaz(0.10), [zaznam(0.10), zaznam(0.11)], ci=(0.02, 0.18))
    assert pl.table(a).encode("ascii", "replace")
