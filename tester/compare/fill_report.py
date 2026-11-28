"""Report fill v1 proti fill v2 (zadanie U4, akceptácia): PF, obchody, zisk a podiel TP „dotykov“ na L trhu.

TP dotyk = výstup na TP, pri ktorom bol TP presne na high (long) / low (short) minúty výstupu — v1 ho plní, v2 nie
(cena musí prejsť o tick, pri CFD o spread). CFD trh nemá v §1 vlastné rozdelenie; berie sa L príbuzného futures trhu
(US100 → MNQ, US500 → ES, XAUUSD → MGC) v rozsahu dát Dukascopy.

    PY -m tester.compare.fill_report                 # predvolená sada zadania U4
    PY -m tester.compare.fill_report --write         # aj docs/merania/<dnes>-fill-v2.md
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from typing import Any

#: (stratégia, nástroj, profil) — sada zadania U4
CASES = [
    ("ibsentrynet", "mnq_databento", "ZAKLAD_MNQ"),
    ("ibsentrynet", "nas100_dukascopy", "ZAKLAD_MNQ"),
    ("vwaporbnet", "mnq_databento", "ZAKLAD_MNQ"),
    ("noanet", "mnq_databento", "ZAKLAD_MNQ"),
    ("nyvaesnet", "us500_dukascopy", "ZAKLAD_ES"),
    ("spravynet", "xau_dukascopy", "ZAKLAD_MGC"),
]
#: CFD -> futures trh, ktorého L sa použije
CFD_MARKET = {"nas100_dukascopy": "MNQ", "us500_dukascopy": "ES", "xau_dukascopy": "MGC", "dj30_dukascopy": "MYM"}


def _l_range(inst_key: str) -> tuple[int, int, str]:
    from tester.register import MARKETS, market_of_instrument

    market = market_of_instrument(inst_key) or CFD_MARKET.get(inst_key)
    if market is None:
        raise ValueError(f"{inst_key}: trh bez L")
    m = MARKETS[market]
    a = int(datetime.fromisoformat(m.L[0]).replace(tzinfo=timezone.utc).timestamp() * 1000)
    b = int(datetime.fromisoformat(m.L[1]).replace(tzinfo=timezone.utc).timestamp() * 1000) + 86_400_000
    return a, b, market


def _touch_share(trades: list[dict[str, Any]], m1) -> tuple[int, int]:
    """(TP výstupov, z toho dotykov) — TP presne na high/low minúty výstupu."""
    idx = {int(t): i for i, t in enumerate(m1["ms"])}
    tp = touch = 0
    for t in trades:
        if t["reason"] != "take_profit":
            continue
        tp += 1
        i = idx.get(int(t["close_ms"]))
        if i is None:
            continue
        hi, lo = float(m1["high"].iat[i]), float(m1["low"].iat[i])
        if (t["dir"] == 1 and abs(hi - t["take_profit"]) < 1e-9) or (t["dir"] == -1 and abs(lo - t["take_profit"]) < 1e-9):
            touch += 1
    return tp, touch


def run_case(strategy: str, inst_key: str, profile: str) -> dict[str, Any]:
    import pandas as pd

    from tradebot.core.candles import timeframe_minutes
    from tradebot.core.fill import model_for
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec
    from tester import engines
    from tester.compare.csharp_backtest import run_csharp
    from tester.native import _trades, rows_from_trades

    inst = INSTRUMENTS[inst_key]
    a, b, market = _l_range(inst_key)
    m1 = pd.read_feather(engines.one_minute_file(inst))
    d = pd.to_datetime(m1["date"], utc=True)
    a = max(a, int(d.iloc[0].timestamp() * 1000))
    b = min(b, int(d.iloc[-1].timestamp() * 1000))
    m1 = m1.assign(ms=(d.astype("int64") // 1_000_000))
    tf = timeframe_minutes(get_spec(strategy).default_timeframe)

    out: dict[str, Any] = {"strategy": strategy, "instrument": inst_key, "profile": profile, "market_L": market,
                           "from": datetime.fromtimestamp(a / 1000, timezone.utc).date().isoformat(),
                           "to": datetime.fromtimestamp(b / 1000, timezone.utc).date().isoformat()}
    for mode in ("v1", "v2"):
        fill = model_for(inst_key, mode)
        fee = 0.0   # v1 bez poplatku (čistý rozdiel plnenia), v2 s nákladom z tabuľky
        res = run_csharp(strategy, profile, inst, tf, a, b, fee, {}, fill=fill)
        if "error" in res:
            out[mode] = {"error": res["error"]}
            continue
        rows = rows_from_trades(_trades(res), inst, fee)
        gp = sum(r["profit_abs"] for r in rows if r["profit_abs"] > 0)
        gl = -sum(r["profit_abs"] for r in rows if r["profit_abs"] < 0)
        tp, touch = _touch_share(res["trades"], m1)
        out[mode] = {"trades": len(rows), "pf": gp / gl if gl > 0 else None, "pnl": round(gp - gl, 2),
                     "tp": tp, "tp_touch": touch, "touch_share": touch / tp if tp else None,
                     "rejected": int(res.get("rejected") or 0)}
    return out


def markdown(rows: list[dict[str, Any]]) -> str:
    def f(v: Any, d: int = 2) -> str:
        return "—" if v is None else (f"{v:.{d}f}" if isinstance(v, float) else str(v))

    lines = [f"# Fill v1 proti fill v2 ({date.today().isoformat()})", "",
             "*Zadanie U4, akceptácia. Natívny emulátor MultiCharts (C#), profily ZAKLAD_<trh>, obdobie L trhu (§1); "
             "CFD na L príbuzného futures trhu v rozsahu dát Dukascopy. v1 bez poplatku, v2 s nákladom z tabuľky "
             "`tradebot/core/fill_v2.json`. TP dotyk = TP presne na high/low minúty výstupu.*", "",
             "```", "python -m tester.compare.fill_report --write", "```", "",
             "| stratégia | nástroj | obdobie | obchody v1 / v2 | PF v1 / v2 | zisk v1 / v2 | TP dotyky v1 | odmietnuté v2 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a, b = r.get("v1") or {}, r.get("v2") or {}
        lines.append(f"| {r['strategy']} | {r['instrument']} | {r['from']} – {r['to']} | {f(a.get('trades'))} / {f(b.get('trades'))} "
                     f"| {f(a.get('pf'))} / {f(b.get('pf'))} | {f(a.get('pnl'), 0)} / {f(b.get('pnl'), 0)} "
                     f"| {f((a.get('touch_share') or 0) * 100, 0) if a.get('tp') else '—'} % ({a.get('tp_touch', 0)}/{a.get('tp', 0)}) "
                     f"| {b.get('rejected', '—')} |")
    lines += ["", "## Záver", "", "_(dopíše človek: či je v2 pripravený byť predvolený — SMERNICA V2 U4)_", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from tradebot.core.paths import MERANIA_DIR

    ap = argparse.ArgumentParser(prog="python -m tester.compare.fill_report", description=__doc__.split("\n\n")[0])
    ap.add_argument("--write", action="store_true", help="zapísať docs/merania/<dnes>-fill-v2.md")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rows = []
    for s, i, p in CASES:
        try:
            r = run_case(s, i, p)
        except Exception as exc:  # noqa: BLE001 - jeden prípad nesmie zhodiť report
            r = {"strategy": s, "instrument": i, "profile": p, "from": "—", "to": "—", "v1": {"error": str(exc)},
                 "v2": {"error": str(exc)}}
        rows.append(r)
        v1, v2 = r.get("v1") or {}, r.get("v2") or {}
        print(f"{s:<13} {i:<17} v1 {v1.get('trades')} obch PF {v1.get('pf')} | v2 {v2.get('trades')} obch PF {v2.get('pf')}"
              + (f" | chyba {v1.get('error')}" if v1.get("error") else ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
    if a.write:
        out = MERANIA_DIR / f"{date.today().isoformat()}-fill-v2.md"
        out.write_text(markdown(rows), encoding="utf-8")
        print(f"zapísané: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
