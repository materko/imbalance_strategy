"""Testy robustnosti smernice (`tester.robust`): Deflated Sharpe a posun vstupu v emulátore."""

from __future__ import annotations

import math
import random

from tester.robust import deflated_sharpe


def test_dsr_klesa_s_poctom_skusok():
    rnd = random.Random(1)
    daily = [rnd.gauss(0.001, 0.01) for _ in range(1000)]
    one = deflated_sharpe(daily, 1)
    many = deflated_sharpe(daily, 20000)
    assert one["dsr"] > many["dsr"]
    assert math.isclose(one["dsr"], one["psr"])          # jedna skúška = pravdepodobnostný Sharpe bez korekcie
    assert many["sr0"] > 0


def test_dsr_bez_edge_je_nizky():
    rnd = random.Random(2)
    daily = [rnd.gauss(0.0, 0.01) for _ in range(1000)]
    assert deflated_sharpe(daily, 1000)["dsr"] < 0.5


def test_malo_dni_nedava_vysledok():
    assert deflated_sharpe([0.01] * 10, 10)["dsr"] == 0.0


def test_posun_0_je_presne_emulator(tmp_path):
    """`entry_delay=0` nesmie zmeniť ani jeden obchod (parita s platformou)."""
    import pandas as pd

    from tester import engines
    from tradebot.adapters.multicharts.emulator import emulate
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies.m2 import M2Config

    inst = INSTRUMENTS["es_databento"]
    path = engines.one_minute_file(inst)
    if not path.exists():
        import pytest
        pytest.skip("chýbajú 1m dáta ES")
    m1 = pd.read_feather(path)
    cfg = M2Config(useEmaTrend=False)
    a, b = 1772409600000, 1772496000000            # 2. 3. 2026 – 3. 3. 2026
    r0, _ = emulate(cfg, inst, m1, 1, from_ms=a, to_ms=b)
    r1, _ = emulate(cfg, inst, m1, 1, from_ms=a, to_ms=b, entry_delay=0)
    rd, _ = emulate(cfg, inst, m1, 1, from_ms=a, to_ms=b, entry_delay=1)
    key = lambda r: [(t.order_id, t.open_ms, t.entry, t.exit) for t in r.trades]   # noqa: E731
    assert key(r0) == key(r1)
    assert r0.trades and key(rd) != key(r0)


def test_prekryv_okien_sa_pocita_raz():
    """M-CORE-2: obchod z prekrytia okien (4.–30. 9. 2024) je v oboch behoch, do súčtu ide raz.
    `enter_tag` má v každom behu iné číslo baru, preto rozhoduje čas otvorenia, nie order."""
    from tester.robust import _outside

    skor = {"open_date": "2024-09-03T14:00:00+00:00", "enter_tag": "sigma:9", "profit_abs": 5.0}
    v_prekryti = {"open_date": "2024-09-10T14:00:00+00:00", "enter_tag": "sigma:8948", "profit_abs": 50.0}
    na_hrane = {"open_date": "2024-10-01T00:00:00+00:00", "enter_tag": "sigma:9100", "profit_abs": -20.0}
    po = {"open_date": "2024-10-02T14:00:00+00:00", "enter_tag": "sigma:9403", "profit_abs": 10.0}
    druhe = [v_prekryti, na_hrane, po]
    assert _outside(druhe, []) == druhe                                   # prvé okno ide celé
    assert _outside(druhe, ["20231001-20241001"]) == [na_hrane, po]       # koniec okna do neho nepatrí
    assert _outside([skor], ["20231001-20241001"]) == []


def test_sucty_cez_prekryte_okna_nemaju_obchod_dvakrat():
    """Skutočný beh: dve prekryté okná dajú v súčte toľko obchodov ako okná, ktoré sa len dotýkajú."""
    import pandas as pd
    import pytest

    from tester import engines
    from tester.robust import robustness
    from tradebot.core.config import profile_path
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec

    inst = INSTRUMENTS["es_databento"]
    path = engines.one_minute_file(inst)
    if not path.exists():
        pytest.skip("chýbajú 1m dáta ES")
    m1 = pd.read_feather(path)
    m1 = m1[(m1["date"] >= "2026-01-15") & (m1["date"] < "2026-03-07")].reset_index(drop=True)
    prof = profile_path("m2", get_spec("m2").default_profile)
    kw = dict(m1=m1, log=lambda _s: None)
    prekryte = robustness(str(prof), inst.symbol, "1m", 1e-5, 1, windows=("20260302-20260305", "20260304-20260306"), **kw)
    susedne = robustness(str(prof), inst.symbol, "1m", 1e-5, 1, windows=("20260302-20260305", "20260305-20260306"), **kw)
    spolu = sum(w["trades"] for w in prekryte.windows)
    assert prekryte.windows[0]["trades"] > 0 and spolu > prekryte.total["trades"] > 0
    # 4. 3. patrí prvému oknu; z druhého ide do súčtu len 5. 3. — približne to, čo dá okno od 5. 3.
    # (beh s iným začiatkom má inú predhistóriu, preto nie na obchod presne)
    assert abs(prekryte.total["trades"] - susedne.total["trades"]) <= max(3, susedne.total["trades"] // 10)


def test_pf_je_pravidlo_jadra():
    """M-CORE-7 / N-CORE-7: PF počíta jedna funkcia v jadre — aj bez stratových obchodov."""
    from tester.robust import _pf
    from tradebot.core.money import profit_factor, summary_money

    rows = [{"profit_abs": 30.0}, {"profit_abs": -10.0}]
    assert _pf(rows) == profit_factor(30.0, 10.0) == 3.0
    wins = [{"profit_abs": 30.0}, {"profit_abs": 12.5}]
    assert _pf(wins) == profit_factor(42.5, 0.0) == summary_money(wins, 1000.0)["profit_factor"]
    assert _pf([]) == 0.0


def test_sharpe_z_vsetkych_obchodnych_dni():
    """M-CORE-7: dni bez obchodu majú výnos 0 — riedka stratégia nemá Sharpe len z dní, kde obchodovala."""
    from tester.robust import _daily_returns, _trading_days

    days = _trading_days(("20240902-20240916", "20240909-20240923"))     # prekrytie 9.–15. 9. raz
    assert days[0] == "2024-09-02" and days[-1] == "2024-09-20" and len(days) == 15
    rows = [{"close_date": "2024-09-03T15:00:00+00:00", "profit_abs": 100.0},
            {"close_date": "2024-09-03T18:00:00+00:00", "profit_abs": -50.0},
            {"close_date": "2024-09-08T23:30:00+00:00", "profit_abs": 20.0}]   # nedeľa (Globex) sa nestratí
    daily = _daily_returns(rows, 1000.0, ("20240902-20240916", "20240909-20240923"))
    assert len(daily) == 16 and sorted(x for x in daily if x) == [0.02, 0.05]
    assert math.isclose(sum(daily), 0.07)


def test_timeframe_cez_jadro():
    """M-CORE-7: `1h` nesmie spadnúť — TF parsuje `tradebot.core.candles.timeframe_minutes`."""
    from tester.lookahead import _tf_minutes

    assert _tf_minutes("1h") == 60 and _tf_minutes("3m") == 3 and _tf_minutes(None) == 5


def test_vyrez_m1_je_rovnaky_ako_maska():
    """§5 bod 4: `searchsorted` nad zoradeným m1 dá presne tie isté bary ako maska; cache ich len zdieľa."""
    import pandas as pd

    from tradebot.adapters.multicharts.emulator import BarCache, _window, bars_from_frame

    n = 600
    dates = pd.date_range("2026-03-02 00:00", periods=n, freq="1min", tz="UTC")
    dates = dates.delete(list(range(100, 130)))                       # diera v dátach
    rnd = random.Random(3)
    px = [100 + rnd.random() for _ in dates]
    m1 = pd.DataFrame({"date": dates, "open": px, "high": [p + 1 for p in px], "low": [p - 1 for p in px],
                       "close": px, "volume": [1.0] * len(dates)})
    a = int(dates[37].timestamp() * 1000)
    b = int(dates[400].timestamp() * 1000) + 20_000                    # hranica mimo minúty
    for lo, hi in ((a, b), (None, b), (a, None), (b, a), (a - 10 ** 9, b + 10 ** 9)):
        mask = m1
        if lo is not None:
            mask = mask[mask["date"] >= pd.Timestamp(lo, unit="ms", tz="UTC")]
        if hi is not None:
            mask = mask[mask["date"] < pd.Timestamp(hi, unit="ms", tz="UTC")]
        pd.testing.assert_frame_equal(_window(m1, lo, hi), mask)
    shuffled = m1.sample(frac=1.0, random_state=1)                     # nezoradený rámec ide maskou
    assert sorted(_window(shuffled, a, b)["date"]) == sorted(_window(m1, a, b)["date"])
    cache = BarCache(m1)
    assert cache.bars(5, a, b) == bars_from_frame(m1, 5, a, b)
    assert cache.bars(5, a, b) is cache.bars(5, a, b)
