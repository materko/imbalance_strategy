"""Walk-forward so zámkom podľa SMERNICE V2 (krok 6, zadanie U8).

Okná sú len v rámci L trhu (§1, `tester.register`):

* **ES a 6E:** učenie 24 mesiacov, test 6, posun 6;
* **MNQ, MYM, BTC a MGC:** učenie 18 mesiacov, test 6, posun 6.

V každom okne sa preladí **tou istou mriežkou** (`--param`, parametre musia byť v hlavičke hypotézy, „## Mriežka“)
natívnym hyperoptom C# jadra s rozpočtom ≤ 300 / počet okien epoch. WF sa pre hypotézu púšťa **raz**
(`register.lock_wf`). Jeho behy idú do registra so zdrojom `wf` a do N pre DSR sa nerátajú.

Brány (`wf_gates`):

* spojená OOS krivka PF ≥ 1,15;
* WFE (ročný OOS výnos / ročný výnos v ladení) ≥ 0,5;
* ≥ 75 % kúskov v pluse (pri < 4 kúskoch všetky);
* žiaden parameter sa medzi susednými oknami nezmení o viac ako ½ rozsahu mriežky.

Výstup (`--out`) nesie aj denný OOS PnL (každý pracovný deň, bez obchodu 0) pre Sortino (U9).

    PY -m tester.walkforward --hypothesis orb-pondelok --strategy orbnet --instrument mnq_databento \\
        --param rrRatio=1.5:3:0.5 --param orMinutes=5,15 --out wf.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from .overfit import GATES, sortino

__all__ = ["wf_windows", "train_count", "wf_gates", "daily_pnl", "BUDGET", "main"]

#: Rozpočet epoch celého WF (V2 U8.2: ≤ 300 / počet okien na okno).
BUDGET = 300


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1) if d.day == 1 else date(d.year + y, m + 1, min(d.day, 28))


def wf_windows(market: str) -> list[str]:
    """Šesťmesačné kúsky L trhu za sebou (koniec bez); zvyšok kratší ako 3 mesiace sa pridá k poslednému."""
    from .register import MARKETS

    m = MARKETS[market]
    od = date.fromisoformat(m.L[0])
    koniec = date.fromisoformat(m.L[1]) + timedelta(days=1)
    okna: list[tuple[date, date]] = []
    while od < koniec:
        do = min(_add_months(od, 6), koniec)
        if (koniec - do).days < 90:
            do = koniec
        okna.append((od, do))
        od = do
    return [f"{a:%Y%m%d}-{b:%Y%m%d}" for a, b in okna]


def train_count(market: str) -> int:
    """Koľko 6-mesačných kúskov je učenie (24 -> 4, 18 -> 3)."""
    from .register import MARKETS

    return MARKETS[market].wf[0] // 6


def daily_pnl(trades: Sequence[dict[str, Any]], windows: Sequence[str]) -> dict[str, float]:
    """Denný PnL OOS: každý pracovný deň testovacích okien, deň bez obchodu = 0 (deň zatvorenia obchodu)."""
    out: dict[str, float] = {}
    for w in windows:
        a, b = (datetime.strptime(x, "%Y%m%d").date() for x in w.split("-"))
        d = a
        while d < b:
            if d.weekday() < 5:
                out.setdefault(d.isoformat(), 0.0)
            d += timedelta(days=1)
    for t in trades:   # obchod zavretý cez víkend (Globex, krypto) pridá svoj deň - nič sa nestratí
        c = str(t.get("close") or "")[:10]
        if len(c) == 10:
            out[c] = out.get(c, 0.0) + float(t.get("pnl") or 0.0)
    return dict(sorted(out.items()))


def _span(knob: Any) -> float | None:
    lo, hi = getattr(knob, "low", None), getattr(knob, "high", None)
    if lo is None or hi is None or getattr(knob, "choices", None) is not None:
        return None
    try:
        return float(hi) - float(lo)
    except (TypeError, ValueError):
        return None


def wf_gates(folds: Sequence[dict[str, Any]], knobs: Sequence[Any] = (), *, wallet: float = 10000,
             limits: dict[str, float] | None = None) -> dict[str, Any]:
    """Brány WF z foldov `native_hyperopt.walk_forward(..., keep_trades=True)`."""
    lim = {**GATES, **(limits or {})}
    trades = [t for f in folds for t in (f.get("trades") or [])]
    gross_win = sum(float(t["pnl"]) for t in trades if float(t.get("pnl") or 0) > 0)
    gross_loss = -sum(float(t["pnl"]) for t in trades if float(t.get("pnl") or 0) < 0)
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else None)
    pnl_folds = [sum(float(t.get("pnl") or 0) for t in (f.get("trades") or [])) for f in folds]
    kladne = sum(1 for p in pnl_folds if p > 0)
    n = len(folds)
    need = n if n < 4 else lim["wf_positive_min"] * n
    oos_days = sum(int(f.get("oos_days") or 0) for f in folds)
    is_days = sum(int(f.get("is_days") or 0) for f in folds)
    oos_ann = (sum(pnl_folds) / wallet * 100) / (oos_days / 365.25) if oos_days else None
    is_ann = (sum(float(f.get("is_pnl_pct") or 0) for f in folds)) / (is_days / 365.25) if is_days else None
    wfe = oos_ann / is_ann if oos_ann is not None and is_ann not in (None, 0) and is_ann > 0 else None
    # stabilita: zmena parametra medzi susednými oknami ≤ ½ rozsahu mriežky
    spans = {getattr(k, "name", ""): _span(k) for k in knobs}
    skoky: list[str] = []
    for a, b in zip(folds, folds[1:]):
        pa, pb = a.get("params") or {}, b.get("params") or {}
        for name, span in spans.items():
            if not span or name not in pa or name not in pb:
                continue
            try:
                d = abs(float(pb[name]) - float(pa[name]))
            except (TypeError, ValueError):
                continue
            if d > span / 2 + 1e-12:
                skoky.append(f"{name} fold {a.get('fold')}→{b.get('fold')}: {pa[name]}→{pb[name]} (> ½ rozsahu {span:g})")
    windows = [str(f.get("test")) for f in folds if f.get("test")]
    daily = daily_pnl(trades, windows)
    so = sortino([v / wallet for v in daily.values()]) if daily else None
    out = {
        "folds": n, "trades": len(trades), "pf_oos": pf, "positive": kladne, "positive_need": need,
        "wfe": wfe, "oos_annual_pct": oos_ann, "is_annual_pct": is_ann, "param_jumps": skoky, "sortino_oos": so,
        "pf_ok": pf is not None and pf >= lim["wf_pf_min"],
        "wfe_ok": wfe is not None and wfe >= lim["wfe_min"],
        "positive_ok": n > 0 and kladne >= need - 1e-9,
        "stable_ok": not skoky,
        "daily": daily,
    }
    out["passed"] = bool(n and out["pf_ok"] and out["wfe_ok"] and out["positive_ok"] and out["stable_ok"])
    return out


def verdict(g: dict[str, Any]) -> str:
    def f(v: Any, d: int = 2) -> str:
        return "—" if v is None else f"{v:.{d}f}"

    stav = "WALK-FORWARD DRZI" if g["passed"] else "WALK-FORWARD NEDRZI"
    return (f"{stav}: PF OOS {f(g['pf_oos'])} (≥ {GATES['wf_pf_min']}), WFE {f(g['wfe'])} (≥ {GATES['wfe_min']}), "
            f"v pluse {g['positive']}/{g['folds']} kúskov (treba {g['positive_need']:g}), "
            + ("parametre stabilné" if g["stable_ok"] else f"skoky parametrov: {'; '.join(g['param_jumps'])}")
            + f", Sortino OOS {f(g['sortino_oos'])}")


def main(argv: list[str] | None = None) -> int:
    from tradebot.core.candles import timeframe_minutes
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec

    from . import register as rg
    from .hyperopt import build_plan
    from .native_hyperopt import NativeRunner, walk_forward

    ap = argparse.ArgumentParser(prog="python -m tester.walkforward", description=__doc__.split("\n\n")[0])
    ap.add_argument("--hypothesis", required=True, help="hypotéza registra (zámok WF, hlavička s mriežkou)")
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--instrument", required=True, help="kľúč nástroja (mnq_databento, es_databento, …)")
    ap.add_argument("--profile")
    ap.add_argument("--timeframe")
    ap.add_argument("--param", action="append", default=[], metavar="POLE=OD:DO:KROK|A,B,C")
    ap.add_argument("--goal", default="break_even")
    ap.add_argument("--min-trades", type=int)
    ap.add_argument("--sampler", default="tpe")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--wallet", type=float, default=10000)
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--out", help="JSON s foldmi, bránami a denným OOS PnL")
    ap.add_argument("--dry-run", action="store_true", help="len okná a rozpočet, nič nespúšťať ani nezamykať")
    a = ap.parse_args(argv)
    market = rg.market_of_instrument(a.instrument)
    if market is None:
        ap.error(f"nástroj {a.instrument} nemá v SMERNICI V2 §1 rozdelenie (L) - walk-forward nejde")
    okna = wf_windows(market)
    k = train_count(market)
    nfold = len(okna) - k
    if nfold < 1:
        ap.error(f"L {market} má len {len(okna)} kúskov po 6 mesiacov - na učenie {k} a test nestačí")
    epochs = max(1, BUDGET // nfold)
    print(f"walk-forward {a.hypothesis} {a.strategy} {market}: {len(okna)} kúskov po 6 mes., učenie {k * 6} mes., "
          f"{nfold} foldov po {epochs} epoch (rozpočet {BUDGET})")
    print("  " + ", ".join(okna))
    space = dict(p.split("=", 1) for p in a.param)
    if not space:
        ap.error("aspoň jeden --param (zmrazená mriežka z hlavičky)")
    try:
        rg.require_header(a.hypothesis)
        mriezka = rg._sections(rg.header_path(a.hypothesis).read_text(encoding="utf-8")).get("Mriežka", "")
        chyba = [n for n in space if n not in mriezka]
        if chyba:
            raise rg.RegisterError(f"parametre {', '.join(chyba)} nie sú v hlavičke („## Mriežka“) - mriežka je zmrazená")
        if a.dry_run:
            return 0
        rg.lock_wf(a.hypothesis)
    except rg.RegisterError as e:
        print(f"chyba: {e}")
        return 2
    plan = build_plan(space, strategy=a.strategy, goal=a.goal, min_trades=a.min_trades)
    spec = get_spec(a.strategy)
    tf = timeframe_minutes(a.timeframe or spec.default_timeframe)
    runner = NativeRunner(a.strategy, INSTRUMENTS[a.instrument], tf, a.fee, a.jobs)
    wf = walk_forward(runner, plan, a.profile, okna, epochs=epochs, sampler=a.sampler, seed=a.seed, wallet=a.wallet,
                      train_windows=k, keep_trades=True)
    g = wf_gates(wf.folds, plan.knobs, wallet=a.wallet)
    print("\n" + verdict(g))
    for e in wf.epochs:   # behy WF do registra (zdroj wf, do N sa nerátajú)
        try:
            rg.append(a.hypothesis, {"source": "wf", "key": a.strategy, "market": market, "tf": f"{tf}m",
                                     "params": e.params, "timerange": None, "pf": e.profit_factor, "trades": e.trades,
                                     "fold": e.fold})
        except rg.RegisterError as exc:
            print(f"POZOR: register: {exc}")
            break
    if a.out:
        Path(a.out).write_text(json.dumps({
            "mode": "walkforward_v2", "hypothesis": a.hypothesis, "strategy": a.strategy, "market": market,
            "windows": okna, "train_chunks": k, "epochs_per_fold": epochs, "folds": wf.folds, "gates": g,
            "verdict": verdict(g), "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"uložené: {a.out}")
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
