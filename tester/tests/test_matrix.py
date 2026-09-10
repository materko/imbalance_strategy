"""Matica trhov — a hlavne prepočet prahov, bez ktorého by celá tabuľka klamala.

Prah v absolútnych cenových bodoch znamená na každom trhu inú vec: `minImbSizePoints = 2,5`
je na BTC (cena 110 000) prakticky nula, na EURUSD (cena 1,08) podmienka, ktorá nikdy
nenastane. Bez prepočtu na `atr` by tabuľka nehovorila „na forexe to nefunguje", ale
„profil je tam nezmysel" — a to dvoje sa v nej nedá rozlíšiť. Testy strážia práve to.
"""

from __future__ import annotations

import pytest

pytest.importorskip("freqtrade")

from tester import matrix as mx
from tradebot.strategies import get_spec

IBS = get_spec("ibs")


def zaznam(pair, timeframe="3m", *, be=0.1, trades=50, status="done"):
    """Beh v tvare, aký ukladá `RunStore`, so značkou matice."""
    return {
        "id": f"x-{pair}-{timeframe}", "status": status,
        "settings": {"pair": pair, "timeframe": timeframe, "timerange": "20250904-20260904",
                     "matrix": {"id": "m1", "pair": pair, "timeframe": timeframe,
                                "goal": "break_even"}},
        "result": {"break_even_pct": be, "trades": trades, "pnl_pct": be * 100,
                   "winrate": 50.0, "max_drawdown_pct": 5.0},
    }


# --------------------------------------------------------------------------- #
# prepočet prahov
# --------------------------------------------------------------------------- #


def test_hole_cislo_znamena_predvolenu_jednotku_pola():
    """Regresia: prepočet hľadal len slovníky `{"value":…,"unit":…}`.

    V profile aj vo formulári je `minImbSizePoints: 2.5` **bez jednotky** a znamená to
    absolútne cenové body, lebo tak má pole zadefinované `SIZE_FIELDS`. Prvá verzia preto
    na profile z formulára nespravila nič a matica testovala prah 2,5 na EURUSD — osem
    trhov malo nula obchodov a v tabuľke to vyzeralo ako „tu to nefunguje".
    """
    cls = IBS.config_cls
    assert mx._unit_of({"minImbSizePoints": 2.5}, "minImbSizePoints", cls) == "abs"
    assert mx._value_of({"minImbSizePoints": 2.5}, "minImbSizePoints") == 2.5
    # Slovník aj SizeSpec musia fungovať rovnako.
    from tradebot.core.types import SizeSpec

    assert mx._unit_of({"minImbSizePoints": {"value": 1.0, "unit": "atr"}},
                       "minImbSizePoints", cls) == "atr"
    assert mx._unit_of({"minImbSizePoints": SizeSpec(value=1.0, unit="pct")},
                       "minImbSizePoints", cls) == "pct"
    # Pole, ktoré má predvolenú jednotku `pct`, sa za absolútne vydávať nesmie.
    assert mx._unit_of({"minSlDistance": 0.25}, "minSlDistance", cls) == "pct"


def test_prepocet_deli_medianom_atr_referencneho_trhu(monkeypatch):
    monkeypatch.setattr(mx, "median_atr", lambda *a, **k: 100.0)
    params = {"minImbSizePoints": 2.5, "srClusterPoints": 15.0, "minSlDistance": 0.25}

    novy, zmeny = mx.to_relative(params, ref_pair="BTC/USDT:USDT", ref_timeframe="3m")

    assert novy["minImbSizePoints"] == {"value": 0.025, "unit": "atr"}
    assert novy["srClusterPoints"] == {"value": 0.15, "unit": "atr"}
    assert novy["minSlDistance"] == 0.25          # `pct` je už prenositeľné, nechá sa
    assert any("2.5 abs" in z for z in zmeny)


def test_bez_referencnych_sviecok_sa_nic_nezmeni_a_povie_sa_to(monkeypatch):
    """Tichý prepočet zlou mierkou by bol horší než žiadny."""
    monkeypatch.setattr(mx, "median_atr", lambda *a, **k: None)
    params = {"minImbSizePoints": 2.5}

    novy, zmeny = mx.to_relative(params, ref_pair="NIECO/USD", ref_timeframe="3m")

    assert novy == params
    assert zmeny and "nedal" in zmeny[0]


def test_profil_bez_absolutnych_prahov_sa_neprepocitava(monkeypatch):
    monkeypatch.setattr(mx, "median_atr", lambda *a, **k: 100.0)
    params = {"minImbSizePoints": {"value": 0.5, "unit": "atr"}}
    novy, zmeny = mx.to_relative(params, ref_pair="BTC/USDT:USDT", ref_timeframe="3m")
    assert novy == params and zmeny == []


# --------------------------------------------------------------------------- #
# mriežka a spustiteľnosť
# --------------------------------------------------------------------------- #


def test_mriezka_je_po_trhoch_aby_prve_vysledky_pokryli_viac_trhov():
    bunky = mx.expand(["A", "B"], ["3m", "15m"])
    assert [(c.pair, c.timeframe) for c in bunky] == [
        ("A", "3m"), ("A", "15m"), ("B", "3m"), ("B", "15m")]


def test_prazdne_zadanie_je_chyba():
    with pytest.raises(ValueError, match="trh"):
        mx.expand([], ["3m"])
    with pytest.raises(ValueError, match="timeframe"):
        mx.expand(["A"], [])


def test_spot_s_pakou_sa_preskoci_s_dovodom_nie_az_pri_spusteni():
    """Šesť červených buniek bez vysvetlenia je horšie než „preskočené, lebo páka 10"."""
    bunky = mx.expand(["BTC/USDT", "BTC/USDT:USDT"], ["3m"])
    ok, preco = mx.playable(bunky, params={"leverage": 10, "tradeDirection": "Both"})

    assert [c.pair for c in ok] == ["BTC/USDT:USDT"]
    assert "spotový" in preco["BTC/USDT|3m"]


def test_chybajuci_timeframe_sa_preskoci():
    bunky = mx.expand(["BTC/USDT:USDT"], ["7m"])
    ok, preco = mx.playable(bunky)
    assert ok == [] and "7m" in preco["BTC/USDT:USDT|7m"]


# --------------------------------------------------------------------------- #
# tabuľka a verdikt
# --------------------------------------------------------------------------- #


def test_tabulka_ma_trhy_v_riadkoch_a_tf_v_stupcoch_podla_minut():
    zaznamy = [zaznam("A", "15m"), zaznam("A", "3m"), zaznam("B", "3m")]
    tabulka = mx.matrix(zaznamy)

    assert tabulka["timeframes"] == ["3m", "15m"]      # zoradené podľa minút, nie abecedy
    assert set(tabulka["pairs"]) == {"A", "B"}
    assert tabulka["cells"]["A"]["3m"]["value"] == 0.1
    assert mx.table(tabulka).encode("ascii", "replace")   # konzola na Windows


def test_verdikt_odlisi_myslienku_od_vlastnosti_jedneho_paru():
    vsade = [zaznam(p, be=0.1) for p in ("A", "B", "C", "D")]
    assert "MYSLIENKA DRZI" in mx.verdict(vsade)

    len_jeden = [zaznam("A", be=0.2)] + [zaznam(p, be=-0.1) for p in ("B", "C", "D")]
    assert "LEN NA JEDNOM TRHU" in mx.verdict(len_jeden)

    polovica = [zaznam(p, be=0.1) for p in ("A", "B")] + [zaznam(p, be=-0.1) for p in ("C", "D")]
    assert "CIASTOCNE" in mx.verdict(polovica)


def test_bunky_s_malo_obchodmi_verdikt_neovplyvnia():
    """Bunka s dvoma obchodmi nie je zistenie a nesmie rozhodovať o verdikte."""
    zaznamy = [zaznam("A", be=0.1, trades=50), zaznam("B", be=5.0, trades=2)]
    assert "hodnotit neda" not in mx.verdict(zaznamy)
    poradie = mx.rank(zaznamy, min_trades=10)
    mimo = [r for r in poradie if not r["sweep_ok"]]
    assert [r["settings"]["pair"] for r in mimo] == ["B"]


def test_z_jedneho_trhu_sa_zaver_naprieč_trhmi_nerobi():
    """Celý zmysel matice je porovnanie naprieč trhmi — z jedného to nie je porovnanie."""
    zaznamy = [zaznam("A", be=0.1), zaznam("B", status="failed")]
    assert "aspoň tri" in mx.verdict(zaznamy)


# --------------------------------------------------------------------------- #
# mena kótácie
# --------------------------------------------------------------------------- #


def test_fiktivna_burza_dostane_config_podla_meny_kotacie():
    """Regresia: šesť trhov padlo na „No pair in whitelist".

    Freqtrade vyhodí z whitelistu pár, ktorého kótovacia mena nesedí so `stake_currency`
    configu. Naše Dukascopy symboly sú v USD, JPY, EUR aj CAD, takže jeden hotový config
    ich pokryť nemôže — a prepínač na to Freqtrade nemá.
    """
    import json

    from tradebot.core.types import INSTRUMENTS
    from tester import engines

    jpy = engines.stake_config(INSTRUMENTS["jp225_dukascopy"], "tester")
    assert json.loads(jpy.read_text(encoding="utf-8"))["stake_currency"] == "JPY"

    # USD trh nepotrebuje nič generovať — vezme sa hotový config repozitára.
    usd = engines.stake_config(INSTRUMENTS["nas100_dukascopy"], "tester")
    assert usd == engines.freqtrade_config(INSTRUMENTS["nas100_dukascopy"], "tester")


def test_skutocnej_burze_sa_mena_nevymysla():
    """U Binance je mena daná burzou; generovať jej config by bolo klamstvo."""
    from tradebot.core.types import INSTRUMENTS
    from tester import engines

    inst = INSTRUMENTS["btcusdt_binance"]
    assert engines.stake_config(inst, "binance") == engines.freqtrade_config(inst, "binance")


def test_kazda_bunka_matice_dostane_poplatok_svojho_trhu():
    """Matica púšťa jeden profil na cudzích trhoch — poplatok musí ísť s trhom.

    `_prepare` spočíta poplatok raz, z páru profilu. Keby si ho bunky zobrali odtiaľ,
    matica by CFD na kávu účtovala Binance taker 0,05 % a jej PnL aj profit factor by
    boli nezmysel. (Na poradie buniek to vplyv nemá — break-even od poplatku nezávisí —
    ale práve preto by si toho nikto nevšimol.)
    """
    import argparse

    from tester.webapp.cli import _fee_for

    args = argparse.Namespace(fee=None, timeframe="3m", timerange="20240904-20250904")
    krypto = _fee_for(args, "BTC/USDT:USDT")
    cfd = _fee_for(args, "COFFEE/USD")
    assert krypto["fee"] != cfd["fee"], "krypto taker a spread na CFD nemôžu byť to isté číslo"
    assert "Binance" in krypto["fee_note"] and "Binance" not in cfd["fee_note"]
    # a zadaný --fee prebije oboje, aby sa dalo porovnávať s TradingView
    zadany = argparse.Namespace(fee=0.0, timeframe="3m", timerange="20240904-20250904")
    assert _fee_for(zadany, "COFFEE/USD") == {"fee": 0.0, "fee_note": "zadané cez --fee"}
