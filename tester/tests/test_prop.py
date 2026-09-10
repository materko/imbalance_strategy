"""Prop výzva — testy nad obchodmi, ktorých priebeh poznáme dopredu.

Zmyslom nie je, či vyjde pekné číslo, ale či **pravidlá robia to, čo tvrdia**: denný
limit má zabiť účet práve vtedy, keď sa prekročí v jednom dni; trailing z vrcholu má byť
prísnejší než statický; pravidlo konzistencie má jeden veľký deň neuznať. Zle napísané
pravidlo tu vyrobí optimistické číslo a to je horšie než žiadne.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from tester import prop

ZACIATOK = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
UCET = 100_000.0


def obchod(den: int, *, r: float, poradie: int = 0):
    """Obchod v `den`-tý deň, ktorý pri riziku 1 % zarobí `r` násobok rizika.

    Stop je 1 % ceny, takže pri riziku 1 % zo zostatku je strata presne 1 % účtu
    a zisk `r` %.
    """
    cas = ZACIATOK + timedelta(days=den, minutes=poradie)
    return {"open_date": cas.isoformat(),
            "close_date": (cas + timedelta(minutes=1)).isoformat(),
            "open_rate": 100.0, "close_rate": 100.0 + r, "amount": 1.0,
            "is_short": False, "profit_abs": r,
            "_sl_pct": 1.0, "stop_loss_abs": 99.0, "initial_stop_loss_abs": 99.0}


def pravidla(**kw):
    zaklad = dict(name="test", account=UCET, targets=(5.0,), max_daily_loss_pct=5.0,
                  max_loss_pct=10.0, min_days=0, cost=100.0, payout_pct=100.0,
                  refund=False, horizon_days=0)
    return prop.Rules(**{**zaklad, **kw})


def pokus(trades, rules, risk=1.0):
    return prop.attempt(prop._sorted(trades), rules, risk_pct=risk)


# --------------------------------------------------------------------------- #
# cieľ
# --------------------------------------------------------------------------- #


def test_ciel_sa_da_splnit_a_pokus_prejde():
    t = [obchod(i, r=2.0) for i in range(3)]          # 3x +2 % = +6 % > 5 %
    v = pokus(t, pravidla())

    assert v.passed
    assert v.reason == "cieľ"
    assert v.profit > UCET * 0.05


def test_minimum_dni_drzi_pokus_otvoreny():
    """Cieľ padne prvý deň, ale firma chce štyri — pokus musí pokračovať."""
    t = [obchod(0, r=6.0)] + [obchod(i, r=0.1, poradie=i) for i in range(1, 4)]

    assert pokus(t, pravidla(min_days=0)).days == 0      # bez minima hned prvy den
    v = pokus(t, pravidla(min_days=4))
    assert v.passed and v.days == 3                      # s minimom az stvrty den


def test_dve_fazy_su_tazsie_nez_jedna():
    """Každá fáza začína s čerstvým zostatkom — zisk sa neprenáša."""
    t = [obchod(i, r=2.0) for i in range(4)]          # staci na jednu fazu, nie na dve

    assert pokus(t, pravidla(targets=(5.0,))).passed
    assert not pokus(t, pravidla(targets=(5.0, 5.0))).passed


# --------------------------------------------------------------------------- #
# limity
# --------------------------------------------------------------------------- #


def test_denny_limit_zabije_ucet_v_ten_isty_den():
    t = [obchod(0, r=-2.0, poradie=i) for i in range(4)]   # -8 % za jeden den

    v = pokus(t, pravidla(max_daily_loss_pct=5.0))
    assert v.outcome == "spálený"
    assert v.reason == "denný limit"


def test_ta_ista_strata_rozlozena_do_dni_denny_limit_neprekroci():
    """Denný limit je o zhlukovaní v čase — to je celý rozdiel oproti celkovému."""
    t = [obchod(i, r=-2.0) for i in range(4)]             # -2 % denne, spolu -8 %

    v = pokus(t, pravidla(max_daily_loss_pct=5.0, max_loss_pct=10.0))
    assert v.reason != "denný limit"


def test_nulovy_denny_limit_znamena_ze_firma_ziadny_nema():
    """Toto je ľahké pokaziť: 0 nesmie znamenať „zabi na prvej strate“."""
    t = [obchod(0, r=-2.0, poradie=i) for i in range(3)]

    assert pokus(t, pravidla(max_daily_loss_pct=0.0)).reason != "denný limit"


def test_celkovy_limit_zabije_aj_ked_denny_nie():
    t = [obchod(i, r=-2.0) for i in range(8)]             # -2 % denne, spolu -16 %

    v = pokus(t, pravidla(max_daily_loss_pct=5.0, max_loss_pct=10.0))
    assert v.outcome == "spálený"
    assert v.reason == "celkový limit"


# --------------------------------------------------------------------------- #
# trailing: od čoho sa počíta celkový limit
# --------------------------------------------------------------------------- #


def test_trailing_z_vrcholu_je_prisnejsi_nez_staticky():
    """Účet vyrastie a potom padá: statický limit to prežije, trailing nie."""
    t = [obchod(0, r=8.0)] + [obchod(i, r=-2.0) for i in range(1, 6)]   # +8 %, potom -10 %

    staticky = pokus(t, pravidla(max_loss_pct=10.0, trailing="nie", targets=(50.0,)))
    trailing = pokus(t, pravidla(max_loss_pct=10.0, trailing="vrchol", targets=(50.0,)))

    assert staticky.outcome != "spálený"
    assert trailing.outcome == "spálený"


def test_trailing_z_konca_dna_nevidi_vrchol_vnutri_dna():
    """Rozdiel medzi EOD a intraday trailingom: vrchol, ktorý si nezrealizoval.

    V jednom dni sa vyletí o +8 % a hneď sa to vráti — intraday trailing si ten vrchol
    zapamätá, koncodenný nie.
    """
    t = [obchod(0, r=8.0, poradie=0), obchod(0, r=-8.0, poradie=1)]
    t += [obchod(i, r=-2.0) for i in range(1, 3)]

    intraday = pokus(t, pravidla(max_loss_pct=10.0, trailing="vrchol", targets=(50.0,)))
    koncodenny = pokus(t, pravidla(max_loss_pct=10.0, trailing="koniec_dna", targets=(50.0,)))

    assert intraday.outcome == "spálený"
    assert koncodenny.outcome != "spálený"


def test_zamrznuty_trailing_prestane_stupat_na_pociatocnom_zostatku():
    """Apex: hranica sa zastaví, keď dorovná počiatočný zostatok."""
    t = [obchod(0, r=20.0)] + [obchod(i, r=-3.0) for i in range(1, 6)]   # +20 %, potom -15 %

    volny = pokus(t, pravidla(max_loss_pct=10.0, trailing="vrchol", targets=(50.0,)))
    zamrznuty = pokus(t, pravidla(max_loss_pct=10.0, trailing="vrchol",
                                  trailing_freeze_at_start=True, targets=(50.0,)))

    assert volny.outcome == "spálený"          # hranica vysla az na 110 %
    assert zamrznuty.outcome != "spálený"      # hranica sa zastavila na 90 %


# --------------------------------------------------------------------------- #
# konzistencia
# --------------------------------------------------------------------------- #


def test_jeden_velky_den_ciel_nezavrie():
    """Pravidlo, na ktoré algotrader najčastejšie narazí."""
    t = [obchod(0, r=6.0)] + [obchod(i, r=0.1, poradie=i) for i in range(1, 4)]

    bez = pokus(t, pravidla(targets=(5.0,), min_days=3))
    s_pravidlom = pokus(t, pravidla(targets=(5.0,), min_days=3, max_day_share_pct=40.0))

    assert bez.passed
    assert not s_pravidlom.passed


def test_rozlozeny_zisk_pravidlo_konzistencie_prejde():
    t = [obchod(i, r=2.0) for i in range(4)]

    assert pokus(t, pravidla(targets=(5.0,), max_day_share_pct=40.0)).passed


# --------------------------------------------------------------------------- #
# celá simulácia
# --------------------------------------------------------------------------- #


def test_simulacia_zacina_na_kazdom_obchode():
    t = [obchod(i, r=1.0) for i in range(60)]
    r = prop.simulate(t, pravidla(), risk_pct=1.0)

    assert r.attempts == 60
    assert r.passed + r.burned + r.unfinished == r.attempts


def test_nedobehnute_pokusy_sa_pocitaju_ako_neuspech():
    """Zaplatená výzva bez výplaty je strata, nech skončila akokoľvek."""
    t = [obchod(i, r=0.01) for i in range(60)]          # nikdy nedosiahne ciel
    r = prop.simulate(t, pravidla(), risk_pct=1.0)

    assert r.passed == 0
    assert r.p_pass == 0.0
    assert r.ev == -r.rules.cost


def test_suvislé_pozicie_sa_zmeraju_a_ohlasia():
    t = [obchod(0, r=1.0, poradie=0), obchod(0, r=1.0, poradie=0)]   # rovnaky cas

    assert prop.max_concurrent(t) == 2
    assert prop.max_concurrent([obchod(0, r=1.0), obchod(5, r=1.0)]) == 1


def test_malo_obchodov_dostane_verdikt_malo_dat():
    r = prop.simulate([obchod(i, r=1.0) for i in range(10)], pravidla(), risk_pct=1.0)

    assert r.verdict.startswith("MALO DAT")


# --------------------------------------------------------------------------- #
# predlohy firiem
# --------------------------------------------------------------------------- #


def test_kazda_predloha_povie_odkial_su_cisla():
    """Pravidlá firiem sa menia — bez zdroja sa nedá zistiť, čo treba overiť."""
    for meno, r in prop.PRESETS.items():
        assert r.source, meno
        assert "2026-" in r.source, meno
        assert r.targets, meno


def test_predlohy_sa_daju_prepisat():
    upravene = replace(prop.PRESETS["ftmo2"], max_daily_loss_pct=2.0)

    assert upravene.max_daily_loss_pct == 2.0
    assert prop.PRESETS["ftmo2"].max_daily_loss_pct == 5.0     # original ostal


def test_neznamy_trailing_sa_neda_zadat():
    with pytest.raises(ValueError, match="trailing"):
        pravidla(trailing="hocico")


def test_bez_faz_sa_pravidla_nedaju_vyrobit():
    with pytest.raises(ValueError, match="targets"):
        pravidla(targets=())


# --------------------------------------------------------------------------- #
# webapp
# --------------------------------------------------------------------------- #


@pytest.fixture
def klient():
    fastapi = pytest.importorskip("fastapi")          # noqa: F841
    from fastapi.testclient import TestClient

    from tester.webapp.app import create_app

    return TestClient(create_app())


def test_meta_da_predlohy_aj_so_zdrojom(klient):
    m = klient.get("/api/prop/meta").json()

    assert set(prop.PRESETS) <= set(m["presets"])
    for meno, r in m["presets"].items():
        assert r["source"], meno
        assert isinstance(r["targets"], list)
    assert "nie" in m["trailing"] and "koniec_dna" in m["trailing"]


def test_nezname_pravidla_endpoint_odmietne(klient):
    r = klient.post("/api/prop", json={"rules": "neexistuje"})

    assert r.status_code == 422
    assert "neexistuje" in r.json()["detail"]


def test_nezmyselne_trailing_endpoint_odmietne(klient):
    r = klient.post("/api/prop", json={"rules": "ftmo2", "trailing": "hocico"})

    assert r.status_code == 422


def test_bez_behov_endpoint_povie_ze_nie_su(klient):
    r = klient.post("/api/prop", json={"rules": "ftmo2", "q": "note~urcite-nic-take-nie-je"})

    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# viac predlôh naraz
# --------------------------------------------------------------------------- #


def test_rules_for_vezme_zoznam_all_aj_custom():
    vsetky = prop.rules_for(["all"])
    assert [k for k, _ in vsetky] == list(prop.PRESETS)

    dve = prop.rules_for(["ftmo2,apex100", "custom"], {"cost": 100.0})
    assert [k for k, _ in dve] == ["ftmo2", "apex100", "custom"]
    # Pri viacerých firmách sa ich pravidlá neprepisujú; `custom` prepisy dostane vždy.
    assert dict(dve)["ftmo2"].cost == prop.PRESETS["ftmo2"].cost
    assert dict(dve)["custom"].cost == 100.0

    jedna = prop.rules_for(["ftmo2"], {"cost": 100.0})
    assert dict(jedna)["ftmo2"].cost == 100.0        # jediná vybraná: polia ju upravujú


def test_rules_for_nezname_a_prazdne_odmietne():
    with pytest.raises(ValueError, match="neexistuje"):
        prop.rules_for(["neexistuje"])
    with pytest.raises(ValueError):
        prop.rules_for([""])


def test_porovnanie_predloh_ma_riadok_pre_kazdu():
    obchody = [obchod(d, r=(1.5 if d % 3 else -1.0), poradie=0) for d in range(60)]
    varianty = [(k, prop.risk_table(obchody, r, risks=(1.0,))) for k, r in prop.rules_for(["ftmo2,ftmo1"])]
    text = prop.compare(varianty)
    assert "ftmo2" in text and "ftmo1" in text
    text.encode("ascii", "replace")


def test_endpoint_prijme_zoznam_predloh(klient):
    r = klient.post("/api/prop", json={"rules": ["ftmo2", "neexistuje"], "q": "note~nic"})

    assert r.status_code == 422
    assert "neexistuje" in r.json()["detail"]
