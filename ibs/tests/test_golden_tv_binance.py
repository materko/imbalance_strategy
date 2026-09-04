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

from ibs.core import load_profile

GOLDEN = Path(__file__).parent / "golden"
TRADES = json.loads((GOLDEN / "tv_btcusdt_binance_3m.json").read_text(encoding="utf-8"))
ZONES = json.loads((GOLDEN / "tv_zones_btcusdt_binance_3m.json").read_text(encoding="utf-8"))

RANGE = ("2026-08-24", "2026-09-04")


@pytest.fixture(scope="module")
def result():
    scan_trades = pytest.importorskip("ibs.tools.scan_trades")
    cfg, inst = load_profile("btcusdt_3m_binance_tv")
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
