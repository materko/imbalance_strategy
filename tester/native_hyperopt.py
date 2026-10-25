"""Hyperopt C# stratégie natívne: Optuna navrhuje, C# počíta dávku backtestov paralelne.

    PY -m tester.native_hyperopt --strategy orbnet --instrument nas100_dukascopy \\
        --param rrRatio=1:5:0.25 --param slBufferTicks=0:40:1 --goal break_even \\
        --timerange 20240904-20250904 --epochs 400 --sampler tpe --fee 0.0001

### Čo je kde
Zadanie je **to isté** ako pri hyperopte cez Freqtrade (`tester.hyperopt`): tie isté `--param`
(`sweep.to_knob`), kritériá a mantinely (`--goal`, `--max-dd`, `--min-trades`), väzby medzi
parametrami vie stratégia (`hyperopt_cls.constrain`). Líši sa, kto počíta epochu:

| | `tester.hyperopt` | toto |
|---|---|---|
| backtest | Freqtrade (krypto fill model) | emulátor MultiCharts v C# (`McEmulator`) — fill model NT8/MT5 |
| stratégie | všetky | len s C# jadrom (`ibsnet`, `orbnet`, …) |
| dáta | `--timeframe-detail 1m` | 1m súbor emulátora (`tester.engines.one_minute_file`) |
| rýchlosť | ~20–40 s na rok a epochu | 0,15–0,9 s na rok a epochu, na všetkých jadrách naraz |

Python v epoche len postaví config a spočíta kritérium (`summary_money` — tie isté čísla,
aké ukazuje história behov emulátora); obchody počíta C# a ich zhodu s Python emulátorom
stráži `tester/tests/test_csharp_backtest.py`.

### Samplery (Optuna)
`tpe` (bayesovský, predvolený — viac parametrov naraz, `multivariate`), `cmaes` (evolučná
stratégia — len čísla, kategórie dorieši náhodný), `nsga2` (genetický algoritmus), `random`,
`qmc` (rovnomerné pokrytie priestoru — dobrý prvý prieskum). Dávka = `--jobs` epoch naraz:
sampler ich navrhne, C# spočíta paralelne, výsledky dostane späť.

### Overenie
Víťaz (a `--top` ďalších) sa po skončení prepočíta na piatich referenčných oknách — rovnaký
verdikt ako `tester.hyperopt` (znamienko break-even nad poplatkom po oknách, ladené okno zvlášť).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.adapters.freqtrade.hyperplan import Plan, knob_kind, knowledge
from tradebot.adapters.multicharts.emulator import EmuTrade, rows_from_trades
from tradebot.core import load_profile
from tradebot.core.candles import timeframe_minutes
from tradebot.core.money import summary_money
from tradebot.core.types import INSTRUMENTS, Direction, InstrumentSpec
from tradebot.strategies import get_spec

from . import engines
from .hyperopt import REFERENCE_WINDOWS, Epoch, build_plan, overrides, table, verdict

__all__ = ["SAMPLERS", "NativeRunner", "Search", "loss_of", "config_json", "run_search", "main"]

SAMPLERS = ("tpe", "cmaes", "nsga2", "random", "qmc")

#: Skóre epochy, ktorá sa nedá vyhodnotiť — rovnaké ako `TradebotPlanLoss.UNUSABLE`.
UNUSABLE = 1000.0
#: Bez `min_trades` v pláne platí to isté dno ako v `TradebotPlanLoss`.
DEFAULT_MIN_TRADES_PER_YEAR = 60


def _window_ms(timerange: str) -> tuple[int, int]:
    a, _, b = timerange.partition("-")
    def ms(text: str) -> int:
        return int(datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    return ms(a), ms(b)


def _days(timerange: str) -> int:
    a, b = _window_ms(timerange)
    return max((b - a) // 86_400_000, 1)


# --------------------------------------------------------------------------- #
# C# strana
# --------------------------------------------------------------------------- #


class NativeRunner:
    """Dávky backtestov jednej stratégie na jednom inštrumente a TF cez `NativeBacktest.RunBatchJson`."""

    def __init__(self, strategy: str, inst: InstrumentSpec, timeframe: int, fee: float, threads: int = 0) -> None:
        from tradebot.adapters.csharp import bridge

        from .compare.csharp_backtest import instrument_json

        self.spec = get_spec(strategy)
        self.key = getattr(self.spec.engine_factory, "csharp_key", None)
        if self.key is None:
            raise ValueError(f"{strategy}: stratégia nemá C# jadro — natívny hyperopt nejde, použi tester.hyperopt")
        self.inst = inst
        self.timeframe = int(timeframe)
        self.fee = float(fee)
        self.threads = int(threads)
        self.m1_path = engines.one_minute_file(inst)
        if not self.m1_path.exists():
            raise FileNotFoundError(f"chýbajú 1m dáta {self.m1_path}")
        bridge._load_clr()
        from TradeBot.Backtest import NativeBacktest

        self._native = NativeBacktest
        self._inst_json = instrument_json(inst)

    def run(self, configs: list[str], timerange: str) -> list[dict[str, Any]]:
        """Config JSON-y -> výsledky (`trades`, `bars`, …, alebo `error`) v tom istom poradí."""
        from System import Array, String

        a, b = _window_ms(timerange)
        raw = self._native.RunBatchJson(self.key, Array[String](configs), self._inst_json, str(self.m1_path),
                                        self.timeframe, a, b, self.fee, self.threads)
        return [json.loads(r) for r in raw]


def summary_of(result: dict[str, Any], inst: InstrumentSpec, fee: float, wallet: float) -> dict[str, Any] | None:
    """Súhrn behu z obchodov C# — `rows_from_trades` + `summary_money`, ako história emulátora."""
    if "error" in result:
        return None
    trades = [EmuTrade(order_id=t["order_id"], direction=Direction.LONG if t["dir"] == 1 else Direction.SHORT,
                       qty=t["qty"], entry=t["entry"], open_ms=t["open_ms"], stop_initial=t["stop_initial"],
                       take_profit=t["take_profit"], market=t["market"], stop_last=t["stop_last"], exit=t["exit"],
                       close_ms=t["close_ms"], reason=t["reason"], max_price=t["max_price"], min_price=t["min_price"])
              for t in result["trades"]]
    return summary_money(rows_from_trades(trades, inst, fee), wallet)


def loss_of(summary: dict[str, Any] | None, plan: Plan, days: int) -> float:
    """`TradebotPlanLoss` nad súhrnom behu: menej je lepšie, mimo mantinelov nad tisíc."""
    if summary is None:
        return UNUSABLE
    za_rok = plan.min_trades or DEFAULT_MIN_TRADES_PER_YEAR
    treba = max(3, int(za_rok * days / 365))
    n = int(summary.get("trades") or 0)
    if n < treba:
        return UNUSABLE + (treba - n)
    goal = plan.goal or "break_even"
    if goal == "winrate":
        skore = float(summary["winrate"])
    elif goal == "profit":
        skore = float(summary["pnl_pct"])
    elif goal == "drawdown":
        skore = -float(summary["max_drawdown_pct"])
    else:
        if summary.get("break_even_pct") is None:
            return UNUSABLE
        skore = float(summary["break_even_pct"])
    loss = -skore
    if plan.max_dd and float(summary["max_drawdown_pct"]) > plan.max_dd:
        loss += UNUSABLE + (float(summary["max_drawdown_pct"]) - plan.max_dd)
    return loss


# --------------------------------------------------------------------------- #
# priestor -> config
# --------------------------------------------------------------------------- #


def _suggest(trial: Any, plan: Plan) -> dict[str, Any]:
    """Hodnoty epochy pod menami `hp_<pole>` — tvar, aký čaká `tester.hyperopt.overrides`."""
    spec = get_spec(plan.strategy)
    out: dict[str, Any] = {}
    for k in plan.knobs:
        if k.choices is not None:
            out[k.attr] = trial.suggest_categorical(k.attr, list(k.choices))
            continue
        kind, _ = knob_kind(k.name, spec)
        if kind == "int":
            krok = max(1, int(round(k.step))) if k.step else 1
            out[k.attr] = trial.suggest_int(k.attr, int(k.low), int(k.high), step=krok)
        else:
            krok = k.step if k.step and k.step > 0 else 0.01
            pocet = math.floor((k.high - k.low) / krok + 1e-9)
            hodnota = trial.suggest_float(k.attr, k.low, k.low + pocet * krok, step=krok)
            out[k.attr] = round(hodnota, 10)
    return out


def config_json(base: dict[str, Any], cfg_cls: type, plan: Plan, params: dict[str, Any]) -> str:
    """Config epochy: profil + hodnoty plánu + väzby stratégie (`constrain`) — ako `hyperplan.apply`."""
    cfg = cfg_cls.from_dict({**base, **overrides(plan, params)})
    knowledge(get_spec(plan.strategy)).constrain(cfg)
    return json.dumps(cfg.to_dict())


# --------------------------------------------------------------------------- #
# hľadanie
# --------------------------------------------------------------------------- #


def _sampler(name: str, seed: int | None, n_startup: int):
    import optuna

    if name == "tpe":
        return optuna.samplers.TPESampler(seed=seed, multivariate=True, n_startup_trials=n_startup)
    if name == "cmaes":
        return optuna.samplers.CmaEsSampler(seed=seed, n_startup_trials=n_startup, warn_independent_sampling=False)
    if name == "nsga2":
        return optuna.samplers.NSGAIISampler(seed=seed)
    if name == "random":
        return optuna.samplers.RandomSampler(seed=seed)
    if name == "qmc":
        return optuna.samplers.QMCSampler(seed=seed, warn_independent_sampling=False)
    raise ValueError(f"neznámy sampler {name!r}; známe: {', '.join(SAMPLERS)}")


@dataclass
class Search:
    plan: Plan
    epochs: list[Epoch]
    best: Epoch | None
    seconds: float
    #: koľko rôznych configov sa naozaj počítalo (zvyšok boli opakovania)
    distinct: int = 0


def run_search(runner: NativeRunner, plan: Plan, profile: str | None, timerange: str, *, epochs: int = 200,
               sampler: str = "tpe", batch: int | None = None, seed: int | None = None, wallet: float = 10000,
               log: Callable[[str], None] = print, should_stop: Callable[[], bool] | None = None,
               on_progress: Callable[[int, int], None] | None = None) -> Search:
    """Optuna ask/tell po dávkach: sampler navrhne `batch` epoch, C# ich spočíta naraz, späť ide loss.

    `should_stop` sa pýta medzi dávkami (zrušenie z webapp), `on_progress(hotovo, spolu)` po každej
    dávke (priebeh a odhad vo fronte).
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    spec = runner.spec
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    base = cfg.to_dict()
    days = _days(timerange)
    batch = batch or max(1, runner.threads or __import__("os").cpu_count() or 1)
    study = optuna.create_study(direction="minimize", sampler=_sampler(sampler, seed, min(epochs // 5 or 1, 4 * batch)))
    found: list[Epoch] = []
    #: config JSON -> súhrn: sampler na mriežke (krok) navrhuje tie isté body znova a znova
    seen: dict[str, dict[str, Any] | None] = {}
    t0 = time.perf_counter()
    while len(found) < epochs:
        if should_stop is not None and should_stop():
            log("zrusene")
            break
        trials = [study.ask() for _ in range(min(batch, epochs - len(found)))]
        params = [_suggest(t, plan) for t in trials]
        configs: list[str | None] = []
        for p in params:
            try:
                configs.append(config_json(base, type(cfg), plan, p))
            except (ValueError, TypeError) as exc:   # config kombináciu odmietol
                configs.append(None)
                log(f"  epocha zamietnutá configom: {exc}")
        nove = list(dict.fromkeys(c for c in configs if c is not None and c not in seen))
        for c, res in zip(nove, runner.run(nove, timerange) if nove else []):
            if "error" in res:
                log(f"  epocha spadla v C#: {res['error']}")
            seen[c] = summary_of(res, runner.inst, runner.fee, wallet)
        for trial, p, c in zip(trials, params, configs):
            s = seen.get(c) if c is not None else None
            loss = loss_of(s, plan, days)
            study.tell(trial, loss)
            found.append(Epoch(number=len(found) + 1, loss=loss, params=p, trades=int((s or {}).get("trades") or 0),
                               pnl_pct=(s or {}).get("pnl_pct"), winrate=(s or {}).get("winrate"),
                               max_drawdown_pct=(s or {}).get("max_drawdown_pct"),
                               profit_factor=(s or {}).get("profit_factor")))
        if on_progress is not None:
            on_progress(len(found), epochs)
        best = min((e for e in found if e.usable), key=lambda e: e.loss, default=None)
        rate = len(found) / (time.perf_counter() - t0)
        log(f"  {len(found)}/{epochs} epoch ({len(seen)} roznych), {rate:.1f}/s"
            + (f", najlepsie skore {-best.loss:.4f} (epocha {best.number})" if best else ", zatial nic v mantineloch"))
    best = min((e for e in found if e.usable), key=lambda e: e.loss, default=None)
    if best is not None:
        found = [Epoch(**{**e.__dict__, "is_best": e is best}) for e in found]
        best = next(e for e in found if e.is_best)
    return Search(plan=plan, epochs=found, best=best, seconds=time.perf_counter() - t0, distinct=len(seen))


def verify(runner: NativeRunner, plan: Plan, profile: str | None, params: dict[str, Any], tuned: str,
           wallet: float = 10000, windows: tuple[str, ...] = REFERENCE_WINDOWS) -> list[dict[str, Any]]:
    """Parametre na referenčných oknách (jedna dávka) — záznamy v tvare, aký čaká `hyperopt.verdict`."""
    spec = runner.spec
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    cj = config_json(cfg.to_dict(), type(cfg), plan, params)
    okna = list(windows) + ([tuned] if tuned not in windows else [])
    out = []
    for okno in okna:
        res = runner.run([cj], okno)[0]
        s = summary_of(res, runner.inst, runner.fee, wallet)
        out.append({"status": "done" if s is not None else "failed", "result": s or {},
                    "settings": {"timerange": okno, "fee": runner.fee}, "tuned": okno == tuned})
    return out


def _verification_table(records: list[dict[str, Any]]) -> str:
    lines = [f"{'okno':>19}  {'obchodov':>8}  {'PnL %':>8}  {'WR %':>6}  {'maxDD %':>8}  {'BE %':>8}"]
    for r in records:
        s = r["result"]
        mark = "  <- ladene" if r["tuned"] else ""
        be = s.get("break_even_pct")
        lines.append(f"{r['settings']['timerange']:>19}  {s.get('trades', 0):>8}  {s.get('pnl_pct', 0):>8}  "
                     f"{s.get('winrate', 0):>6}  {s.get('max_drawdown_pct', 0):>8}  "
                     f"{'-' if be is None else be:>8}{mark}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--instrument", required=True, help="kľúč z tradebot.core.types.INSTRUMENTS")
    ap.add_argument("--timeframe", help="default = TF stratégie")
    ap.add_argument("--timerange", default="20240904-20250904")
    ap.add_argument("--param", action="append", default=[], metavar="POLE=OD:DO:KROK|A,B,C")
    ap.add_argument("--goal", default="break_even", choices=("break_even", "profit", "winrate", "drawdown"))
    ap.add_argument("--max-dd", type=float)
    ap.add_argument("--min-trades", type=int, help="obchodov za rok")
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--sampler", default="tpe", choices=SAMPLERS)
    ap.add_argument("--jobs", type=int, default=0, help="vlákna C# (0 = všetky jadrá); dávka sampleru je rovnako veľká")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--wallet", type=float, default=10000)
    ap.add_argument("--out", help="JSON s epochami a overením (default: nič sa neukladá)")
    a = ap.parse_args(argv)

    if not a.param:
        ap.error("aspoň jeden --param")
    space = dict(p.split("=", 1) for p in a.param)
    plan = build_plan(space, strategy=a.strategy, goal=a.goal, max_dd=a.max_dd, min_trades=a.min_trades)
    spec = get_spec(a.strategy)
    tf = timeframe_minutes(a.timeframe or spec.default_timeframe)
    runner = NativeRunner(a.strategy, INSTRUMENTS[a.instrument], tf, a.fee, a.jobs)
    print(f"natívny hyperopt {a.strategy} {a.instrument} {tf}m {a.timerange}: {a.epochs} epoch, sampler {a.sampler}, "
          f"kritérium {a.goal}")
    search = run_search(runner, plan, a.profile, a.timerange, epochs=a.epochs, sampler=a.sampler,
                        batch=a.jobs or None, seed=a.seed, wallet=a.wallet)
    print(f"\n{len(search.epochs)} epoch za {search.seconds:.1f} s\n")
    print(table(search.epochs, plan))
    if search.best is None:
        print("\nziadna epocha nesplnila mantinely - overenie sa nerobi")
        return 1
    best = overrides(plan, search.best.params)
    print(f"\nvitaz: {json.dumps(best, ensure_ascii=False)}\n")
    records = verify(runner, plan, a.profile, search.best.params, a.timerange, a.wallet)
    print(_verification_table(records))
    print("\n" + verdict(records, a.timerange))
    if a.out:
        Path(a.out).write_text(json.dumps({
            "plan": plan.to_dict(), "instrument": a.instrument, "timeframe": tf, "timerange": a.timerange,
            "sampler": a.sampler, "fee": a.fee, "seconds": search.seconds, "best": best,
            "epochs": [e.to_dict() for e in search.epochs], "verification": records,
        }, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nulozene: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
