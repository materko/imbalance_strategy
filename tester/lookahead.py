"""Test utnutia dát — smernica krok 1b a 1c: nepozerá stratégia do budúcnosti?

Stratégia sa prehrá v emulátore MultiCharts nad oknom a zapíše sa, čo engine povedal na každom
bare (vstupy s cenou, SL, TP a veľkosťou, SL/TP otvorenej pozície, zatvorenie seansy). Potom sa ten
istý beh pustí s dátami **utnutými na konci vybraného baru** — budúce sviečky neexistujú, ako naživo.
Utína sa na baroch, kde vznikol nový vstup (1b), a na náhodných baroch, ktoré väčšinou padnú doprostred
sviečky vyššieho TF (1c). Výstup enginu na všetkých baroch po utnutie musí byť **presne rovnaký**;
prvý rozdiel znamená, že engine, feeder alebo skladanie TF videli dáta za utnutím.

Čo test nevidí: dáta, ktoré sa neutínajú spolu s grafom — vlastné súbory stratégie (Mag7 symboly,
kalendár SPRÁVY) a Freqtrade cesta (informatívny DataFrame). Tie treba prejsť čítaním kódu
(audit `docs/audity/AUDIT_lookahead_2026-11-09.md`).

    PY -m tester.lookahead                          # všetky stratégie v registry
    PY -m tester.lookahead --strategy tks --strategy sigma --from 20251103 --to 20260302
    PY -m tester.lookahead --strategy tks --profile tester/profiles/SMERNICE_CS_TKS_1.json

Profil: výber webapp (`tester/webapp_vyber.json`), inak prvý vlastný profil stratégie
v `tester/profiles/`, inak predvolený profil stratégie. Návratový kód 1 = aspoň jeden rozdiel alebo chyba.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.paths import PROFILES_DIR, WEBAPP_SELECTION

__all__ = ["CutReport", "cut_test", "pick_profile", "check_strategy", "main"]

MIN_MS = 60_000
#: Okno predvoleného behu — 6 týždňov stačí na desiatky signálov väčšiny stratégií a beh trvá sekundy.
DEFAULT_FROM = "20260202"
DEFAULT_TO = "20260316"


def _ms(day: str) -> int:
    return int(datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def _r(x: float | None) -> float | None:
    return None if x is None or x != x else round(float(x), 6)


def _record(out) -> tuple:
    """Čo engine na bare povedal brokerovi — všetko, čo môže zmeniť obchod."""
    entries = tuple(sorted(
        (e.order_id, str(e.direction), _r(e.plan.entry), _r(e.plan.stop_loss), _r(e.plan.take_profit),
         _r(e.plan.qty), bool(e.market), bool(e.stop))
        for e in out.entries))
    xp = out.exit_plan
    exit_ = None if xp is None else (_r(xp.stop_loss), _r(xp.take_profit), _r(out.exit_stop))
    return entries, bool(out.close_session), exit_


@dataclass
class CutReport:
    bars: int = 0
    #: bary, na ktorých sa objavil nový vstup (iná sada vstupov než na predošlom bare)
    signal_bars: int = 0
    cuts: list[str] = field(default_factory=list)
    #: prvý rozdiel pri každom utnutí, ktoré nesedelo
    diffs: list[dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diffs


def cut_test(cfg, inst, m1, chart_tf: int, from_ms: int, to_ms: int, *, spec=None,
             signal_cuts: int = 6, random_cuts: int = 4, seed: int = 0) -> CutReport:
    """Plný beh + behy utnuté na konci vybraných barov; porovná výstup enginu bar po bare."""
    from tradebot.adapters.multicharts.emulator import emulate

    step = chart_tf * MIN_MS

    def run(end_ms: int) -> dict[int, tuple]:
        log: dict[int, tuple] = {}
        emulate(cfg, inst, m1, chart_tf, from_ms=from_ms, to_ms=end_ms, spec=spec,
                observe=lambda bar, out: log.__setitem__(bar.time, _record(out)))
        return log

    full = run(to_ms)
    times = sorted(full)
    rep = CutReport(bars=len(times))
    if not times:
        return rep
    sig = [t for i, t in enumerate(times) if full[t][0] and (i == 0 or full[t][0] != full[times[i - 1]][0])]
    rep.signal_bars = len(sig)
    cuts: set[int] = set()
    if sig and signal_cuts > 0:
        n = min(signal_cuts, len(sig))
        cuts |= {sig[round(i * (len(sig) - 1) / max(1, n - 1))] for i in range(n)}
    pool = times[len(times) // 10:]
    cuts |= set(random.Random(seed).sample(pool, min(random_cuts, len(pool) // 2)))
    for cut in sorted(cuts):
        rep.cuts.append(_iso(cut))
        part = run(cut + step)
        for t in times:
            if t > cut:
                break
            if part.get(t) != full[t]:
                rep.diffs.append({"cut": _iso(cut), "bar": _iso(t),
                                  "full": repr(full[t])[:400], "cut_run": repr(part.get(t))[:400]})
                break
    return rep


def _tf_minutes(tf: str | None) -> int:
    t = str(tf or "5m").strip()
    if t.endswith("h"):
        return int(t[:-1]) * 60
    return int(t.rstrip("m"))


def pick_profile(key: str) -> Path:
    """Profil, s ktorým sa stratégia testuje (viď hlavička modulu)."""
    from tradebot.strategies import get_spec

    if WEBAPP_SELECTION.exists():
        vyber = json.loads(WEBAPP_SELECTION.read_text(encoding="utf-8"))
        for name in vyber.get("strategies", {}).get(key, []):
            p = PROFILES_DIR / f"{name}.json"
            if p.exists():
                return p
    for p in sorted(PROFILES_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("_strategy") == key and d.get("_instrument"):
            return p
    spec = get_spec(key)
    p = Path(spec.profile_dir) / f"{spec.default_profile}.json"
    return p if p.exists() else Path(spec.profile_dir) / spec.default_profile


def check_strategy(key: str, from_day: str = DEFAULT_FROM, to_day: str = DEFAULT_TO,
                   profile: str | Path | None = None, signal_cuts: int = 6, random_cuts: int = 4) -> dict[str, Any]:
    """Test utnutia jednej stratégie s jej profilom; výsledok ako slovník (aj pri chybe)."""
    import pandas as pd

    from tradebot.core.config import load_profile
    from tradebot.strategies import get_spec

    from . import engines

    t0 = time.time()
    res: dict[str, Any] = {"strategy": key}
    try:
        prof = Path(profile) if profile else pick_profile(key)
        res["profile"] = prof.name
        meta = json.loads(prof.read_text(encoding="utf-8")) if prof.suffix == ".json" and prof.exists() else {}
        spec = None
        if meta.get("_strategy") not in (None, key):
            # C# prepis („…net") s profilom svojej Python predlohy — tak ho púšťa aj webapp
            cfg, inst = load_profile(str(prof), engine=engines.MULTICHARTS)
            spec = get_spec(key)
        else:
            cfg, inst = load_profile(str(prof), strategy=key, engine=engines.MULTICHARTS)
        tf = _tf_minutes(meta.get("_timeframe"))
        res.update(timeframe=f"{tf}m", pair=inst.symbol)
        m1 = pd.read_feather(engines.one_minute_file(inst))
        rep = cut_test(cfg, inst, m1, tf, _ms(from_day), _ms(to_day), spec=spec, signal_cuts=signal_cuts,
                       random_cuts=random_cuts, seed=zlib.crc32(key.encode()))
        res.update(asdict(rep))
        res["status"] = "OK" if rep.ok else "LOOKAHEAD"
    except Exception as exc:  # noqa: BLE001 - chyba jednej stratégie nesmie zhodiť celý prechod
        res["status"] = "ERROR"
        res["error"] = f"{type(exc).__name__}: {exc}"
        res["traceback"] = traceback.format_exc()[-2000:]
    res["seconds"] = round(time.time() - t0, 1)
    return res


def _line(r: dict[str, Any]) -> str:
    s = (f"{r['strategy']:16s} {r['status']:9s} {r.get('pair', ''):10s} {r.get('timeframe', ''):4s} "
         f"signálov {r.get('signal_bars', 0):3d}, utnutí {len(r.get('cuts', [])):2d}, {r['seconds']} s")
    if r["status"] == "ERROR":
        s += f"  {r['error'][:160]}"
    for d in r.get("diffs", []):
        s += f"\n    utnuté {d['cut']}: rozdiel na bare {d['bar']}\n      celé: {d['full']}\n      utnuté: {d['cut_run']}"
    return s


def main(argv: list[str] | None = None) -> int:
    from concurrent.futures import ProcessPoolExecutor, as_completed

    from tradebot.strategies import STRATEGIES

    ap = argparse.ArgumentParser(prog="python -m tester.lookahead", description=__doc__.splitlines()[0])
    ap.add_argument("--strategy", action="append", help="kľúč stratégie (dá sa zopakovať); bez neho všetky")
    ap.add_argument("--profile", help="profil (len s jednou --strategy)")
    ap.add_argument("--from", dest="from_day", default=DEFAULT_FROM, help="začiatok okna YYYYMMDD")
    ap.add_argument("--to", dest="to_day", default=DEFAULT_TO, help="koniec okna YYYYMMDD")
    ap.add_argument("--signal-cuts", type=int, default=6, help="utnutí na baroch s novým vstupom")
    ap.add_argument("--random-cuts", type=int, default=4, help="utnutí na náhodných baroch")
    ap.add_argument("--workers", type=int, default=4, help="paralelných procesov")
    ap.add_argument("--json", help="zapíš výsledky do JSON")
    args = ap.parse_args(argv)
    keys = args.strategy or sorted(STRATEGIES)
    if args.profile and len(keys) != 1:
        ap.error("--profile ide len s jednou --strategy")

    results: list[dict[str, Any]] = []
    kw = dict(from_day=args.from_day, to_day=args.to_day, profile=args.profile,
              signal_cuts=args.signal_cuts, random_cuts=args.random_cuts)
    if args.workers <= 1 or len(keys) == 1:
        for k in keys:
            results.append(check_strategy(k, **kw))
            print(_line(results[-1]), flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(check_strategy, k, **kw) for k in keys]
            for f in as_completed(futs):
                results.append(f.result())
                print(_line(results[-1]), flush=True)
    results.sort(key=lambda r: r["strategy"])
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("OK", "LOOKAHEAD", "ERROR")}
    print(f"spolu {len(results)}: OK {counts['OK']}, LOOKAHEAD {counts['LOOKAHEAD']}, chyba {counts['ERROR']}")
    few = [r["strategy"] for r in results if r["status"] == "OK" and r.get("signal_bars", 0) < 3]
    if few:
        print("málo signálov v okne (overené hlavne náhodnými utnutiami, skús dlhšie okno): " + ", ".join(few))
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if counts["OK"] == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
