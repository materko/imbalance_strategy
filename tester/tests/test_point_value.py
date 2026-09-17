"""Hodnota bodu (`point_value`) — ten istý obchod dá všade tie isté peniaze (audit A1).

Trh s hodnotou bodu ≠ 1 (MNQ 2, zlato 100, forex 100 000) prezradil každú kópiu vzorca,
ktorá na ňu zabudla: emulátor mal break-even ×hodnota bodu, Monte Carlo a analytika
doláre ÷hodnota bodu a Freqtrade ju nepoznal vôbec. Testy tu stavajú **ten istý obchod
v peniazoch** na štyroch hodnotách bodu (kusy = peniaze za bod / hodnota bodu) a chcú
rovnaké čísla v súhrne emulátora, v normalizovanom Freqtrade výsledku, v Monte Carlo,
v analytike aj v portfóliu — a jedno reálne číslo z auditu (MNQ 100 → 110 = 4,7619 %).
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from tradebot.core.money import (break_even_pct, fill_point_value, gross_and_volume, max_drawdown,
                                 row_money, summary_money, trade_money)
from tradebot.core.types import INSTRUMENTS, Direction, InstrumentSpec

#: hodnota bodu -> pár s touto hodnotou v registri (Freqtrade normalizácia ide cez pár)
PAIRS = {1.0: "BTC/USDT:USDT", 2.0: "MNQ/USD", 100.0: "XAU/USD", 100_000.0: "EURUSD/USD"}
POINT_VALUES = tuple(PAIRS)

#: (vstup, výstup, short, peniaze za bod, dôvod) — výsledok v mene účtu nezávisí od pv
TRADES = [
    (100.0, 110.0, False, 2.0, "take_profit"),    # +20
    (110.0, 104.0, False, 3.0, "stop_loss"),      # -18
    (104.0, 99.0, True, 4.0, "take_profit"),      # +20
    (99.0, 101.5, True, 10.0, "stop_loss"),       # -25
    (101.5, 100.0, False, 8.0, "stop_loss"),      # -12
    (100.0, 103.0, False, 6.0, "take_profit"),    # +18
]
FEE = 0.0005
WALLET = 1_000.0


def _inst(pv: float) -> InstrumentSpec:
    return InstrumentSpec(symbol=PAIRS[pv], venue="test", tick_size=0.01, point_value=pv,
                          qty_step=1e-9, min_qty=1e-9)


def _emu_rows(pv: float) -> list[dict]:
    from tradebot.adapters.multicharts.emulator import EmuTrade, rows_from_trades

    t0 = 1_736_121_600_000
    trades = []
    for i, (o, c, short, money, reason) in enumerate(TRADES):
        trades.append(EmuTrade(
            order_id=f"T{i}", direction=Direction.SHORT if short else Direction.LONG,
            qty=money / pv, entry=o, open_ms=t0 + i * 3_600_000, stop_initial=o * (1.02 if short else 0.98),
            take_profit=o * (0.96 if short else 1.04), market=False, stop_last=o,
            exit=c, close_ms=t0 + i * 3_600_000 + 1_800_000, reason=reason, max_price=max(o, c),
            min_price=min(o, c)))
    return rows_from_trades(trades, _inst(pv), FEE, leverage=10.0)


def _emu_summary(pv: float) -> dict:
    from tradebot.adapters.multicharts.emulator import EmulationResult, summarize

    rows = _emu_rows(pv)
    res = EmulationResult(trades=[], bars=10, first_ms=0, last_ms=1, first_close=100.0,
                          last_close=100.0, ambiguous=0)
    return summarize(rows, WALLET, res)[0]


EXPECTED_NET = [20 - (100 + 110) * 2 * FEE, -18 - (110 + 104) * 3 * FEE, 20 - (104 + 99) * 4 * FEE,
                -25 - (99 + 101.5) * 10 * FEE, -12 - (101.5 + 100) * 8 * FEE, 18 - (100 + 103) * 6 * FEE]
EXPECTED_GROSS = 20 - 18 + 20 - 25 - 12 + 18
EXPECTED_VOLUME = sum((o + c) * m for o, c, _s, m, _r in TRADES)


# --------------------------------------------------------------------------- #
# jadro
# --------------------------------------------------------------------------- #


def test_audit_mnq_jeden_kontrakt():
    """Reprodukcia z auditu: 1 MNQ, 100 → 110, bez poplatku = 20 USD, objem 420, 4,7619 %."""
    m = trade_money(100.0, 110.0, 1.0, is_short=False, point_value=2.0)
    assert m.gross == 20.0 and m.volume == 420.0
    assert break_even_pct(m.gross, m.volume) == 4.7619
    from tradebot.adapters.multicharts.emulator import EmuTrade, EmulationResult, rows_from_trades, summarize

    t = EmuTrade(order_id="A", direction=Direction.LONG, qty=1.0, entry=100.0, open_ms=0, stop_initial=90.0,
                 take_profit=110.0, market=False, exit=110.0, close_ms=60_000, reason="take_profit")
    rows = rows_from_trades([t], INSTRUMENTS["mnq_databento"], 0.0)
    summary = summarize(rows, 10_000.0, EmulationResult([], 1, 0, 1, 100.0, 110.0, 0))[0]
    assert summary["break_even_pct"] == 4.7619 and summary["pnl_abs"] == 20.0
    assert rows[0]["point_value"] == 2.0 and rows[0]["initial_take_profit_abs"] == 110.0


def test_poplatok_v_tickoch_je_ticky_krat_hodnota_ticku():
    """CFD spread (`cost_pct`) je percento z ceny; s hodnotou bodu v nominále vyjde v peniazoch
    presne `ticky × tick × pv × kusy` na stranu — nie ×pv viac ani menej."""
    inst = INSTRUMENTS["eurusd_dukascopy"]
    cena = 1.1
    fee = inst.cost_pct(cena) / 100.0
    m = trade_money(cena, cena, 3.0, is_short=False, point_value=inst.point_value, fee_open=fee)
    assert m.fee_open == pytest.approx(inst.cost * inst.tick_size * inst.point_value * 3.0)


def test_max_drawdown_je_definicia_freqtradu():
    freqtrade_metrics = pytest.importorskip("freqtrade.data.metrics")
    pd = pytest.importorskip("pandas")
    profits = [50.0, -120.0, 30.0, -80.0, 200.0, -10.0]
    df = pd.DataFrame({"profit_abs": profits,
                       "close_date": pd.date_range("2025-01-01", periods=len(profits), tz="UTC")})
    ft = freqtrade_metrics.calculate_max_drawdown(df, value_col="profit_abs", starting_balance=WALLET)
    dd_abs, dd_pct = max_drawdown(profits, WALLET)
    assert dd_abs == pytest.approx(ft.drawdown_abs)
    assert dd_pct == pytest.approx(ft.relative_account_drawdown * 100.0)


def test_chybajuca_hodnota_bodu_sa_doplni_z_paru_a_neprepise():
    rows = [{"open_rate": 1.0, "close_rate": 1.1, "amount": 1.0}, {"point_value": 7.0}]
    fill_point_value(rows, "EURUSD/USD")
    assert rows[0]["point_value"] == 100_000.0 and rows[1]["point_value"] == 7.0
    krypto = [{"open_rate": 1.0}]
    fill_point_value(krypto, "BTC/USDT:USDT")          # hodnota 1 -> záznam sa nemení
    assert krypto == [{"open_rate": 1.0}]


# --------------------------------------------------------------------------- #
# ten istý obchod na štyroch hodnotách bodu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("pv", POINT_VALUES)
def test_emulator_riadky_a_suhrn(pv):
    rows = _emu_rows(pv)
    assert [r["profit_abs"] for r in rows] == pytest.approx(EXPECTED_NET, abs=1e-3)
    assert all(r["point_value"] == pv for r in rows)
    s = _emu_summary(pv)
    ref = _emu_summary(1.0)
    assert s["gross_abs"] == pytest.approx(EXPECTED_GROSS, abs=0.01)
    assert s["volume_abs"] == pytest.approx(EXPECTED_VOLUME, abs=0.01)
    for k in ("break_even_pct", "pnl_abs", "max_drawdown_abs", "max_drawdown_pct", "profit_factor"):
        assert s[k] == ref[k], k
    assert s["break_even_pct"] == round(EXPECTED_GROSS / EXPECTED_VOLUME * 100, 4)


def _freqtrade_zip(pv: float) -> io.BytesIO:
    """Výsledkový zip, aký by Freqtrade napísal: množstvo v základnej mene (kusy × contractSize)."""
    trades = []
    cum = 0.0
    for i, ((o, c, short, money, reason), net) in enumerate(zip(TRADES, EXPECTED_NET)):
        cum += net
        trades.append({
            "pair": PAIRS[pv], "open_date": f"2025-01-06 {i:02d}:00:00+00:00",
            "close_date": f"2025-01-06 {i:02d}:30:00+00:00", "open_rate": o, "close_rate": c,
            "amount": money, "stake_amount": o * money / 10, "leverage": 10.0, "profit_abs": net,
            "profit_ratio": net / (o * money / 10), "exit_reason": reason, "enter_tag": f"t{i}",
            "is_short": short, "fee_open": FEE, "fee_close": FEE, "funding_fees": 0.0,
            "trade_duration": 30, "initial_stop_loss_abs": o, "stop_loss_abs": o,
            "max_rate": max(o, c), "min_rate": min(o, c),
        })
    wins = sum(1 for n in EXPECTED_NET if n > 0)
    stats = {"strategy": {"Demo": {
        "trades": trades, "starting_balance": WALLET, "total_trades": len(trades), "wins": wins,
        "losses": len(trades) - wins, "draws": 0, "profit_total_abs": cum, "profit_total": cum / WALLET,
        "stake_currency": "USD", "final_balance": WALLET + cum,
    }}}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("backtest-result.json", json.dumps(stats))
    buf.seek(0)
    return buf


@pytest.mark.parametrize("pv", POINT_VALUES)
def test_freqtrade_vysledok_sa_normalizuje_na_kusy_a_sedi_s_emulatorom(pv, tmp_path):
    pytest.importorskip("pandas")
    from tester.webapp.runner import result_from_zip

    path = tmp_path / "bt.zip"
    path.write_bytes(_freqtrade_zip(pv).getvalue())
    summary, rows, _ = result_from_zip(path)
    emu = _emu_summary(pv)
    assert [r["amount"] for r in rows] == pytest.approx([m / pv for *_x, m, _r in TRADES])
    assert all(r["point_value"] == pv for r in rows)
    for k in ("break_even_pct", "pnl_abs", "gross_abs", "volume_abs", "max_drawdown_abs",
              "max_drawdown_pct"):
        assert summary[k] == pytest.approx(emu[k], abs=0.011), k
    # peniaze obchodu z normalizovaného záznamu = to, čo Freqtrade spočítal
    assert [row_money(r).net for r in rows] == pytest.approx(EXPECTED_NET, abs=1e-9)


@pytest.mark.parametrize("pv", POINT_VALUES)
def test_monte_carlo(pv):
    pytest.importorskip("numpy")
    from tester import montecarlo as mc

    def run(p):
        return mc.analyze(_emu_rows(p) * 6, fee_pct=FEE * 100, iterations=300, seed=1,
                          account=WALLET, risk_ref=25.0, risk=50.0, block=1)

    r, ref = run(pv), run(1.0)
    assert r["gross"] == pytest.approx(EXPECTED_GROSS * 6, abs=1e-6)
    assert r["volume"] == pytest.approx(EXPECTED_VOLUME * 6, abs=1e-6)
    assert r["break_even"]["observed"] == pytest.approx(ref["break_even"]["observed"])
    assert r["net"]["observed"] == pytest.approx(sum(EXPECTED_NET) * 6 * 2, abs=1e-6)
    for k in ("drawdown_abs", "drawdown_pct"):
        assert r["account"][k]["observed"] == pytest.approx(ref["account"][k]["observed"]), k
        assert r["account"][k]["median"] == pytest.approx(ref["account"][k]["median"]), k


@pytest.mark.parametrize("pv", POINT_VALUES)
def test_analytika(pv):
    from tester import analytics as an

    rows = _emu_rows(pv)
    gross, volume = an.gross_and_volume(rows)
    assert gross == pytest.approx(EXPECTED_GROSS) and volume == pytest.approx(EXPECTED_VOLUME)
    assert an.break_even_pct(rows) == an.break_even_pct(_emu_rows(1.0))
    assert gross_and_volume(rows) == (gross, volume)
    assert summary_money(rows, WALLET)["break_even_pct"] == _emu_summary(pv)["break_even_pct"]


@pytest.mark.parametrize("pv", POINT_VALUES)
def test_portfolio_a_prop(pv):
    from tester import portfolio as pf
    from tester import prop

    v, ref = (pf.equity_curve(_emu_rows(p), risk_pct=1.0, account=WALLET) for p in (pv, 1.0))
    assert v["trades"] == len(TRADES) and v["skipped"] == 0
    for k in ("final", "max_drawdown_pct", "return_pct"):
        assert v[k] == pytest.approx(ref[k]), k
    # prvý obchod: riziko 1 % z 1000 = 10 na stop 2 % pod vstupom -> 5 peňazí za bod
    prvy = _emu_rows(pv)[0]
    assert prop._pnl(prvy, WALLET, 1.0) == pytest.approx(
        trade_money(100.0, 110.0, 5.0, is_short=False, fee_open=FEE).net)


# --------------------------------------------------------------------------- #
# Freqtrade: stake a zisk v mene účtu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("pv,rate,leverage,qty", [
    (1.0, 79419.5, 20.0, 1.0), (2.0, 21000.25, 10.0, 3.0), (100.0, 2650.3, 20.0, 2.0),
    (100_000.0, 1.08517, 30.0, 2.0),
])
def test_freqtrade_stake_a_zisk_s_contract_size(pv, rate, leverage, qty):
    """Adaptér pýta stake za `qty` kontraktov; Freqtrade z neho spraví množstvo v základnej
    mene, oreže ho na krok kontraktu (contractSize = hodnota bodu, burza Tester) a zisk
    počíta z neho. Musí vyjsť presne qty kontraktov a peniaze ako `trade_money`."""
    pytest.importorskip("freqtrade")
    from datetime import datetime, timedelta, timezone

    from freqtrade.enums import TradingMode
    from freqtrade.exchange import amount_to_contract_precision
    from freqtrade.persistence import LocalTrade

    from tradebot.adapters.freqtrade.base import TradebotStrategyBase
    from tradebot.adapters.freqtrade.runner import SignalRow
    from tester import ftexchange

    pair = PAIRS[pv]
    market = {m["symbol"]: m for m in ftexchange.markets()}[pair]
    assert market["contractSize"] == pv

    s = TradebotStrategyBase.__new__(TradebotStrategyBase)
    row = SignalRow(enter_long=1, entry=rate, stop_loss=rate * 0.99, take_profit=rate * 1.01,
                    qty=qty, in_trade_window=True)
    s._signal = lambda *_a, **_k: row
    s.ai_scale = lambda *_a, **_k: 1.0
    when = datetime(2025, 1, 6, tzinfo=timezone.utc)
    stake = s.custom_stake_amount(pair, when, rate, 1.0, None, 1e15, leverage, "t", "long")

    # to isté, čo robí freqtrade/optimize/backtesting.py::_enter_trade
    step = market["precision"]["amount"]
    amount = amount_to_contract_precision(stake / rate * leverage, step, 4, pv)
    assert amount / pv == pytest.approx(qty)

    exit_rate = rate * 0.997
    trade = LocalTrade(pair=pair, open_rate=rate, amount=amount, stake_amount=amount * rate / leverage,
                       fee_open=FEE, fee_close=FEE, is_short=True, leverage=leverage,
                       trading_mode=TradingMode.FUTURES, contract_size=pv, open_date=when,
                       close_date=when + timedelta(hours=1), exchange="tester", is_open=True,
                       amount_precision=step, precision_mode=4, price_precision=0.00001,
                       precision_mode_price=4)
    ocakavane = trade_money(rate, exit_rate, qty, is_short=True, point_value=pv, fee_open=FEE)
    assert trade.calc_profit(exit_rate) == pytest.approx(ocakavane.net, rel=1e-6)
    assert trade.stake_amount == pytest.approx(ocakavane.notional_open / leverage, rel=1e-9)


# --------------------------------------------------------------------------- #
# prepočet starých behov
# --------------------------------------------------------------------------- #


def _record(pair: str, engine: str, summary: dict, wallet: float = WALLET) -> dict:
    return {"id": "20260910-090140-abcdef", "status": "done",
            "settings": {"pair": pair, "engine": engine, "wallet": wallet},
            "result": {**summary, "starting_balance": wallet}, "series": {"equity": []}}


def test_prepocet_opravi_stary_suhrn_emulatora():
    """Starý emulátor: obchody správne, objem v súhrne bez hodnoty bodu (GBPJPY 336,9 %)."""
    from tester.recompute import recompute_run

    rows = [{k: v for k, v in r.items() if k != "point_value"} for r in _emu_rows(100_000.0)]
    zly = dict(_emu_summary(100_000.0))
    zly["volume_abs"] = round(EXPECTED_VOLUME / 100_000.0, 2)
    zly["break_even_pct"] = round(EXPECTED_GROSS / (EXPECTED_VOLUME / 100_000.0) * 100, 4)
    r = recompute_run(_record("EURUSD/USD", "multicharts", zly), rows)
    assert r.changes["break_even_pct"][1] == _emu_summary(1.0)["break_even_pct"]
    assert "pnl_abs" not in r.changes                           # zisk obchodov bol dobrý
    assert r.trades_changed == len(rows) and all(t["point_value"] == 100_000.0 for t in r.trades)
    assert [t["profit_abs"] for t in r.trades] == [t["profit_abs"] for t in rows]


def test_prepocet_starého_freqtrade_behu_dopocita_peniaze_a_varuje():
    """Starý Freqtrade CFD beh (spot): kusy dobré, zisk bez hodnoty bodu."""
    from tester.recompute import recompute_run

    rows = []
    for (o, c, short, money, reason), i in zip(TRADES, range(len(TRADES))):
        qty = money / 100.0
        smer = -1 if short else 1
        rows.append({"open_date": f"2025-01-06T{i:02d}:00:00+00:00", "close_date": f"2025-01-06T{i:02d}:30:00+00:00",
                     "open_rate": o, "close_rate": c, "amount": qty, "is_short": short, "leverage": 1.0,
                     "fee_open": FEE, "fee_close": FEE, "exit_reason": reason,
                     "profit_abs": (c - o) * smer * qty - (o + c) * qty * FEE})
    zly = summary_money(rows, WALLET)
    r = recompute_run(_record("XAU/USD", "freqtrade", zly), rows)
    assert r.summary["pnl_abs"] == pytest.approx(round(sum(EXPECTED_NET), 2), abs=0.011)
    assert r.summary["break_even_pct"] == _emu_summary(100.0)["break_even_pct"]
    assert r.summary["max_drawdown_abs"] == _emu_summary(100.0)["max_drawdown_abs"]
    assert r.warning and r.series_equity


def test_prepocet_krypto_behu_nemeni_obchody():
    from tester.recompute import recompute_run

    rows = _emu_rows(1.0)
    r = recompute_run(_record("BTC/USDT:USDT", "multicharts", _emu_summary(1.0)), rows)
    assert not r.changed and r.trades_changed == 0
