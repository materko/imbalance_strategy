"""Testy robustnosti pre smernicu — tri body, ktoré hovoria, či kandidát nie je náhoda zo skúšania.

1. **Dvojnásobný poplatok** — tie isté obchody prepočítané s `fee_mult` × poplatok (poplatok signály nemení).
2. **Vstup o sviečku neskôr** — emulátor MultiCharts s `entry_delay=1`: broker dostane zadanie aj zrušenie
   vstupného orderu o bar neskôr (latencia). Edge, ktorý závisí od presného časovania, tu zmizne.
3. **Deflated Sharpe Ratio** (Bailey & López de Prado, 2014) — pravdepodobnosť, že skutočný Sharpe je nad nulou,
   keď sa najlepšie nastavenie vybralo z `trials` skúšok. Sharpe z denných výnosov všetkých okien spolu —
   zo **všetkých obchodných dní** (pondelok–piatok) okien, deň bez obchodu má výnos 0 (inak by √252
   riedku stratégiu nadhodnotila) —,
   so šikmosťou a špicatosťou; očakávané maximum `trials` nezávislých skúšok pri nulovom edgi
   (rozptyl Sharpe pod nulou = 1 / T). Skúšky z hľadania sú korelované → N je horná hranica, test je prísny.

Hranice SMERNICE V2 (krok 7 a 9, zadanie U9), všetko na **L trhu** (§1):
- 2× náklad: PF ≥ 1,05;
- vstup o sviečku neskôr: PF ≥ 1,05 a ≥ 80 % PF;
- tercily ATR(20 dní): žiadny pod 0,90 a žiadny nenesie > 60 % zisku;
- DSR ≥ 0,95 pri N_eff a ≥ 0,50 pri surovom N;
- haircut Harvey–Liu (`tester.overfit.haircut_hl`): PF po ňom ≥ 1,10;
- PBO ≤ 0,20 (16 blokov mesačného PnL registra);
- walk-forward (`tester.walkforward`) a Sortino OOS ≥ 1,0.

Výsledok je stav ✅ 🟡 ⏳ ⚠ ❌.

    PY -m tester.robust --profile tradebot/strategies/orb/configs/ZAKLAD_MNQ.json --pair MNQ/USD --timeframe 3m \\
        --fee 1.755e-05 --hypothesis orb-pondelok --hyperopt wf.json --save
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any

from tradebot.adapters.multicharts.emulator import BarCache, emulate, rows_from_trades
from tradebot.core.candles import timeframe_minutes
from tradebot.core.config import load_profile
from tradebot.core.money import profit_factor, summary_money
from tradebot.core.types import INSTRUMENTS

from . import engines
from .webapp.market import instrument_for_pair

__all__ = ["WINDOWS", "deflated_sharpe", "robustness", "from_hyperopt", "save_to_profile", "main"]

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
    """PF podľa jediného pravidla v jadre (`tradebot.core.money.profit_factor`)."""
    gp = sum(r["profit_abs"] for r in rows if r["profit_abs"] > 0)
    gl = -sum(r["profit_abs"] for r in rows if r["profit_abs"] < 0)
    return profit_factor(gp, gl)


def _open_ms(row: dict[str, Any]) -> int:
    from datetime import datetime

    return int(datetime.fromisoformat(str(row["open_date"])).timestamp() * 1000)


def _outside(rows: list[dict[str, Any]], earlier) -> list[dict[str, Any]]:
    """Obchody okna, ktoré sa neotvorili v čase už pokrytom skorším oknom (`earlier` = okná pred ním).

    Okná sa prekrývajú (`20231001-20241001` a `20240904-20250904` majú spoločné 4.–30. 9. 2024) a obchody
    z prekrytia sú v oboch behoch — do súčtov cez okná smú ísť raz. Reže sa podľa **času**, nie podľa
    orderu: `enter_tag` nesie číslo baru od začiatku behu, takže ten istý obchod má v každom okne iný,
    a beh s iným začiatkom nemusí v prekrytí dať presne tie isté obchody. Prekrytie patrí skoršiemu oknu.
    """
    spans = [tuple(_ms(x) for x in w.split("-")) for w in earlier]
    if not spans:
        return list(rows)
    return [r for r in rows if not any(a <= _open_ms(r) < b for a, b in spans)]


def _trading_days(windows) -> list[str]:
    """Všetky obchodné dni (pondelok–piatok, UTC) okien `YYYYMMDD-YYYYMMDD`, koniec okna nepatrí; každý raz."""
    from datetime import datetime, timedelta

    days: set[str] = set()
    for w in windows:
        a, b = (datetime.strptime(x, "%Y%m%d") for x in w.split("-"))
        while a < b:
            if a.weekday() < 5:
                days.add(a.strftime("%Y-%m-%d"))
            a += timedelta(days=1)
    return sorted(days)


def _daily_returns(rows: list[dict[str, Any]], wallet: float, windows) -> list[float]:
    """Denné výnosy cez všetky obchodné dni okien; deň bez obchodu = 0. Obchod zavretý mimo nich
    (nedeľný Globex, krypto víkend) svoj deň pridá, aby sa žiadny zisk ani strata nestratili."""
    daily = _daily(rows, wallet)
    return [daily.get(d, 0.0) for d in sorted(set(_trading_days(windows)) | set(daily))]


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
    #: DSR pri surovom N (`dsr`) a pri N_eff (`dsr_neff`) - SMERNICA V2 krok 7
    dsr: dict[str, float] = field(default_factory=dict)
    dsr_neff: dict[str, float] = field(default_factory=dict)
    #: odolnosť (krok 9): 2× náklad, vstup o sviečku neskôr, tercily ATR(20 dní)
    verdict: dict[str, bool] = field(default_factory=dict)
    terciles: list[dict[str, Any]] = field(default_factory=list)
    #: Harvey–Liu haircut (`tester.overfit.haircut_hl`) a PF po ňom
    haircut: dict[str, Any] = field(default_factory=dict)
    #: brány SMERNICE V2 (`tester.overfit.gates`) a stav (✅ 🟡 ⏳ ⚠ ❌)
    gates: dict[str, Any] = field(default_factory=dict)
    status: str = ""
    status_reason: str = ""


def _atr_terciles(rows: list[dict[str, Any]], m1) -> list[dict[str, Any]]:
    """Obchody podľa denného ATR(20) dňa vstupu (známe pred dňom) na tercily: PF a podiel na zisku každého."""
    import pandas as pd

    if not rows:
        return []
    d = m1.set_index(pd.to_datetime(m1["date"], utc=True)) if "date" in m1.columns else m1
    day = d.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    prev = day["close"].shift(1)
    tr = pd.concat([day["high"] - day["low"], (day["high"] - prev).abs(), (day["low"] - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean().shift(1)
    atr.index = atr.index.strftime("%Y-%m-%d")
    vals = [(atr.get(str(r["open_date"])[:10]), r["profit_abs"]) for r in rows]
    vals = [(a, p) for a, p in vals if a is not None and a == a]
    if len(vals) < 9:
        return []
    q1, q2 = pd.Series([a for a, _ in vals]).quantile([1 / 3, 2 / 3]).tolist()
    total = sum(p for _, p in vals)
    out = []
    for name, lo, hi in (("nízke", -math.inf, q1), ("stredné", q1, q2), ("vysoké", q2, math.inf)):
        part = [p for a, p in vals if lo < a <= hi] if name != "nízke" else [p for a, p in vals if a <= hi]
        gp = sum(p for p in part if p > 0)
        gl = -sum(p for p in part if p < 0)
        out.append({"tercile": name, "trades": len(part), "pf": profit_factor(gp, gl),
                    "share": (sum(part) / total) if total > 0 else None})
    return out


def robustness(profile: str, pair: str, timeframe: str, fee: float, trials: int, *, fee_mult: float = 2.0,
               delay: int = 1, wallet: float = 100_000.0, windows=None, m1=None, log=print,
               pbo: float | None = None, walk_forward: Any = None, n_eff: int | None = None,
               sortino_oos: float | None = None, economic: bool = False, legacy: bool = False,
               year_a_pf: float | None = None) -> Report:
    """Odolnosť, DSR, haircut a brány SMERNICE V2 na **L trhu po rokoch** (`hyperopt.windows_for`); pre trh mimo
    §1 (CFD) na piatich referenčných oknách. `trials` = surové N, `n_eff` = N_eff (bez neho = N)."""
    import pandas as pd

    from .hyperopt import windows_for
    from .overfit import gates, haircut_hl, pf_after_haircut, status

    if windows is None:
        windows = windows_for(pair)
    cfg, _ = load_profile(profile, engine=engines.MULTICHARTS)
    inst = INSTRUMENTS[instrument_for_pair(pair)]
    if m1 is None:
        m1 = pd.read_feather(engines.one_minute_file(inst))
    tf = timeframe_minutes(timeframe)
    rep = Report(profile=str(profile))
    all_base, all_fee2, all_delay = [], [], []
    for w in windows:
        a, b = w.split("-")
        bars = BarCache(m1)        # oba behy okna (bez posunu a s posunom) skladajú tie isté bary raz
        res, _ = emulate(cfg, inst, m1, tf, from_ms=_ms(a), to_ms=_ms(b), fee=fee, bars=bars)
        base = rows_from_trades(res.trades, inst, fee)
        fee2 = rows_from_trades(res.trades, inst, fee * fee_mult)
        res_d, _ = emulate(cfg, inst, m1, tf, from_ms=_ms(a), to_ms=_ms(b), fee=fee, entry_delay=delay, bars=bars)
        dl = rows_from_trades(res_d.trades, inst, fee)
        # do súčtov cez okná len to, čo skoršie okno ešte nepokrylo (audit M-CORE-2); riadok okna je celý
        seen = list(windows)[:len(rep.windows)]
        all_base += _outside(base, seen)
        all_fee2 += _outside(fee2, seen)
        all_delay += _outside(dl, seen)
        row = {"window": w, "trades": len(base), "pf": _pf(base), "pf_fee2": _pf(fee2),
               "trades_delay": len(dl), "pf_delay": _pf(dl),
               "be": summary_money(base, wallet).get("break_even_pct")}
        rep.windows.append(row)
        log(f"  {w}: {row['trades']} obch PF {row['pf']:.2f} | 2× poplatok {row['pf_fee2']:.2f} | "
            f"o sviečku neskôr {row['trades_delay']} obch PF {row['pf_delay']:.2f}")
    years = sum(window_days(w) for w in windows) / 365.25
    rep.total = {"pf": _pf(all_base), "pf_fee2": _pf(all_fee2), "pf_delay": _pf(all_delay),
                 "trades": len(all_base), "trades_delay": len(all_delay), "years": years,
                 "trades_per_year": len(all_base) / years if years else None,
                 "win_fee2": sum(1 for r in rep.windows if r["pf_fee2"] >= 1.0),
                 "win_delay": sum(1 for r in rep.windows if r["pf_delay"] >= 1.0)}
    daily = _daily_returns(all_base, wallet, windows)
    rep.dsr = deflated_sharpe(daily, trials)
    rep.dsr_neff = deflated_sharpe(daily, n_eff if n_eff else trials)
    rep.terciles = _atr_terciles(all_base, m1)
    t = rep.total
    rep.verdict = {   # krok 9 / U9: odolnosť
        "fee2": t["pf_fee2"] >= 1.05,
        "delay": t["pf_delay"] >= 1.05 and t["pf_delay"] >= 0.8 * t["pf"],
        "atr": bool(rep.terciles) and all(x["pf"] >= 0.90 for x in rep.terciles)
        and all((x["share"] or 0) <= 0.60 for x in rep.terciles),
    }
    tests = max(1.0, (n_eff or trials) / (2 if economic else 1))
    rep.haircut = haircut_hl(rep.dsr.get("sr_annual", 0.0), rep.dsr.get("days", 0), tests)
    rep.haircut["pf"] = t["pf"]
    rep.haircut["pf_live"] = pf_after_haircut(t["pf"], rep.haircut.get("ratio"))
    rep.gates = gates(dsr_neff=rep.dsr_neff.get("dsr"), dsr_n=rep.dsr.get("dsr"), pbo=pbo, walk_forward=walk_forward,
                      pf=t["pf"], haircut_ratio=rep.haircut.get("ratio"), sortino_oos=sortino_oos, legacy=legacy)
    rep.gates["robust"] = rep.verdict
    rep.status, rep.status_reason = status(rep.gates, year_a_pf=year_a_pf)
    return rep


def window_days(w: str) -> int:
    a, b = w.split("-")
    return max(0, (_ms(b) - _ms(a)) // 86_400_000)


def save_to_profile(path: str, rep: Report, trials: int, extra: dict[str, Any]) -> bool:
    """`_robust` do JSON profilu (webapp: stav a stĺpce SMERNICE V2). Profil sa číta tesne pred zápisom (nie skôr
    načítaná kópia) a mení sa len `_robust`. Vráti False, keď `path` nie je súbor."""
    from datetime import date
    from pathlib import Path

    from tradebot.core.atomic import read_json, write_json_atomic

    p = Path(path)
    if not p.is_file():
        return False
    data = read_json(p, {}) or {}
    g, h = rep.gates, rep.haircut
    wf = extra.get("walk_forward")
    data["_robust"] = {
        "date": date.today().isoformat(), "smernica": "V2", "trials": int(trials), "n_eff": extra.get("n_eff"),
        "dsr": rep.dsr.get("dsr"), "dsr_neff": rep.dsr_neff.get("dsr"), "pbo": extra.get("pbo"),
        "walk_forward": g.get("walk_forward"),
        "walk_forward_text": wf if isinstance(wf, str) else (wf or {}).get("verdict"),
        "wfe": (wf or {}).get("wfe") if isinstance(wf, dict) else None,
        "sortino": extra.get("sortino"), "pf": h.get("pf"), "pf_live": h.get("pf_live"),
        "haircut": h.get("haircut"), "pf_fee2": rep.total.get("pf_fee2"), "pf_delay": rep.total.get("pf_delay"),
        "trades_per_year": rep.total.get("trades_per_year"), "robust": rep.verdict,
        "legacy": g.get("legacy"), "info": g.get("info"),
        "passed": g.get("passed"), "missing": g.get("missing"), "failed": g.get("failed"),
        "status": rep.status, "status_reason": rep.status_reason,
        "k": extra.get("k"), "t": extra.get("t"), "t_req": extra.get("t_req"), "year_a_pf": extra.get("year_a_pf"),
    }
    write_json_atomic(p, data, indent=1)
    return True


def from_hyperopt(paths) -> dict[str, Any]:
    """PBO, walk-forward a Sortino OOS z JSON `tester.walkforward --out` (V2) alebo `tester.native_hyperopt --out`."""
    out: dict[str, Any] = {}
    for p in paths or ():
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("mode") == "walkforward_v2" and data.get("gates"):
            g = dict(data["gates"])
            g.pop("daily", None)
            g["verdict"] = data.get("verdict")
            out["walk_forward"] = g
            if g.get("sortino_oos") is not None:
                out["sortino"] = float(g["sortino_oos"])
        elif data.get("mode") == "walkforward" and data.get("verdict"):
            out["walk_forward"] = data["verdict"]
        if (data.get("pbo") or {}).get("pbo") is not None:
            out["pbo"] = float(data["pbo"]["pbo"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.robust", description=__doc__.splitlines()[0])
    ap.add_argument("--profile", action="append", required=True, help="profil (dá sa zopakovať)")
    ap.add_argument("--pair", default="MNQ/USD")
    ap.add_argument("--timeframe", default="3m")
    ap.add_argument("--fee", type=float, default=1.755e-05)
    ap.add_argument("--trials", type=int, default=None,
                    help="surové N; bez neho N z registra (--hypothesis), inak 1")
    ap.add_argument("--n-eff", type=int, help="N_eff; bez neho z registra (--hypothesis), inak N")
    ap.add_argument("--hypothesis", help="hypotéza registra (tester.register): N, N_eff a PBO zo 16 blokov mesačného PnL")
    ap.add_argument("--economic", action="store_true", help="bonus za ekonomický dôvod (§2): haircut z ½ N_eff")
    ap.add_argument("--legacy", action="store_true", help="legacy stratégia: DSR, PBO a haircut len informácia, najviac 🟡")
    ap.add_argument("--year-a-pf", type=float, help="PF na roku A (len negatívna kontrola: < 1,0 -> ❌)")
    ap.add_argument("--fee-mult", type=float, default=2.0)
    ap.add_argument("--delay", type=int, default=1)
    ap.add_argument("--pbo", type=float, help="PBO zvonka (inak z registra pri --hypothesis)")
    ap.add_argument("--hyperopt", action="append", default=[],
                    help="JSON z tester.walkforward --out (brány WF, Sortino OOS) alebo native_hyperopt --out (PBO)")
    ap.add_argument("--windows", help="okná oddelené čiarkou (predvolene L trhu po rokoch)")
    ap.add_argument("--json", help="zapíš výsledky do JSON")
    ap.add_argument("--save", action="store_true",
                    help="zapísať výsledok do profilu ako `_robust` (profil = cesta k súboru; webapp)")
    args = ap.parse_args(argv)
    extra = from_hyperopt(args.hyperopt)
    if args.hypothesis:
        from .overfit import pbo_of_register
        from .register import attempts, n_eff, n_trials

        rows = attempts(args.hypothesis)
        if args.trials is None:
            args.trials = max(1, n_trials(rows))
        if args.n_eff is None:
            args.n_eff = max(1, n_eff(rows))
        if args.pbo is None and "pbo" not in extra:
            pb = pbo_of_register(rows)
            if pb is not None:
                extra["pbo"] = pb["pbo"]
        print(f"register {args.hypothesis}: N {args.trials}, N_eff {args.n_eff}, PBO "
              + (f"{extra['pbo']:.3f}" if extra.get("pbo") is not None else "—"))
    if args.trials is None:
        args.trials = 1
    if args.pbo is not None:
        extra["pbo"] = args.pbo
    extra["n_eff"] = args.n_eff
    if args.year_a_pf is not None:
        extra["year_a_pf"] = args.year_a_pf
    import pandas as pd

    inst = INSTRUMENTS[instrument_for_pair(args.pair)]
    m1 = pd.read_feather(engines.one_minute_file(inst))
    windows = [w.strip() for w in args.windows.split(",") if w.strip()] if args.windows else None
    out = []

    def f(v: Any, d: int = 2) -> str:
        return "—" if v is None else f"{v:.{d}f}"

    for p in args.profile:
        print(f"== {p}")
        rep = robustness(p, args.pair, args.timeframe, args.fee, args.trials, fee_mult=args.fee_mult,
                         delay=args.delay, m1=m1, windows=windows, pbo=extra.get("pbo"),
                         walk_forward=extra.get("walk_forward"), n_eff=args.n_eff, sortino_oos=extra.get("sortino"),
                         economic=args.economic, legacy=args.legacy, year_a_pf=args.year_a_pf)
        t, d, dn, h, g = rep.total, rep.dsr, rep.dsr_neff, rep.haircut, rep.gates
        print(f"  spolu: PF {t['pf']:.2f}, {t['trades']} obch ({f(t['trades_per_year'], 0)}/rok) | 2× náklad {t['pf_fee2']:.2f} | "
              f"o sviečku neskôr {t['pf_delay']:.2f} | tercily ATR "
              + ", ".join(f"{x['tercile']} PF {x['pf']:.2f} ({f((x['share'] or 0) * 100, 0)} %)" for x in rep.terciles))
        print(f"  Sharpe {f(d.get('sr_annual'))} → DSR {f(d.get('dsr'), 3)} pri N {args.trials}, {f(dn.get('dsr'), 3)} pri N_eff "
              f"{args.n_eff or args.trials} (≥ 0,50 / ≥ 0,95)")
        print(f"  haircut Harvey–Liu: SR {f(h.get('sr'))} → {f(h.get('sr_haircut'))} ({f((h.get('haircut') or 0) * 100, 0)} %), "
              f"PF {f(h.get('pf'))} → {f(h.get('pf_live'))} (≥ 1,10)")
        print(f"  odolnosť: {rep.verdict}")
        print("  brány: " + ", ".join(f"{k} {'áno' if g[k] else 'nie' if g[k] is False else '—'}{' (info)' if k in g['info'] else ''}"
                                     for k in ("dsr", "pbo", "walk_forward", "haircut", "sortino")))
        print(f"  stav: {rep.status} {rep.status_reason}")
        if args.save:
            print("  zapísané do profilu (_robust)" if save_to_profile(p, rep, args.trials, extra)
                  else "  --save: profil nie je cesta k súboru - nezapísané")
        out.append(rep.__dict__)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
