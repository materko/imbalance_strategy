"""Stav trhu pri vstupe — vlastnosti, podľa ktorých sa **dá** filtrovať.

Rozdiel oproti vlastnostiam obchodu je v tom, že tieto sa počítajú z barov PRED vstupom,
takže v okamihu rozhodnutia sú známe. Testy strážia, že sa naozaj počítajú z minulosti
(nie z barov po vstupe) a že každá miera meria to, čo tvrdí — na trhoch, ktorých tvar
poznáme dopredu.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tester import regime as rg


class FakeSeries:
    """Sviečky s dopredu známym tvarom, podstrčené namiesto skladu."""

    def __init__(self, close):
        self.close = np.asarray(close, dtype=float)
        self.ts = np.arange(len(self.close), dtype=np.int64) * 180_000  # 3m bary

    def __call__(self, pair, timeframe):
        c = self.close
        return self.ts, {"high": c + 0.5, "low": c - 0.5, "close": c,
                         "open": c, "volume": np.ones_like(c)}


def obchod(index: int, *, short: bool = False, ts_krok: int = 180_000):
    """Obchod, ktorý vstúpil na bare `index`."""
    from datetime import datetime, timezone

    cas = datetime.fromtimestamp(index * ts_krok / 1000, tz=timezone.utc)
    return {"open_date": cas.isoformat(), "is_short": short,
            "open_rate": 100.0, "close_rate": 101.0, "amount": 1.0}


def anotuj(close, trades, monkeypatch, lookback=50):
    monkeypatch.setattr("tester.webapp.chart.series", FakeSeries(close))
    return rg.annotate(trades, "X/USD", "3m", lookback=lookback)


# --------------------------------------------------------------------------- #
# trend alebo rozsah
# --------------------------------------------------------------------------- #


def test_priamka_ma_efektivitu_jedna_pilka_takmer_nulu(monkeypatch):
    """Efficiency ratio: čistá zmena delená súčtom absolútnych krokov."""
    priamka = np.arange(200, dtype=float)
    t = anotuj(priamka, [obchod(150)], monkeypatch)
    assert t[0]["_regime_trend"] == pytest.approx(1.0, abs=1e-6)

    pilka = np.array([100.0 + (i % 2) for i in range(200)])
    t = anotuj(pilka, [obchod(150)], monkeypatch)
    assert t[0]["_regime_trend"] < 0.05


# --------------------------------------------------------------------------- #
# volatilita
# --------------------------------------------------------------------------- #


def test_volatilita_je_pomer_k_typickemu_atr(monkeypatch):
    """Pokojný trh, ktorý sa na konci rozkolíše — vstup v rozkolísanej časti musí vyjsť nad 1."""
    pokoj = np.cumsum(np.tile([0.1, -0.1], 300))[:400] + 100.0
    divoke = np.cumsum(np.tile([3.0, -3.0], 50))[:100] + 100.0
    close = np.concatenate([pokoj, divoke])

    v_pokoji = anotuj(close, [obchod(300)], monkeypatch)[0]["_regime_vol"]
    v_divokom = anotuj(close, [obchod(470)], monkeypatch)[0]["_regime_vol"]

    assert v_divokom > v_pokoji
    assert v_divokom > 1.0


# --------------------------------------------------------------------------- #
# poloha v rozsahu
# --------------------------------------------------------------------------- #


def test_poloha_v_rozsahu_je_nula_na_spodku_a_jedna_na_vrchu(monkeypatch):
    rastuci = np.arange(200, dtype=float)
    t = anotuj(rastuci, [obchod(150)], monkeypatch)
    assert t[0]["_regime_pos"] > 0.95            # vstup na vrchu okna

    klesajuci = np.arange(200, 0, -1).astype(float)
    t = anotuj(klesajuci, [obchod(150)], monkeypatch)
    assert t[0]["_regime_pos"] < 0.05            # vstup na spodku


# --------------------------------------------------------------------------- #
# smer voči trendu
# --------------------------------------------------------------------------- #


def test_long_v_rastucom_trhu_je_s_trendom_short_proti(monkeypatch):
    rastuci = np.arange(200, dtype=float)
    t = anotuj(rastuci, [obchod(150), obchod(150, short=True)], monkeypatch)
    assert t[0]["_regime_align"] == "s trendom"
    assert t[1]["_regime_align"] == "proti trendu"


def test_v_klesajucom_trhu_je_to_naopak(monkeypatch):
    klesajuci = np.arange(200, 0, -1).astype(float)
    t = anotuj(klesajuci, [obchod(150), obchod(150, short=True)], monkeypatch)
    assert t[0]["_regime_align"] == "proti trendu"
    assert t[1]["_regime_align"] == "s trendom"


# --------------------------------------------------------------------------- #
# hranice
# --------------------------------------------------------------------------- #


def test_pocita_sa_LEN_z_barov_pred_vstupom(monkeypatch):
    """Toto je celý dôvod, prečo sú tieto vlastnosti filtrovateľné.

    Trh, ktorý do vstupu rastie a hneď po ňom sa zrúti: keby sa počítalo z barov po
    vstupe, vyšlo by „proti trendu" a filter postavený na tom by v ostrej prevádzke
    nefungoval, lebo budúcnosť sa v ňom vidieť nedá.
    """
    close = np.concatenate([np.arange(150, dtype=float), np.arange(150, 0, -1).astype(float)])
    t = anotuj(close, [obchod(149)], monkeypatch)
    assert t[0]["_regime_align"] == "s trendom"
    assert t[0]["_regime_pos"] > 0.9


def test_obchod_prilis_skoro_nema_kontext(monkeypatch):
    """Prvých päťdesiat barov nemá za sebou okno — radšej nič než vymyslené číslo."""
    t = anotuj(np.arange(200, dtype=float), [obchod(10)], monkeypatch, lookback=50)
    assert not any(k in t[0] for k in rg.KEYS)


def test_bez_sviecok_sa_nedoplni_nic(monkeypatch):
    def spadne(pair, timeframe):
        raise FileNotFoundError("nie su data")

    monkeypatch.setattr("tester.webapp.chart.series", spadne)
    t = rg.annotate([obchod(150)], "X/USD", "3m")
    assert not any(k in t[0] for k in rg.KEYS)


def test_bez_paru_sa_nic_nepocita():
    t = rg.annotate([obchod(150)], "", "3m")
    assert not any(k in t[0] for k in rg.KEYS)


# --------------------------------------------------------------------------- #
# napojenie na analytiku
# --------------------------------------------------------------------------- #


def test_rezimove_vlastnosti_su_medzi_vopred_znamymi():
    """Keby boli medzi výsledkovými, nedali by sa použiť ako filter."""
    from tester import analytics as an

    podla_mena = {f.key: f for f in an.FEATURES}
    for kluc in ("regime_trend", "regime_vol", "regime_pos", "regime_align"):
        assert kluc in podla_mena, kluc
        assert podla_mena[kluc].at_entry, f"{kluc} musí byť známa pri vstupe"
