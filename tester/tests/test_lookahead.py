"""Test utnutia dát (`tester.lookahead`, smernica 1b/1c): poctivá stratégia prejde, pohľad dopredu sa chytí."""

from __future__ import annotations

import pytest

from tester.lookahead import cut_test


@pytest.fixture(scope="module")
def mnq():
    import pandas as pd

    from tester import engines
    from tradebot.core.types import INSTRUMENTS

    inst = INSTRUMENTS["mnq_databento"]
    path = engines.one_minute_file(inst)
    if not path.exists():
        pytest.skip("chýbajú 1m dáta MNQ")
    return inst, pd.read_feather(path)


def _tks():
    from tradebot.strategies.tks.config import TksConfig

    return TksConfig()


A, B = 1770595200000, 1771804800000          # 9. 2. 2026 – 23. 2. 2026


def test_poctiva_strategia_nema_rozdiel(mnq):
    inst, m1 = mnq
    rep = cut_test(_tks(), inst, m1, 3, A, B, signal_cuts=3, random_cuts=2, seed=1)
    assert rep.bars > 1000 and rep.cuts
    assert rep.ok, rep.diffs


def test_pohlad_dopredu_sa_chyti(mnq, monkeypatch):
    """Bar grafu nesie high/low o 5 barov dopredu (ako `shift(-5)`) — test to musí vidieť."""
    from tradebot.adapters.multicharts import emulator
    from tradebot.core.types import Bar

    orig = emulator.bars_from_frame

    def leaky(m1, minutes, from_ms=None, to_ms=None):
        bars = orig(m1, minutes, from_ms, to_ms)
        if minutes == 1:
            return bars
        out = []
        for i, b in enumerate(bars):
            f = bars[min(i + 5, len(bars) - 1)]
            out.append(Bar(time=b.time, open=b.open, high=max(b.high, f.high), low=min(b.low, f.low),
                           close=b.close, volume=b.volume))
        return out

    monkeypatch.setattr(emulator, "bars_from_frame", leaky)
    inst, m1 = mnq
    rep = cut_test(_tks(), inst, m1, 3, A, B, signal_cuts=3, random_cuts=2, seed=1)
    assert not rep.ok
