"""Spracovanie výsledku behu: zip Freqtradu, beh v emulátore MultiCharts a počet signálov
z logu.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS

from .. import engines
from .command import tf_minutes
from .market import instrument_for_pair


#: `IBS NAS100/USD: 12445 barov, 7467 HTF barov, 147 zon, 13 signalov (13 long / 0 short)`
_SIGNALS_RE = re.compile(r"(\d+) signalov")


def entry_signals(log_lines: list[str]) -> int | None:
    """Koľko vstupných signálov engine vôbec vygeneroval — z logu adaptéra."""
    for line in reversed(log_lines):
        m = _SIGNALS_RE.search(line)
        if m:
            return int(m.group(1))
    return None


def zero_trade_warning(summary: dict, log_lines: list[str]) -> str | None:
    """Beh bez obchodov, hoci signály boli — Freqtrade odmietol každý vstup.

    Najčastejšie je to malá peňaženka pri `legacyPineSizing`: engine pýta množstvo
    v jednotkách po 1 USD/bod (na NAS100 desiatky jednotiek, nominál stovky tisíc),
    Freqtrade stake oreže na zostatok a vstup zahodí. Bez tohto riadka vyzerá beh ako
    platný výsledok „stratégia neobchoduje", čo je nepravda.
    """
    if summary.get("trades"):
        return None
    signals = entry_signals(log_lines)
    if not signals:
        return None
    return (f"engine dal {signals} vstupných signálov, ale nevznikol ani jeden obchod — "
            f"Freqtrade každý vstup odmietol. Skús väčšiu peňaženku (profil s `legacyPineSizing` "
            f"pýta nominál v stovkách tisíc) alebo páku; v logu je celý priebeh.")


_TRADE_COLS = (
    "open_date", "close_date", "open_rate", "close_rate", "amount", "stake_amount", "leverage",
    "profit_abs", "profit_ratio", "exit_reason", "enter_tag", "is_short", "fee_open", "fee_close",
    "funding_fees", "trade_duration", "initial_stop_loss_abs", "stop_loss_abs", "max_rate", "min_rate",
)


def result_from_zip(zip_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """(súhrn, obchody, série pre graf) z výsledkového zipu Freqtradu.

    Obchody sa normalizujú na záznam spoločný s emulátorom MultiCharts: `amount` sú kusy
    enginu (kontrakty, loty), nie základná mena Freqtradu (`kusy × contractSize`),
    a `point_value` je výslovne v zázname. Peňažná časť súhrnu (gross, objem, break-even,
    PnL, drawdown) sa počíta z nich jedinou definíciou `tradebot.core.money` — rovnako
    ako v emulátore, takže ten istý obchod dá v oboch enginoch tie isté peniaze.
    """
    import pandas as pd

    from tradebot.core.money import point_value_for_pair, row_money, summary_money

    from ..report import load

    stats, trades, change = load(zip_path)
    start = float(stats["starting_balance"])

    rows: list[dict[str, Any]] = []
    if not trades.empty:
        t = trades.sort_values("close_date")
        for r in t.to_dict("records"):
            row = {k: r.get(k) for k in _TRADE_COLS if k in r}
            for k in ("open_date", "close_date"):
                if row.get(k) is not None:
                    row[k] = pd.Timestamp(row[k]).isoformat()
            for k, v in list(row.items()):
                if hasattr(v, "item"):
                    row[k] = v.item()
            # Freqtrade drží množstvo v základnej mene; burza Tester má contractSize =
            # hodnota bodu, takže kusy enginu sú množstvo / hodnota bodu a peniaze
            # (cena × množstvo) ostanú presne tie, ktoré Freqtrade spočítal.
            pv = point_value_for_pair(r.get("pair")) or 1.0
            row["amount"] = float(row.get("amount") or 0.0) / pv
            row["point_value"] = pv
            m = row_money(row)
            row["gross_abs"] = round(m.gross, 4)
            row["fees_abs"] = round(m.fees, 4)
            rows.append(row)

    money = summary_money(rows, start)
    summary = {
        "trades": int(stats["total_trades"]),
        "wins": int(stats["wins"]), "losses": int(stats["losses"]), "draws": int(stats.get("draws", 0)),
        "winrate": round(100.0 * stats["wins"] / stats["total_trades"], 2) if stats["total_trades"] else 0.0,
        **{k: money[k] for k in ("pnl_abs", "pnl_pct", "profit_factor", "max_drawdown_abs",
                                 "max_drawdown_pct", "starting_balance", "final_balance",
                                 "gross_abs", "volume_abs", "break_even_pct", "exits")},
        "stake_currency": stats.get("stake_currency", "USDT"),
        "market_change_pct": round(float(stats.get("market_change", 0.0)) * 100.0, 3),
        "backtest_start": stats.get("backtest_start"),
        "backtest_end": stats.get("backtest_end"),
        "holding_avg": str(stats.get("holding_avg", "")),
    }

    series: dict[str, Any] = {"equity": [], "market": []}
    if not trades.empty:
        t = trades.sort_values("close_date")
        pct = (t["profit_abs"] / start * 100.0)
        series["equity"] = [
            [pd.Timestamp(ts).isoformat(), round(float(p), 4), round(float(c), 4)]
            for ts, p, c in zip(t["close_date"], pct, pct.cumsum())
        ]
    if change is not None and not change.empty:
        bh = change.set_index("date")["rel_mean"].resample("1D").last().dropna()
        series["market"] = [[pd.Timestamp(ts).isoformat(), round(float(v) * 100.0, 4)] for ts, v in bh.items()]

    return summary, rows, series


def timerange_ms(timerange: str) -> tuple[int | None, int | None]:
    """`YYYYMMDD-YYYYMMDD` → (od, do) v ms UTC; prázdna strana je `None`."""
    start_s, _, end_s = (timerange or "").partition("-")
    def ms(text: str) -> int | None:
        if not text:
            return None
        return int(datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    return ms(start_s), ms(end_s)


def run_multicharts(params: dict[str, Any], settings: dict[str, Any], profile: Path, *,
                    log: Callable[[str], None], should_stop: Callable[[], bool] = lambda: False,
                    chart_out: Path | None = None):
    """Beh cez emulátor MultiCharts — jeden kód pre backtest aj prepočet grafu.

    Vracia `(súhrn, obchody, séria, hlavička kresieb | None)`, alebo `None`, keď sa beh
    zrušil. Kresby sa zapíšu len s `chart_out` (bod mriežky ich nepotrebuje).
    """
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize, write_chart
    from tradebot.core import DrawRegistry

    inst = INSTRUMENTS[instrument_for_pair(settings["pair"])]
    cfg, _ = load_profile(profile, engine=engines.MULTICHARTS)
    tf = settings.get("timeframe") or "3m"
    from_ms, to_ms = timerange_ms(settings["timerange"])
    data_path = engines.one_minute_file(inst)
    log(f"$ emulator MultiCharts {inst.exchange_symbol} {tf} {settings['timerange']} ({data_path.name})")
    if not data_path.exists():
        raise FileNotFoundError(
            f"chýbajú 1m dáta {data_path} — stiahni ich (download-data.sh) alebo naimportuj "
            f"(`python -m tester.dukas_import <csv> --symbol {inst.exchange_symbol}`)")

    import pandas as pd

    m1 = pd.read_feather(data_path)
    registry = DrawRegistry()
    fee = float(settings.get("fee") or 0.0)
    result, mc_runner = emulate(
        cfg, inst, m1, tf_minutes(tf), from_ms=from_ms, to_ms=to_ms,
        log=log, should_stop=should_stop,
        registry=registry, fee=fee,  # zisk obchodu pre maxDailyWins
    )
    if should_stop():
        return None
    wallet = float(settings.get("wallet") or 10000)
    leverage = float(params.get("leverage") or 1.0)
    rows = rows_from_trades(result.trades, inst, fee, leverage)
    summary, series = summarize(rows, wallet, result, currency=inst.quote_currency)
    header = None
    if chart_out is not None:
        header = write_chart(mc_runner, registry, result, settings["pair"], tf, chart_out)
        log(f"kresby: {header.get('counts')}")
    return summary, rows, series, header
