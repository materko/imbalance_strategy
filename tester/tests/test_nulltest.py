"""Test proti náhode — a hlavne to, či je samotná náhoda nezaujatá.

Celý test stojí a padá na tom, že náhodný vstup so symetrickými pravidlami vyjde v priemere
na nulu. Keby simulácia systematicky zarábala alebo prerábala, posunul by sa referenčný
bod a stratégia by vyzerala lepšie (alebo horšie), než je — a nikto by si toho nevšimol,
lebo výsledok by stále vyzeral ako číslo so sigmou. Prvé testy preto merajú náhodu samu.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tester import nulltest as nt


def rovny_trh(n: int = 20000, start: float = 100.0, krok: float = 0.05, seed: int = 7):
    """Náhodná prechádzka bez driftu — na nej musí náhodný vstup vyjsť na nulu."""
    rng = np.random.default_rng(seed)
    close = start + np.cumsum(rng.normal(0.0, krok, n))
    high = close + abs(rng.normal(0.0, krok, n))
    low = close - abs(rng.normal(0.0, krok, n))
    ts = np.arange(n, dtype=np.int64) * 180_000        # 3m bary
    hodiny = ((ts // 3_600_000) % 24).astype(int)
    return ts, high, low, close, hodiny


def plan(count: int = 40, sl: float = 0.01, rr: float = 2.0, bars: int = 60,
         long_share: float = 1.0):
    return {"count": count, "sl_frac": np.array([sl]), "rr": np.array([rr]),
            "long_share": long_share, "max_bars": bars, "hours": np.arange(24)}


def trade(*, open_rate=100.0, close_rate=101.0, short=False, hour=10, duration=60,
          sl_pct=1.0, rr=2.0, exit_reason="roi"):
    smer = -1.0 if short else 1.0
    return {
        "open_date": f"2025-09-04T{hour:02d}:00:00+00:00",
        "open_rate": open_rate, "close_rate": close_rate, "amount": 1.0,
        "profit_abs": (close_rate - open_rate) * smer, "is_short": short,
        "trade_duration": duration, "exit_reason": exit_reason,
        "_sl_pct": sl_pct, "_rr_planned": rr,
    }


# --------------------------------------------------------------------------- #
# je náhoda nezaujatá?
# --------------------------------------------------------------------------- #


def test_nahodny_vstup_je_nezaujaty():
    """Základ celého testu: náhoda musí byť nezaujatá.

    A pozor na smer: keby náhoda vychádzala **horšie**, než je, posunul by sa referenčný
    bod nadol a edge stratégie by tým vyzeral lepší. Meria sa na piatich rôznych trhoch,
    lebo jedna náhodná prechádzka má vždy nejaký vlastný drift — a ten by sa inak zamenil
    za chybu simulácie (stalo sa: testovací trh klesal o 6,4 % a jednosmerné obchody to
    presne skopírovali).
    """
    priemery = []
    for seed in range(5):
        vzorka = nt.simulate(rovny_trh(seed=seed), plan(count=50, long_share=0.5),
                             iterations=200, seed=3)
        assert len(vzorka) == 200
        priemery.append(float(np.mean(vzorka)))

    priemer = float(np.mean(priemery))
    # SL je 1 % ceny; odchýlka pod stotinu rizika je šum, nie systematická výhoda.
    assert abs(priemer) < 0.01, f"náhoda nie je nezaujatá: {priemer:+.4f} % pri riziku 1 %"


def test_nahoda_dedi_drift_trhu_a_to_je_spravne():
    """Keď trh rástol, náhodné longy na ňom zarobia — a stratégia to musí prekonať.

    Bez toho by „nakúp a drž" vyzeralo ako edge. Test proti náhode preto meria edge
    **nad driftom trhu**, nie nad nulou, a to je tá správna latka.
    """
    trh = rovny_trh(seed=7)              # tento konkrétny trh klesá
    close = trh[3]
    assert close[-1] < close[0]

    longy = float(np.mean(nt.simulate(trh, plan(long_share=1.0), iterations=300, seed=3)))
    shorty = float(np.mean(nt.simulate(trh, plan(long_share=0.0), iterations=300, seed=3)))
    assert longy < 0 < shorty            # klesajúci trh: longy prerábajú, shorty zarábajú


def test_shorty_aj_longy_vychadzaju_rovnako():
    """Asymetria medzi smermi by z jednosmernej stratégie spravila zázrak alebo katastrofu."""
    trh = rovny_trh()
    longy = float(np.mean(nt.simulate(trh, plan(long_share=1.0), iterations=300, seed=2)))
    shorty = float(np.mean(nt.simulate(trh, plan(long_share=0.0), iterations=300, seed=2)))
    assert abs(longy - shorty) < 0.02


def test_pri_zasahu_oboch_v_jednom_bare_sa_pocita_stop():
    """Optimistická voľba by nafúkla náhodu, teda urobila edge lepším, než je."""
    close = np.array([100.0, 100.0, 100.0])
    high = np.array([100.0, 130.0, 100.0])      # v tom istom bare je aj TP…
    low = np.array([100.0, 90.0, 100.0])        # …aj SL
    idx = np.array([0])
    ceny = nt._exits(high, low, close, idx, np.array([1]), np.array([95.0]),
                     np.array([120.0]), max_bars=2)
    assert ceny[0] == pytest.approx(95.0)       # stop, nie take profit


def test_bez_zasahu_sa_vychadza_na_zavere_posledneho_baru():
    close = np.array([100.0, 101.0, 102.0, 103.0])
    high = np.array([100.0, 101.5, 102.5, 103.5])
    low = np.array([99.5, 100.5, 101.5, 102.5])
    ceny = nt._exits(high, low, close, np.array([0]), np.array([1]),
                     np.array([50.0]), np.array([200.0]), max_bars=3)
    assert ceny[0] == pytest.approx(103.0)


# --------------------------------------------------------------------------- #
# čo sa zo skutočných obchodov zachováva
# --------------------------------------------------------------------------- #


def test_plan_zoberie_stop_smer_aj_dlzku_zo_skutocnych_obchodov():
    obchody = [trade(sl_pct=0.5, rr=3.0, duration=90, short=False),
               trade(sl_pct=1.5, rr=2.0, duration=30, short=True)]
    p = nt.plan_from_trades(obchody, minutes=3)

    assert p["count"] == 2
    assert sorted(p["sl_frac"]) == pytest.approx([0.005, 0.015])
    assert sorted(p["rr"]) == pytest.approx([2.0, 3.0])
    assert p["long_share"] == pytest.approx(0.5)
    assert p["max_bars"] >= 10           # 90 minút je 30 barov na 3m


def test_bez_planu_v_kresbach_sa_stop_vezme_zo_skutocneho_vystupu():
    """Kresby nemusia byť (starý beh) — vtedy aspoň to, kde sa naozaj vyšlo na stope."""
    obchod = trade(open_rate=100.0, close_rate=99.0, exit_reason="stop_loss")
    obchod.pop("_sl_pct")
    p = nt.plan_from_trades([obchod], minutes=3)
    assert p["sl_frac"][0] == pytest.approx(0.01)


def test_ziadne_obchody_nedaju_vysledok_ale_ani_nespadnu():
    out = nt.compare([], pair="BTC/USDT:USDT", timeframe="3m")
    assert out.observed is None and "obchody" in out.note


def test_neznama_nahoda_sa_ohlasi():
    with pytest.raises(ValueError, match="náhoda"):
        nt.compare([trade()], pair="BTC/USDT:USDT", timeframe="3m", null="nieco")


# --------------------------------------------------------------------------- #
# verdikt
# --------------------------------------------------------------------------- #


def vysledok(sigma: float, trades: int = 100) -> nt.Result:
    return nt.Result(observed=0.1, trades=trades, iterations=1000, mean=0.0, sd=0.05,
                     percentile=99.0, sigma=sigma)


def test_verdikt_rozlisuje_dokaz_naznak_a_nic():
    assert "odlisitelny od nahody" in vysledok(2.5).verdict
    assert "Naznak" in vysledok(1.4).verdict
    assert "Neodlisitelne" in vysledok(0.3).verdict


def test_horsie_nez_nahoda_sa_povie_nahlas():
    """Keď náhodný vstup dáva lepší výsledok, výber vstupu výsledku škodí."""
    assert "HORSIE nez nahoda" in vysledok(-1.8).verdict


def test_pri_malo_obchodoch_verdikt_upozorni_ze_je_ich_malo():
    assert "malo" in vysledok(2.5, trades=8).verdict
    assert "malo" not in vysledok(2.5, trades=100).verdict


def test_vypis_je_ascii_kvoli_konzole_na_windows():
    assert nt.report(vysledok(2.5)).encode("ascii", "replace")


# --------------------------------------------------------------------------- #
# okná a plán bez TP
# --------------------------------------------------------------------------- #


def test_maska_okien_vyberie_len_sviecky_z_okien():
    ts = np.arange(0, 400) * 86_400_000 + int(
        __import__("datetime").datetime(2023, 1, 1, tzinfo=__import__("datetime").timezone.utc)
        .timestamp() * 1000)
    maska = nt._window_mask(ts, ["20230201-20230301", "20230601-20230611", "nezmysel"])
    assert maska.sum() == 28 + 10
    assert not maska[:31].any()


def test_plan_bez_tp_nema_ciel_pre_nahodu():
    """Výstup na štruktúru: plán má stop, ale TP nie — náhoda nesmie dostať RR 1."""
    obchody = [{**trade(), "_rr_planned": None} for _ in range(5)]
    p = nt.plan_from_trades(obchody, 3)
    assert np.isinf(p["rr"]).all()

    bez_planu = [{**trade(exit_reason="stop_loss", close_rate=99.0), "_sl_pct": None,
                  "_rr_planned": None} for _ in range(5)]
    p = nt.plan_from_trades(bez_planu, 3)
    assert (p["rr"] == 1.0).all()                   # bez plánu ostáva neutrálna jednotka


def test_nahoda_bez_tp_konci_na_stope_alebo_na_case():
    candles = rovny_trh()
    p = plan(count=20, rr=float("inf"))
    vzorka = nt.simulate(candles, p, iterations=20)
    assert len(vzorka) == 20 and all(np.isfinite(v) for v in vzorka)
