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
