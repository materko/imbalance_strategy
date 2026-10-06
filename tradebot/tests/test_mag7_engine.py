"""Mag7 + SPX sila: engine na syntetických baroch a hodnotách symbolov.

Testuje sa mechanika portu Pine stratégie, nie edge: výpočet sily, okno vstupu podľa zavretia sviečky,
potvrdenia VWAP / EMA / MAG7, stop za open NY a cieľ z RR, jeden obchod za deň a zatvorenie v čase.
Dáta symbolov prichádzajú ako hotový `Mag7Snapshot` (feeder sa tu nevolá).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.mag7 import Mag7Config, Mag7Engine, SlMode
from tradebot.strategies.mag7.data import Mag7Snapshot, SymbolValue
from tradebot.strategies.mag7.engine import strength

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
STEP = 15 * 60_000
OKNO = MarketContext(in_trade_window=True)


def t(h: int, m: int) -> int:
    return int(datetime(2025, 9, 2, h, m, tzinfo=NY).timestamp() * 1000)


def snap(move: float, typ: float = 0.2, n: int = 8, vwap: float | None = None) -> Mag7Snapshot:
    return Mag7Snapshot(tuple(SymbolValue(move, typ, 1.0) for _ in range(n)), vwap, "mnq_databento")


def engine(**kw) -> Mag7Engine:
    base = dict(emaLen=2, magLen=1)
    base.update(kw)
    return Mag7Engine(Mag7Config(**base), MNQ, 15)


def warm(e: Mag7Engine, px: float = 20000.0) -> None:
    """Nočné bary 8:00–9:15 (EMA sa rozbehne, NY seansa ešte nie je)."""
    for k in range(6):
        e.on_bar(Bar(t(8, 0) + k * STEP, px, px + 2, px - 2, px, 10.0), None, OKNO)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


# ---------------------------------------------------------------------------- #

def test_sila_je_10_ked_vsetko_ide_hore_nad_bezny_pohyb():
    cfg = Mag7Config()
    sila, avg = strength(snap(0.5, typ=0.2), cfg)
    assert sila == 10.0 and abs(avg - 0.5) < 1e-12
    sila, _ = strength(snap(-0.1, typ=0.2), cfg)   # veľkosť −0,5, zhoda −1
    assert abs(sila - (-7.5)) < 1e-9


def test_symbol_bez_dat_sa_nepocita_a_bez_typ_ma_nulovu_velkost():
    cfg = Mag7Config()
    s = Mag7Snapshot((SymbolValue(0.4, None, 1.0), SymbolValue(None, 0.2, 1.0)), None, "")
    sila, _ = strength(s, cfg)
    assert sila == 5.0   # veľkosť 0 (bez bežného pohybu), zhoda +1


def test_long_na_zavreti_915_po_meracom_case():
    e = engine(waitMin=10, slMode=SlMode.OPEN, slOpenBuf=2.0, rr=1.5, useMag=False)
    warm(e)
    out = e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), snap(0.5, vwap=20010), OKNO)
    p = entries(out)[0].plan   # zavretie 9:45 = 15 min po otvorení ≥ 10
    assert p.direction is Direction.LONG
    assert p.entry == 20025 and p.stop_loss == 19998        # za open NY 20000 − 2
    assert p.take_profit == 20025 + 27 * 1.5
    assert p.qty == 1.0


def test_pred_meranim_ani_po_okne_sa_nevstupuje():
    e = engine(waitMin=20, entryEnd=30, useMag=False)
    warm(e)
    assert not entries(e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), snap(0.5, vwap=20010), OKNO))
    assert entries(e.on_bar(Bar(t(9, 45), 20025, 20040, 20020, 20035, 50.0), snap(0.5, vwap=20015), OKNO))
    e2 = engine(waitMin=10, entryEnd=30, useMag=False)
    warm(e2)
    e2.on_bar(Bar(t(9, 30), 20000, 20004, 19996, 20000, 50.0), snap(0.0, vwap=20000), OKNO)   # sila 0
    e2.on_bar(Bar(t(9, 45), 20000, 20004, 19996, 20000, 50.0), snap(0.0, vwap=20000), OKNO)
    # 10:00–10:15 sa zavrie 45 min po otvorení — mimo okna
    assert not entries(e2.on_bar(Bar(t(10, 0), 20000, 20040, 19996, 20035, 50.0), snap(0.5, vwap=20010), OKNO))


def test_vwap_ema_a_mag7_musia_potvrdit():
    for kw, s in ((dict(useMag=False), snap(0.5, vwap=20030)),     # zavretie pod VWAP
                  (dict(useMag=False, emaLen=2), None)):
        e = engine(**kw)
        warm(e, px=20100.0)                                         # EMA nad cenou
        out = e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), s or snap(0.5, vwap=20010), OKNO)
        assert not entries(out)
    e = engine(useMag=True, magLen=1)
    warm(e)
    # priemerný pohyb 0,5 % → čiara MAG7 = 20000 × 1,005 = 20100 nad zavretím 20025
    assert not entries(e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), snap(0.5, vwap=20010), OKNO))


def test_short_zrkadlovo_a_stop_v_bodoch():
    e = engine(useMag=False, slMode=SlMode.POINTS, slPts=20.0, rr=2.0)
    warm(e, px=20050.0)
    p = entries(e.on_bar(Bar(t(9, 30), 20000, 20002, 19970, 19975, 50.0), snap(-0.5, vwap=19990), OKNO))[0].plan
    assert p.direction is Direction.SHORT
    assert (p.stop_loss, p.take_profit) == (19995, 19935)


def test_jeden_obchod_za_den_a_zatvorenie_v_case():
    e = engine(useMag=False, useEod=True, eodH=15, eodM=55, entryEnd=60)
    warm(e)
    assert entries(e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), snap(0.5, vwap=20010), OKNO))
    flat = MarketContext(in_trade_window=True)
    assert not entries(e.on_bar(Bar(t(9, 45), 20025, 20040, 20020, 20035, 50.0), snap(0.5, vwap=20015), flat))
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"m7:6"}))
    assert not e.on_bar(Bar(t(15, 30), 20030, 20032, 20028, 20030, 5.0), snap(0.5, vwap=20015), pos).close_session
    out = e.on_bar(Bar(t(15, 40), 20030, 20032, 20028, 20030, 5.0), snap(0.5, vwap=20015), pos)
    assert out.close_session   # zavretie 15:55


def test_vwap_zo_sviecok_grafu_ked_graf_nie_je_nastroj_vwap():
    e = Mag7Engine(Mag7Config(emaLen=2, useMag=False), INSTRUMENTS["nas100_dukascopy"], 15)
    warm(e)
    e.on_bar(Bar(t(9, 30), 20000, 20030, 19998, 20025, 50.0), snap(0.5, vwap=99999.0), OKNO)
    assert abs(e.vwap - (20030 + 19998 + 20025) / 3) < 1e-9


def test_vaha_akcii_0_pocita_silu_len_z_indexu():
    """1.1: stockW = 0 — akcie sa nepočítajú (tak to vyšlo v TradingView), index sám určí silu."""
    cfg = Mag7Config(stockW=0.0)
    w = [wt for _k, wt in cfg.symbols]
    assert w[:7] == [0.0] * 7 and w[7] == 1.0
    s = Mag7Snapshot(tuple(SymbolValue(-1.0, 0.2, wt) for wt in w[:7]) + (SymbolValue(0.3, 0.12, 1.0),), None, "")
    sila, avg = strength(s, cfg)
    assert sila == 10.0 and abs(avg - 0.3) < 1e-12
    w10 = [wt for _k, wt in Mag7Config().symbols]       # 1.0: všetky váhy 1, akcie dole prevážia
    s10 = Mag7Snapshot(tuple(SymbolValue(-1.0, 0.2, wt) for wt in w10[:7]) + (SymbolValue(0.3, 0.12, 1.0),), None, "")
    assert strength(s10, Mag7Config())[0] < 0
