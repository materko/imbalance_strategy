"""Testy robustnosti pre smernicu — tri body, ktoré hovoria, či kandidát nie je náhoda zo skúšania.

1. **Dvojnásobný poplatok** — tie isté obchody prepočítané s `fee_mult` × poplatok (poplatok signály nemení).
2. **Vstup o sviečku neskôr** — emulátor MultiCharts s `entry_delay=1`: broker dostane zadanie aj zrušenie
   vstupného orderu o bar neskôr (latencia). Edge, ktorý závisí od presného časovania, tu zmizne.
3. **Deflated Sharpe Ratio** (Bailey & López de Prado, 2014) — pravdepodobnosť, že skutočný Sharpe je nad nulou,
   keď sa najlepšie nastavenie vybralo z `trials` skúšok. Sharpe z denných výnosov všetkých okien spolu,
   so šikmosťou a špicatosťou; očakávané maximum `trials` nezávislých skúšok pri nulovom edgi
   (rozptyl Sharpe pod nulou = 1 / T). Skúšky z hľadania sú korelované → N je horná hranica, test je prísny.

Hranice (návrh do smernice, `PASS`): 2× poplatok PF ≥ 1,0 vo väčšine okien a spolu; vstup o sviečku neskôr
PF spolu ≥ 1,1 a aspoň 80 % PF bez posunu; DSR ≥ 0,95.

    PY -m tester.robust --profile tester/profiles/PRESIEL_SMERNICAMI_IBS_Entry_Zone_1.json \\
        --pair MNQ/USD --timeframe 3m --fee 1.755e-05 --trials 20710
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any

from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tradebot.core.config import load_profile
from tradebot.core.money import summary_money
from tradebot.core.types import INSTRUMENTS

from . import engines
from .webapp.market import instrument_for_pair

__all__ = ["WINDOWS", "deflated_sharpe", "robustness", "main"]

WINDOWS = ("20211001-20221001", "20221001-20231001", "20231001-20241001",
           "20240904-20250904", "20250904-20260904")
_EULER = 0.5772156649015329
_N = NormalDist()


def _ms(day: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def deflated_sharpe(daily: list[float], trials: int) -> dict[str, float]:
    """DSR z denných výnosov; `trials` = koľko nastavení sa skúšalo, kým sa toto vybralo."""
    t = len(daily)
    if t < 30:
        return {"sr": 0.0, "sr0": 0.0, "dsr": 0.0, "days": t}
    m = sum(daily) / t
    var = sum((x - m) ** 2 for x in daily) / (t - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd == 0:
        return {"sr": 0.0, "sr0": 0.0, "dsr": 0.0, "days": t}
    sr = m / sd
    skew = sum((x - m) ** 3 for x in daily) / t / sd ** 3
    kurt = sum((x - m) ** 4 for x in daily) / t / sd ** 4
    n = max(1, int(trials))
    if n > 1:
        e_max = (1 - _EULER) * _N.inv_cdf(1 - 1 / n) + _EULER * _N.inv_cdf(1 - 1 / (n * math.e))
        sr0 = math.sqrt(1.0 / t) * e_max
    else:
        sr0 = 0.0
    den = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    z = (sr - sr0) * math.sqrt(t - 1) / math.sqrt(den) if den > 0 else 0.0
    return {"sr": sr, "sr_annual": sr * math.sqrt(252), "sr0": sr0, "sr0_annual": sr0 * math.sqrt(252),
            "dsr": _N.cdf(z), "psr": _N.cdf(sr * math.sqrt(t - 1) / math.sqrt(den)) if den > 0 else 0.0,
            "days": t, "skew": skew, "kurt": kurt}


def _pf(rows: list[dict[str, Any]]) -> float:
    gp = sum(r["profit_abs"] for r in rows if r["profit_abs"] > 0)
    gl = -sum(r["profit_abs"] for r in rows if r["profit_abs"] < 0)
    return gp / gl if gl else (99.0 if gp else 0.0)


def _daily(rows: list[dict[str, Any]], wallet: float) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in rows:
        d = str(r["close_date"])[:10]
        out[d] = out.get(d, 0.0) + r["profit_abs"] / wallet
    return out


@dataclass
class Report:
    profile: str
    windows: list[dict[str, Any]] = field(default_factory=list)
    total: dict[str, Any] = field(default_factory=dict)
    dsr: dict[str, float] = field(default_factory=dict)
    verdict: dict[str, bool] = field(default_factory=dict)


def robustness(profile: str, pair: str, timeframe: str, fee: float, trials: int, *, fee_mult: float = 2.0,
               delay: int = 1, wallet: float = 100_000.0, windows=WINDOWS, m1=None, log=print) -> Report:
    import pandas as pd

    cfg, _ = load_profile(profile, engine=engines.MULTICHARTS)
    inst = INSTRUMENTS[instrument_for_pair(pair)]
    if m1 is None:
        m1 = pd.read_feather(engines.one_minute_file(inst))
    tf = int(timeframe.rstrip("m"))
    rep = Report(profile=str(profile))
    all_base, all_fee2, all_delay = [], [], []
    for w in windows:
        a, b = w.split("-")
        res, _ = emulate(cfg, inst, m1, tf, from_ms=_ms(a), to_ms=_ms(b), fee=fee)
        base = rows_from_trades(res.trades, inst, fee)
        fee2 = rows_from_trades(res.trades, inst, fee * fee_mult)
        res_d, _ = emulate(cfg, inst, m1, tf, from_ms=_ms(a), to_ms=_ms(b), fee=fee, entry_delay=delay)
        dl = rows_from_trades(res_d.trades, inst, fee)
        all_base += base
        all_fee2 += fee2
        all_delay += dl
        row = {"window": w, "trades": len(base), "pf": _pf(base), "pf_fee2": _pf(fee2),
               "trades_delay": len(dl), "pf_delay": _pf(dl),
               "be": summary_money(base, wallet).get("break_even_pct")}
        rep.windows.append(row)
        log(f"  {w}: {row['trades']} obch PF {row['pf']:.2f} | 2× poplatok {row['pf_fee2']:.2f} | "
            f"o sviečku neskôr {row['trades_delay']} obch PF {row['pf_delay']:.2f}")
    rep.total = {"pf": _pf(all_base), "pf_fee2": _pf(all_fee2), "pf_delay": _pf(all_delay),
                 "trades": len(all_base), "trades_delay": len(all_delay),
                 "win_fee2": sum(1 for r in rep.windows if r["pf_fee2"] >= 1.0),
                 "win_delay": sum(1 for r in rep.windows if r["pf_delay"] >= 1.0)}
    # denné výnosy cez všetky okná; prekrytie okien 4.–30. 9. 2025 sa započíta raz (posledný výskyt)
    daily = _daily(all_base, wallet)
    rep.dsr = deflated_sharpe([daily[d] for d in sorted(daily)], trials)
    t = rep.total
    rep.verdict = {
        "fee2": t["pf_fee2"] >= 1.0 and t["win_fee2"] >= 3,
        "delay": t["pf_delay"] >= 1.1 and t["pf_delay"] >= 0.8 * t["pf"],
        "dsr": rep.dsr.get("dsr", 0.0) >= 0.95,
    }
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.robust", description=__doc__.splitlines()[0])
    ap.add_argument("--profile", action="append", required=True, help="profil (dá sa zopakovať)")
    ap.add_argument("--pair", default="MNQ/USD")
    ap.add_argument("--timeframe", default="3m")
    ap.add_argument("--fee", type=float, default=1.755e-05)
    ap.add_argument("--trials", type=int, default=1, help="koľko kombinácií sa skúšalo (ranná tabuľka smernice)")
    ap.add_argument("--fee-mult", type=float, default=2.0)
    ap.add_argument("--delay", type=int, default=1)
    ap.add_argument("--json", help="zapíš výsledky do JSON")
    args = ap.parse_args(argv)
    import pandas as pd

    inst = INSTRUMENTS[instrument_for_pair(args.pair)]
    m1 = pd.read_feather(engines.one_minute_file(inst))
    out = []
    for p in args.profile:
        print(f"== {p}")
        rep = robustness(p, args.pair, args.timeframe, args.fee, args.trials, fee_mult=args.fee_mult,
                         delay=args.delay, m1=m1)
        t, d = rep.total, rep.dsr
        print(f"  spolu: PF {t['pf']:.2f} | 2× poplatok {t['pf_fee2']:.2f} ({t['win_fee2']}/5 okien ≥ 1) | "
              f"o sviečku neskôr {t['pf_delay']:.2f} ({t['win_delay']}/5) | Sharpe {d.get('sr_annual', 0):.2f} "
              f"vs prah {d.get('sr0_annual', 0):.2f} pri {args.trials} skúškach → DSR {d.get('dsr', 0):.3f}")
        print(f"  verdikt: {rep.verdict}")
        out.append(rep.__dict__)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
