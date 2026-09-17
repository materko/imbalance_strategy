"""Stav trhu pri vstupe — vlastnosti, podľa ktorých sa **dá** filtrovať.

Rozdiel oproti vlastnostiam obchodu je v tom, že tieto sa počítajú z barov UZAVRETÝCH PRED vstupom,
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


class Sviecky:
    """Plné OHLC (nie odvodené z close) — aby sa dala zmeniť jedna konkrétna sviečka."""

    def __init__(self, high, low, close):
        self.cols = {"high": np.asarray(high, float), "low": np.asarray(low, float),
                     "close": np.asarray(close, float)}
        self.ts = np.arange(len(close), dtype=np.int64) * 180_000

    def __call__(self, pair, timeframe):
        c = self.cols
        return self.ts, {**c, "open": c["close"], "volume": np.ones_like(c["close"])}


def _nahodny_trh(n=400, seed=7):
    rng = np.random.default_rng(seed)
    close = 1000.0 + np.cumsum(rng.normal(0, 2.0, n))
    rozpatie = np.abs(rng.normal(0, 1.5, n)) + 0.2
    return close + rozpatie, close - rozpatie, close


def _rezim(high, low, close, trades, monkeypatch):
    monkeypatch.setattr("tester.webapp.chart.series", Sviecky(high, low, close))
    return [{k: t.get(k) for k in rg.KEYS} for t in rg.annotate(trades, "X/USD", "3m")]


def test_vstupna_ani_buduca_sviecka_nezmeni_rezim(monkeypatch):
    """Prefixový test (audit A9): príznak pri vstupe smie závisieť len od uzavretých barov.

    Obchod vstúpil na otvorení baru 300. Jeho sviečka (v tej chvíli ešte neuzavretá)
    aj všetko po nej sa prepíše na extrém opačným smerom — stav trhu musí ostať ten istý.
    Prvá verzia tu z „s trendom" urobila „proti trendu".
    """
    high, low, close = _nahodny_trh()
    vstup = 300
    obchody = [obchod(vstup), obchod(vstup, short=True)]
    povodne = _rezim(high, low, close, [dict(t) for t in obchody], monkeypatch)
    assert all(all(v is not None for v in r.values()) for r in povodne)

    for od in (vstup, vstup + 1, vstup + 50):
        h, l, c = high.copy(), low.copy(), close.copy()
        c[od:] = c[od:] * 0.5 if c[vstup - 1] > c[vstup - 51] else c[od:] * 2.0
        h[od:], l[od:] = c[od:] * 1.3, c[od:] * 0.7
        assert _rezim(h, l, c, [dict(t) for t in obchody], monkeypatch) == povodne, od


def test_bar_signalu_pred_vstupom_sa_pocita(monkeypatch):
    """Opačná strana prefixového testu: posledný uzavretý bar (signál) do režimu patrí —
    inak by predošlý test prešiel aj pri príznaku, ktorý nevidí nič."""
    high, low, close = _nahodny_trh()
    vstup = 300
    povodne = _rezim(high, low, close, [obchod(vstup)], monkeypatch)
    h, l, c = high.copy(), low.copy(), close.copy()
    c[vstup - 1] = c[vstup - 1] + 500.0
    h[vstup - 1] = c[vstup - 1] + 1.0
    assert _rezim(h, l, c, [obchod(vstup)], monkeypatch) != povodne


def test_typicka_volatilita_nevidi_buducnost(monkeypatch):
    """Normál volatility je rolling medián minulosti: rozkolísaný koniec série nesmie
    zmeniť `_regime_vol` obchodu, ktorý bol dávno pred ním."""
    high, low, close = _nahodny_trh(n=600)
    povodne = _rezim(high, low, close, [obchod(200)], monkeypatch)
    h, l = high.copy(), low.copy()
    h[400:] += 50.0
    l[400:] -= 50.0
    assert _rezim(h, l, close, [obchod(200)], monkeypatch) == povodne


def test_okno_volatility_je_rovnake_ako_v_ai_vrstve():
    ai = pytest.importorskip("tradebot.adapters.freqtrade.ai")
    assert rg.VOL_DAYS == ai.VOL_DAYS
    for tf in ("1m", "3m", "15m", "1h"):
        assert rg.vol_bars(tf) == ai.vol_window(tf)


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
