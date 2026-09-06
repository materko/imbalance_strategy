"""Parita s TradingView na BINANCE:BTCUSDT.P 3m (Aug 24 - Sep 4 2026).

Referencia je `golden/tv_btcusdt_binance_3m.json` - List of Trades odčítaný priamo
zo Strategy Testera - a `golden/tv_zones_btcusdt_binance_3m.json` - zoznam SD zón
z Pine logov. Test beží nad dátami commitnutými v `platforms/freqtrade/user_data/data`,
takže je deterministický a nepotrebuje sieť.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradebot.core import load_profile

GOLDEN = Path(__file__).parent / "golden"
TRADES = json.loads((GOLDEN / "tv_btcusdt_binance_3m.json").read_text(encoding="utf-8"))
ZONES = json.loads((GOLDEN / "tv_zones_btcusdt_binance_3m.json").read_text(encoding="utf-8"))

RANGE = ("2026-08-24", "2026-09-04")


@pytest.fixture(scope="module")
def result():
    scan_trades = pytest.importorskip("tradebot.tools.scan_trades")
    cfg, inst = load_profile("golden_binance_btcusdt_3m")
    try:
        book, sim, _, _ = scan_trades.run(cfg, inst, "binance", 3, *RANGE)
    except SystemExit as exc:  # chýbajúce feather dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    return book, sim


def _filled(sim):
    """Obchody v poradí vyplnenia - TradingView ich v List of Trades radí rovnako."""
    return sorted(
        (t for t in sim.trades.values() if t.filled_ms is not None),
        key=lambda t: t.filled_ms,
    )


def test_pocet_zon_sedi_s_tradingview(result):
    """TradingView vytvoril 77 zón; posledná (uid 76) je za koncom stiahnutých dát."""
    book, _ = result
    assert len(book.zones) == ZONES["total_zones"] - 1


def test_zony_sedia_na_uid_cas_aj_hranice(result):
    """uid, hranice aj bar vzniku musia sedieť pre každú zónu odčítanú z Pine logov."""
    book, _ = result
    by_uid = {z.uid: z for z in book.zones}
    for tv in ZONES["zones"]:
        ours = by_uid.get(tv["uid"])
        if ours is None:  # uid 76 je za koncom dát
            assert tv["uid"] == ZONES["total_zones"] - 1
            continue
        expected_ms = int(pd.Timestamp(tv["utc"], tz="UTC").timestamp() * 1000)
        assert (int(ours.direction), round(ours.top, 4), round(ours.bot, 4)) == (
            tv["typ"],
            tv["top"],
            tv["bot"],
        ), f"uid {tv['uid']}: iné hranice zóny"
        assert ours.detected_ms == expected_ms, f"uid {tv['uid']}: iný bar vzniku"


def test_pocet_obchodov(result):
    _, sim = result
    assert len(_filled(sim)) == len(TRADES["trades"])


@pytest.mark.parametrize("tv", TRADES["trades"], ids=lambda t: f"trade{t['n']}")
def test_obchod_sedi(result, tv):
    """Minúta vyplnenia, vstupná cena, veľkosť aj výstupná cena musia sedieť."""
    _, sim = result
    ours = _filled(sim)[tv["n"] - 1]
    entry_ms = int(pd.Timestamp(tv["entry_utc"]).timestamp() * 1000)

    assert ours.filled_ms == entry_ms
    assert ours.plan.entry == pytest.approx(tv["entry_price"], abs=0.11)
    assert ours.plan.qty == pytest.approx(tv["size"])

    exit_price = ours.plan.take_profit if ours.outcome == "WIN" else ours.plan.stop_loss
    assert exit_price == pytest.approx(tv["exit_price"], abs=0.11)


def test_winrate(result):
    _, sim = result
    wins = sum(1 for t in _filled(sim) if t.outcome == "WIN")
    assert wins == TRADES["summary"]["wins"]


# --------------------------------------------------------------------------- #
# Obchodovanie z S/R a likvidity
#
# Tieto dve vetvy dlho neboli overené — golden fixture vznikol s nimi vypnutými.
# Zmerané 2026-09-04 priamo v TradingView: na tom istom grafe a rozsahu sa po
# zapnutí oboch prepínačov počet obchodov zmenil z 5 (3W/2L) na 6 (4W/2L)
# (dashboard stratégie hlásil „67% WINRATE (4W / 2L)").
# --------------------------------------------------------------------------- #

#: (enableSrTrading a enableLqTrading, počet zón, obchodov, výhier, prehier)
TV_SR_LQ = [(False, 76, 5, 3, 2), (True, 109, 6, 4, 2)]


@pytest.mark.parametrize("enabled,zones,trades,wins,losses", TV_SR_LQ)
def test_sr_a_likviditne_zony_sedia_s_tradingview(enabled, zones, trades, wins, losses):
    """Zapnutie S/R a sweep zón musí pridať presne ten jeden obchod, čo v TradingView.

    Ide cez `IBSEngine`, nie cez `tradebot.tools.scan_trades` — ten si stavia
    `ZoneBook` a `StateMachine` sám a spawnovanie z S/R ani zo sweepu vôbec
    nezavolá, takže by tento test ticho prešiel aj s rozbitou logikou.
    """
    pytest.importorskip("pandas")
    import pandas as pd

    from tradebot.core import HTFWindow, IBSEngine, MarketContext, SessionClock, htf_window_opens
    from tradebot.tools.scan_trades import FillSimulator
    from tradebot.tools.scan_zones import _load, _to_bar

    cfg, inst = load_profile("golden_binance_btcusdt_3m")
    cfg.enableSrTrading = enabled
    cfg.enableLqTrading = enabled
    try:
        chart, htf, detail = (_load("binance", tf) for tf in ("3m", "5m", "1m"))
    except SystemExit as exc:
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")

    lo, hi = pd.Timestamp(RANGE[0], tz="UTC"), pd.Timestamp(RANGE[1], tz="UTC") + pd.Timedelta(days=1)
    frames = []
    for df in (chart, htf, detail):
        df["date"] = pd.to_datetime(df["date"], utc=True)
        frames.append(df[(df["date"] >= lo) & (df["date"] < hi)])
    chart, htf, detail = frames

    htf = htf.copy()
    htf["vol_sma"] = htf["volume"].rolling(cfg.volSmaLen).mean()
    htf_bars = {int(r.ts): _to_bar(r) for r in htf.itertuples(index=False)}
    htf_sma = {
        int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0)
        for r in htf.itertuples(index=False)
    }
    detail_by_bar: dict[int, list] = {}
    for r in detail.itertuples(index=False):
        detail_by_bar.setdefault(int(r.ts) // 180_000 * 180_000, []).append(_to_bar(r))

    clock, engine, sim = SessionClock(cfg), IBSEngine(cfg, inst, 3), FillSimulator()
    prev_htf: int | None = None
    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        sim.step(bar, detail_by_bar.get(bar.time))

        window = None
        htf_open = bar.time // 300_000 * 300_000
        if prev_htf is not None and htf_open != prev_htf:
            opens = htf_window_opens(bar.time, 180_000, 300_000)
            if all(o in htf_bars for o in opens):
                window = HTFWindow(tuple(htf_bars[o] for o in opens), htf_sma[opens[0]])
        prev_htf = htf_open

        state = clock.state(bar.time)
        out = engine.on_bar(
            bar,
            window,
            MarketContext(
                in_trade_window=state.in_trade_window,
                position_size=sim.position_size,
                open_order_ids=sim.open_ids,
            ),
        )
        sim.apply(out.orders, bar)

    filled = [t for t in sim.trades.values() if t.filled_ms is not None]
    assert len(engine.book.zones) == zones
    assert len(filled) == trades
    assert sum(1 for t in filled if t.outcome == "WIN") == wins
    assert sum(1 for t in filled if t.outcome == "LOSS") == losses
