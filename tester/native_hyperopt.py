"""Hyperopt C# stratégie natívne: Optuna navrhuje, C# počíta dávky backtestov na pracovných procesoch.

    PY -m tester.native_hyperopt --strategy orbnet --instrument nas100_dukascopy \\
        --param rrRatio=0.75:4:0.25 --param nyRangeMinutes=5:60:5 --goal break_even \\
        --timerange 20240904-20250904 --epochs 400 --sampler tpe --fee 0.0001

    # ladiť naraz na štyroch oknách, skóre = najhoršie z nich, víťaz podľa okolia
    PY -m tester.native_hyperopt … --windows 20211001-20221001,20221001-20231001,20231001-20241001,20240904-20250904 \\
        --aggregate min --select plateau

    # walk-forward: ladí na okne N, meria na N+1, posúva sa
    PY -m tester.native_hyperopt … --walk-forward --epochs 200

### Čo je kde
Zadanie je **to isté** ako pri hyperopte cez Freqtrade (`tester.hyperopt`): tie isté `--param`
(`sweep.to_knob`), kritériá a mantinely (`--goal`, `--max-dd`, `--min-trades`), väzby medzi
parametrami vie stratégia (`hyperopt_cls.constrain`). Epochu počíta emulátor MultiCharts v C#
(`tester.native`) — fill model NT8/MT5, len stratégie s C# jadrom; súhrn behu sa počíta tými istými
funkciami ako história (`summary_money`).

### Čo vie navyše (lebo epocha stojí zlomok sekundy)
* **kritérium cez viac okien** (`--windows`, `--aggregate min|median|mean`): epocha = jeden beh na
  každom okne, skóre = najhoršie okno / medián / priemer. Pretrénovanie na jedno okno sa tak bráni už pri
  hľadaní, nie až pri overení.
* **viac cieľov naraz** (`--objectives break_even,drawdown,trades`, sampler `nsga2` alebo `tpe`): Pareto
  hranica namiesto jedného čísla s pokutami; víťaz je najlepší v kritériu plánu, hranica je na výber.
* **výber podľa okolia** (`--select plateau`): z najlepších epoch sa vyberie tá, ktorej susedia (±1 krok
  na každom parametri, ako `tester.plateau`) držia v priemere najlepšie — stred plató, nie ostrá špička.
* **walk-forward** (`--walk-forward`, `--anchored`): ladí na okne N (alebo na všetkých do N), meria na
  N+1; výsledok sú skóre mimo ladených okien za sebou.
* **pokračovanie** (`warm=` / webapp „Pokračovať"): epochy predošlého hyperoptu sa vložia do štúdie a hľadá sa ďalej.

### Samplery (Optuna)
`tpe` (bayesovský, predvolený), `cmaes` (evolučná stratégia — len čísla, jeden cieľ), `nsga2`/`nsga3` (genetický),
`random`, `qmc` (rovnomerné pokrytie priestoru). Dávka = `--jobs` epoch naraz: sampler ich navrhne, C#
spočíta paralelne, výsledky dostane späť.

### Overenie
Víťaz sa po skončení prepočíta na piatich referenčných oknách — rovnaký verdikt ako `tester.hyperopt`
(znamienko break-even nad poplatkom po oknách, ladené okná zvlášť).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from tradebot.adapters.freqtrade.hyperplan import Plan, knob_kind, knowledge
from tradebot.core import load_profile
from tradebot.core.candles import timeframe_minutes
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import get_spec

from . import engines
from .hyperopt import REFERENCE_WINDOWS, Epoch, build_plan, edge_of, eta, overrides, table, verdict
from .native import NativeRunner, summary_of, window_days, window_ms
from .sweep import PF_CAP

__all__ = ["SAMPLERS", "AGGREGATES", "OBJECTIVES", "SELECTS", "NativeRunner", "Search", "WalkForward",
           "loss_of", "objective_of", "config_json", "run_search", "walk_forward", "verify", "summary_of",
           "walk_forward_verdict", "plateau_candidates", "plateau_choice", "aggregate",
           "space_text", "fmt_seconds", "main"]

SAMPLERS = ("tpe", "cmaes", "nsga2", "nsga3", "random", "qmc")
#: Ako sa skóre z viacerých okien zloží do jedného: najhoršie okno (predvolené), medián, priemer.
AGGREGATES = ("min", "median", "mean")
#: Ciele pre `objectives` — kritériá plánu a k nim počet obchodov.
OBJECTIVES = ("break_even", "profit", "winrate", "drawdown", "pf", "trades")
#: Ako vybrať víťaza: najlepšia epocha, alebo najlepšie okolie (plató).
SELECTS = ("best", "plateau")

#: Skóre epochy, ktorá sa nedá vyhodnotiť — rovnaké ako `TradebotPlanLoss.UNUSABLE`.
UNUSABLE = 1000.0
#: Bez `min_trades` v pláne platí to isté dno ako v `TradebotPlanLoss`.
DEFAULT_MIN_TRADES_PER_YEAR = 60
#: Výber podľa okolia preverí toľko najlepších epoch.
PLATEAU_TOP = 5


def fmt_seconds(sec: float) -> str:
    """`42 s`, `3 min 5 s`, `1 h 12 min` — odhad do logu (ASCII okrem čísla)."""
    sec = max(0, int(round(sec)))
    if sec < 60:
        return f"{sec} s"
    if sec < 3600:
        return f"{sec // 60} min {sec % 60} s" if sec % 60 else f"{sec // 60} min"
    return f"{sec // 3600} h {sec % 3600 // 60} min"


# spätná kompatibilita (staršie importy)
_window_ms = window_ms
_days = window_days


# --------------------------------------------------------------------------- #
# kritérium
# --------------------------------------------------------------------------- #


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
    elif goal == "pf":
        skore = min(float(summary.get("profit_factor") or 0.0), PF_CAP)
    else:
        if summary.get("break_even_pct") is None:
            return UNUSABLE
        skore = float(summary["break_even_pct"])
    loss = -skore
    if plan.max_dd and float(summary["max_drawdown_pct"]) > plan.max_dd:
        loss += UNUSABLE + (float(summary["max_drawdown_pct"]) - plan.max_dd)
    return loss


def objective_of(summary: dict[str, Any] | None, name: str, plan: Plan, days: int) -> float:
    """Hodnota jedného cieľa (menej je lepšie). Kritérium plánu nesie aj mantinely, ostatné ciele sú holé čísla."""
    if name == (plan.goal or "break_even"):
        return loss_of(summary, plan, days)
    if summary is None:
        return UNUSABLE
    if name == "break_even":
        be = summary.get("break_even_pct")
        return UNUSABLE if be is None else -float(be)
    if name == "profit":
        return -float(summary.get("pnl_pct") or 0.0)
    if name == "winrate":
        return -float(summary.get("winrate") or 0.0)
    if name == "drawdown":
        return float(summary.get("max_drawdown_pct") or 0.0)
    if name == "trades":
        return -float(summary.get("trades") or 0)
    if name == "pf":
        return -min(float(summary.get("profit_factor") or 0.0), PF_CAP)
    raise ValueError(f"neznámy cieľ {name!r}; známe: {', '.join(OBJECTIVES)}")


def aggregate(values: Sequence[float], how: str) -> float:
    """Skóre z viacerých okien do jedného. `min` = najhoršie okno (loss je najväčší)."""
    if how == "min":
        return max(values)
    if how == "median":
        return float(statistics.median(values))
    if how == "mean":
        return float(statistics.fmean(values))
    raise ValueError(f"neznáme skladanie okien {how!r}; známe: {', '.join(AGGREGATES)}")


# --------------------------------------------------------------------------- #
# priestor -> config
# --------------------------------------------------------------------------- #


def _distributions(plan: Plan) -> dict[str, Any]:
    """Optuna rozdelenie každého parametra — rovnaké pre návrh epochy aj pre vloženie starých epoch."""
    import optuna

    spec = get_spec(plan.strategy)
    out: dict[str, Any] = {}
    for k in plan.knobs:
        if k.choices is not None:
            out[k.attr] = optuna.distributions.CategoricalDistribution(list(k.choices))
            continue
        kind, _ = knob_kind(k.name, spec)
        if kind == "int":
            krok = max(1, int(round(k.step))) if k.step else 1
            out[k.attr] = optuna.distributions.IntDistribution(int(k.low), int(k.high), step=krok)
        else:
            krok = k.step if k.step and k.step > 0 else 0.01
            pocet = math.floor((k.high - k.low) / krok + 1e-9)
            out[k.attr] = optuna.distributions.FloatDistribution(k.low, k.low + pocet * krok, step=krok)
    return out


def _suggest(trial: Any, plan: Plan) -> dict[str, Any]:
    """Hodnoty epochy pod menami `hp_<pole>` — tvar, aký čaká `tester.hyperopt.overrides`."""
    import optuna

    out: dict[str, Any] = {}
    for attr, d in _distributions(plan).items():
        if isinstance(d, optuna.distributions.CategoricalDistribution):
            out[attr] = trial.suggest_categorical(attr, list(d.choices))
        elif isinstance(d, optuna.distributions.IntDistribution):
            out[attr] = trial.suggest_int(attr, d.low, d.high, step=d.step)
        else:
            out[attr] = round(trial.suggest_float(attr, d.low, d.high, step=d.step), 10)
    return out


def config_json(base: dict[str, Any], cfg_cls: type, plan: Plan, params: dict[str, Any]) -> str:
    """Config epochy: profil + hodnoty plánu + väzby stratégie (`constrain`) — ako `hyperplan.apply`."""
    cfg = cfg_cls.from_dict({**base, **overrides(plan, params)})
    knowledge(get_spec(plan.strategy)).constrain(cfg)
    return json.dumps(cfg.to_dict())


def space_text(plan: Plan) -> dict[str, str]:
    """Plán späť na text zadania (`rrRatio=2:8:0.5`) — tak, ako ho berie `tester.plateau.neighbours`."""
    out: dict[str, str] = {}
    for k in plan.knobs:
        if k.choices is not None:
            out[k.name] = ",".join(str(c).lower() if isinstance(c, bool) else str(c) for c in k.choices)
        else:
            out[k.name] = f"{k.low:g}:{k.high:g}:{(k.step or 0.01):g}"
    return out


# --------------------------------------------------------------------------- #
# hľadanie
# --------------------------------------------------------------------------- #


def _sampler(name: str, seed: int | None, n_startup: int, multi: bool):
    import optuna

    if multi and name == "cmaes":
        raise ValueError("CMA-ES vie len jeden cieľ; pre viac cieľov použi nsga2 alebo tpe")
    if name == "tpe":
        return optuna.samplers.TPESampler(seed=seed, multivariate=True, n_startup_trials=n_startup)
    if name == "cmaes":
        return optuna.samplers.CmaEsSampler(seed=seed, n_startup_trials=n_startup, warn_independent_sampling=False)
    if name == "nsga2":
        return optuna.samplers.NSGAIISampler(seed=seed)
    if name == "nsga3":
        return optuna.samplers.NSGAIIISampler(seed=seed)
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
    #: koľko rôznych backtestov (config × okno) sa naozaj počítalo (zvyšok boli opakovania)
    distinct: int = 0
    windows: tuple[str, ...] = ()
    aggregate: str = "min"
    objectives: tuple[str, ...] = ()
    #: čísla epoch na Pareto hranici (len pri viacerých cieľoch)
    pareto: list[int] = field(default_factory=list)
    #: výber podľa okolia: kandidáti, ich okolie a vybraná epocha
    plateau: dict[str, Any] | None = None


class _Evaluator:
    """Config × okno -> súhrn, s pamäťou: tie isté body mriežky sa nepočítajú dvakrát."""

    def __init__(self, runner: NativeRunner, wallet: float, log: Callable[[str], None]) -> None:
        self.runner = runner
        self.wallet = wallet
        self.log = log
        self.seen: dict[tuple[str, str], dict[str, Any] | None] = {}

    def run(self, configs: Iterable[str], windows: Sequence[str]) -> None:
        nove = list(dict.fromkeys((c, w) for c in configs for w in windows if (c, w) not in self.seen))
        for (c, w), res in zip(nove, self.runner.run_many(nove) if nove else []):
            if "error" in res:
                self.log(f"  beh spadol v C#: {res['error']}")
            self.seen[(c, w)] = summary_of(res, self.runner.inst, self.runner.fee, self.wallet)

    def summaries(self, config: str | None, windows: Sequence[str]) -> dict[str, dict[str, Any] | None]:
        return {w: (self.seen.get((config, w)) if config is not None else None) for w in windows}


def _epoch(number: int, params: dict[str, Any], per_window: dict[str, dict[str, Any] | None], plan: Plan,
           how: str, objectives: Sequence[str], fold: int | None = None) -> Epoch:
    """Epocha zo súhrnov po oknách: loss = skladanie oknových lossov, metriky súčet/priemer/maximum."""
    straty = {w: loss_of(s, plan, window_days(w)) for w, s in per_window.items()}
    loss = aggregate(list(straty.values()), how)
    values = None
    if len(objectives) > 1:
        values = [loss] + [aggregate([objective_of(s, o, plan, window_days(w)) for w, s in per_window.items()], how)
                           for o in objectives[1:]]
    hotove = [s for s in per_window.values() if s is not None]

    def mean(key: str) -> float | None:
        cisla = [float(s[key]) for s in hotove if s.get(key) is not None]
        return round(statistics.fmean(cisla), 4) if cisla else None

    jedno = len(per_window) == 1
    s0 = hotove[0] if jedno and hotove else {}
    return Epoch(
        number=number, loss=loss, params=params,
        trades=sum(int(s.get("trades") or 0) for s in hotove),
        pnl_pct=s0.get("pnl_pct") if jedno else mean("pnl_pct"),
        winrate=s0.get("winrate") if jedno else mean("winrate"),
        max_drawdown_pct=s0.get("max_drawdown_pct") if jedno else (
            max((float(s["max_drawdown_pct"]) for s in hotove), default=None)),
        profit_factor=s0.get("profit_factor") if jedno else mean("profit_factor"),
        windows=None if jedno else {w: {"trades": (s or {}).get("trades"), "pnl_pct": (s or {}).get("pnl_pct"),
                                        "winrate": (s or {}).get("winrate"),
                                        "max_drawdown_pct": (s or {}).get("max_drawdown_pct"),
                                        "break_even_pct": (s or {}).get("break_even_pct"), "loss": straty[w]}
                                    for w, s in per_window.items()},
        values=values, fold=fold,
    )


def run_search(runner: NativeRunner, plan: Plan, profile: str | None, timerange: str, *, epochs: int = 200,
               sampler: str = "tpe", batch: int | None = None, seed: int | None = None, wallet: float = 10000,
               windows: Sequence[str] | None = None, aggregate_how: str = "min",
               objectives: Sequence[str] | None = None, select: str = "best",
               warm: Iterable[dict[str, Any]] | None = None, fold: int | None = None,
               log: Callable[[str], None] = print, should_stop: Callable[[], bool] | None = None,
               on_progress: Callable[[int, int], None] | None = None) -> Search:
    """Optuna ask/tell po dávkach: sampler navrhne `batch` epoch, C# ich spočíta naraz, späť ide loss.

    `windows` = okná kritéria (bez nich len `timerange`), `aggregate_how` ich skladá. `objectives` > 1 =
    viac cieľov naraz (prvý je vždy kritérium plánu). `select="plateau"` vyberie víťaza podľa okolia.
    `warm` = epochy predošlého hľadania (`Epoch.to_dict`), ktoré sa vložia do štúdie a do výsledku.
    `should_stop` sa pýta medzi dávkami (zrušenie z webapp), `on_progress(hotovo, spolu)` po každej
    dávke (priebeh a odhad vo fronte).
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    if select not in SELECTS:
        raise ValueError(f"neznámy výber {select!r}; známe: {', '.join(SELECTS)}")
    okna = tuple(dict.fromkeys(windows or (timerange,)))
    ciele = tuple(dict.fromkeys([plan.goal or "break_even", *(objectives or ())]))
    for o in ciele:
        if o not in OBJECTIVES:
            raise ValueError(f"neznámy cieľ {o!r}; známe: {', '.join(OBJECTIVES)}")
    multi = len(ciele) > 1
    spec = runner.spec
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    base = cfg.to_dict()
    batch = batch or max(1, runner.workers)
    kwargs = {"directions": ["minimize"] * len(ciele)} if multi else {"direction": "minimize"}
    study = optuna.create_study(sampler=_sampler(sampler, seed, min(epochs // 5 or 1, 4 * batch), multi), **kwargs)
    ev = _Evaluator(runner, wallet, log)

    found: list[Epoch] = []
    by_trial: dict[int, int] = {}       # číslo pokusu Optuna -> index v `found`
    dists = _distributions(plan)
    for row in warm or ():
        params = dict(row.get("params") or {})
        try:
            hodnoty = row.get("values") if multi else None
            if multi and (not hodnoty or len(hodnoty) != len(ciele)):
                continue            # epocha bez hodnôt všetkých cieľov sa do viac-cieľovej štúdie nevloží
            t = optuna.trial.create_trial(params=params, distributions=dists,
                                          values=hodnoty if multi else None,
                                          value=None if multi else float(row.get("loss", UNUSABLE)))
            study.add_trial(t)
        except (ValueError, TypeError):
            continue                # parameter mimo nového rozsahu - stará epocha do štúdie nepatrí
        by_trial[study.trials[-1].number] = len(found)
        found.append(replace(_epoch_from_dict(row), number=len(found) + 1))
    zaciatok = len(found)
    if zaciatok:
        log(f"  pokracovanie: {zaciatok} epoch z predosleho hladania vlozenych do studie")

    t0 = time.perf_counter()
    #: (čas, počet) po prvej dávke - tempo sa meria od nej, prvá nesie štart pracovných procesov a dáta
    prva: tuple[float, int] | None = None
    while len(found) - zaciatok < epochs:
        if should_stop is not None and should_stop():
            log("zrusene")
            break
        trials = [study.ask() for _ in range(min(batch, epochs - (len(found) - zaciatok)))]
        params = [_suggest(t, plan) for t in trials]
        configs: list[str | None] = []
        for p in params:
            try:
                configs.append(config_json(base, type(cfg), plan, p))
            except (ValueError, TypeError) as exc:   # config kombináciu odmietol
                configs.append(None)
                log(f"  epocha zamietnutá configom: {exc}")
        ev.run([c for c in configs if c is not None], okna)
        for trial, p, c in zip(trials, params, configs):
            e = _epoch(len(found) + 1, p, ev.summaries(c, okna), plan, aggregate_how, ciele, fold)
            study.tell(trial, e.values if multi else e.loss)
            by_trial[trial.number] = len(found)
            found.append(e)
        hotovo = len(found) - zaciatok
        if on_progress is not None:
            on_progress(hotovo, epochs)
        best = min((e for e in found if e.usable), key=lambda e: e.loss, default=None)
        teraz = time.perf_counter()
        if prva is None:
            prva = (teraz, hotovo)
        postup = eta(hotovo, epochs, t0, prva[0], prva[1], teraz, teraz)
        tempo = (hotovo - prva[1]) / (teraz - prva[0]) if teraz > prva[0] and hotovo > prva[1] else None
        log(f"  {hotovo}/{epochs} epoch ({len(ev.seen)} roznych backtestov)"
            + (f", {tempo:.1f} epoch/s" if tempo else "")
            + (f", este ~{fmt_seconds(postup['eta_s'])}" if postup.get("eta_s") is not None else "")
            + f", ubehlo {fmt_seconds(teraz - t0)}"
            + (f", najlepsie skore {-best.loss:.4f} (epocha {best.number})" if best else ", zatial nic v mantineloch"))

    pareto: list[int] = []
    if multi:
        pareto = sorted(found[by_trial[t.number]].number for t in study.best_trials if t.number in by_trial)
        found = [replace(e, pareto=e.number in pareto) for e in found]
    plateau_info = None
    vitaz = min((e for e in found if e.usable), key=lambda e: e.loss, default=None)
    if vitaz is not None and select == "plateau":
        vitaz, plateau_info = _plateau_select(found, plan, base, type(cfg), okna, aggregate_how, ciele, ev, log)
    if vitaz is not None:
        found = [replace(e, is_best=e.number == vitaz.number) for e in found]
        vitaz = next(e for e in found if e.is_best)
    return Search(plan=plan, epochs=found, best=vitaz, seconds=time.perf_counter() - t0, distinct=len(ev.seen),
                  windows=okna, aggregate=aggregate_how, objectives=ciele, pareto=pareto, plateau=plateau_info)


def _epoch_from_dict(row: dict[str, Any]) -> Epoch:
    from .hyperopt import epochs_from_dicts

    return epochs_from_dicts([row])[0]


def _plateau_select(found: list[Epoch], plan: Plan, base: dict[str, Any], cfg_cls: type, okna: Sequence[str],
                    how: str, ciele: Sequence[str], ev: _Evaluator,
                    log: Callable[[str], None]) -> tuple[Epoch, dict[str, Any]]:
    """Z `PLATEAU_TOP` najlepších rôznych epoch tá, ktorej okolie (±1 krok na každom parametri) drží najlepšie.

    Okolie je to isté ako v teste plató (`tester.plateau.neighbours`): mení sa vždy jeden parameter.
    Robustné skóre = priemer lossu epochy a všetkých jej susedov — sused mimo mantinelov ho potiahne
    nahor, takže osamelá špička prehrá so stredom širokého plató.
    """
    okolia = plateau_candidates(found, plan)
    for _e, body in okolia:
        for b in body:
            try:
                b["config"] = config_json(base, cfg_cls, plan, b["params"])
            except (ValueError, TypeError):
                b["config"] = None
    ev.run([b["config"] for _e, body in okolia for b in body if b["config"] is not None], okna)
    scored = [(e, e.loss, [(b, _epoch(0, b["params"], ev.summaries(b["config"], okna), plan, how, ciele).loss)
                           for b in body]) for e, body in okolia]
    info = plateau_choice(scored)
    log(f"  vyber podla okolia: epocha {info['chosen']} (najlepsia epocha {info['best_epoch']})")
    return next(e for e in found if e.number == info["chosen"]), info


# --------------------------------------------------------------------------- #
# walk-forward
# --------------------------------------------------------------------------- #


@dataclass
class WalkForward:
    folds: list[dict[str, Any]]
    epochs: list[Epoch]
    seconds: float
    verdict: str
    #: parametre posledného foldu (naladené na najnovšie dáta) — kandidát na nasadenie
    last: dict[str, Any] | None


def walk_forward(runner: NativeRunner, plan: Plan, profile: str | None, windows: Sequence[str], *,
                 epochs: int = 200, anchored: bool = False, sampler: str = "tpe", seed: int | None = None,
                 wallet: float = 10000, aggregate_how: str = "min", select: str = "best",
                 batch: int | None = None, log: Callable[[str], None] = print,
                 should_stop: Callable[[], bool] | None = None,
                 on_progress: Callable[[int, int], None] | None = None) -> WalkForward:
    """Ladí na okne N (s `anchored` na všetkých do N), víťaza zmeria na N+1; toľko foldov, koľko okien mínus jedno.

    Každé testovacie okno optimalizátor nevidel — skóre za sebou sú to najbližšie k „ako by to dopadlo
    naživo, keby sa parametre preladili raz za rok".
    """
    okna = list(dict.fromkeys(windows))
    if len(okna) < 2:
        raise ValueError("walk-forward potrebuje aspoň dve okná")
    t0 = time.perf_counter()
    folds: list[dict[str, Any]] = []
    vsetky: list[Epoch] = []
    spolu = epochs * (len(okna) - 1)
    spec = runner.spec
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    for i in range(len(okna) - 1):
        if should_stop is not None and should_stop():
            break
        train = tuple(okna[: i + 1]) if anchored else (okna[i],)
        test = okna[i + 1]
        log(f"fold {i + 1}/{len(okna) - 1}: ladenie {'+'.join(train)} -> test {test}")
        hotove = len(vsetky)
        s = run_search(runner, plan, profile, train[-1], epochs=epochs, sampler=sampler, batch=batch,
                       seed=None if seed is None else seed + i, wallet=wallet, windows=train,
                       aggregate_how=aggregate_how, select=select, fold=i, log=log, should_stop=should_stop,
                       on_progress=(lambda d, _t, h=hotove: on_progress(h + d, spolu)) if on_progress else None)
        offset = len(vsetky)
        vsetky.extend(replace(e, number=offset + e.number) for e in s.epochs)
        fold: dict[str, Any] = {"fold": i, "train": list(train), "test": test, "epochs": len(s.epochs)}
        if s.best is None:
            fold.update(params=None, train_loss=None, result=None, edge=None)
            folds.append(fold)
            continue
        cj = config_json(cfg.to_dict(), type(cfg), plan, s.best.params)
        res = runner.run([cj], test)[0]
        summ = summary_of(res, runner.inst, runner.fee, wallet)
        edge = edge_of({"result": summ or {}, "settings": {"fee": runner.fee}})
        fold.update(params=overrides(plan, s.best.params), hp=s.best.params, train_loss=s.best.loss,
                    train_score=-s.best.loss, result=summ, edge=edge, test_loss=loss_of(summ, plan, window_days(test)))
        folds.append(fold)
        log(f"  fold {i + 1}: ladene skore {-s.best.loss:.4f}, test break-even {((summ or {}).get('break_even_pct'))} "
            f"(nad poplatkom {edge if edge is None else round(edge, 4)})")
    text = walk_forward_verdict(folds)
    posledny = next((f.get("params") for f in reversed(folds) if f.get("params")), None)
    return WalkForward(folds=folds, epochs=vsetky, seconds=time.perf_counter() - t0, verdict=text, last=posledny)


def walk_forward_verdict(folds: Sequence[dict[str, Any]]) -> str:
    """Jedna veta o walk-forward: v koľkých testovacích oknách (ktoré optimalizátor nevidel) je edge nad poplatkom."""
    kladne = sum(1 for f in folds if (f.get("edge") or 0) > 0 and ((f.get("result") or {}).get("trades") or 0) > 0)
    n = len(folds)
    if n == 0:
        return "Walk-forward nedobehol."
    if kladne == n:
        return (f"WALK-FORWARD DRZI: break-even nad poplatkom vo vsetkych {n} testovacich oknach, ktore "
                "optimalizator nevidel.")
    if kladne == 0:
        return (f"WALK-FORWARD NEDRZI: ani v jednom z {n} testovacich okien nie je break-even nad poplatkom - "
                "preladovanie hlada sum, nie strategiu.")
    return f"WALK-FORWARD NEJASNE: break-even nad poplatkom v {kladne} z {n} testovacich okien."


def plateau_candidates(found: Sequence[Epoch], plan: Plan, top: int = PLATEAU_TOP) -> list[tuple[Epoch, list[dict[str, Any]]]]:
    """Najlepšie rôzne epochy a ich okolie (±1 krok na každom parametri) — pre oba enginy rovnako."""
    from . import plateau as pl

    space = space_text(plan)
    kandidati: list[Epoch] = []
    videne: set[str] = set()
    for e in sorted((e for e in found if e.usable), key=lambda e: e.loss):
        kluc = json.dumps(e.params, sort_keys=True, default=str)
        if kluc not in videne:
            videne.add(kluc)
            kandidati.append(e)
        if len(kandidati) >= top:
            break
    out = []
    for e in kandidati:
        stred = {k.name: e.params.get(k.attr) for k in plan.knobs}
        body = []
        for n in pl.neighbours(space, stred, steps=(-1, 1)):
            p = dict(e.params)
            p["hp_" + n.param] = n.value
            body.append({"param": n.param, "value": n.value, "step": n.step, "params": p})
        out.append((e, body))
    return out


def plateau_choice(scored: Sequence[tuple[Epoch, float, list[tuple[dict[str, Any], float]]]]) -> dict[str, Any]:
    """`[(epocha, loss stredu, [(sused, loss)])]` -> kandidáti s robustným skóre a vybraná epocha."""
    vysledky = []
    for e, stred, susedia in scored:
        straty = [s for _b, s in susedia]
        vysledky.append({"epoch": e.number, "loss": stred, "robust": statistics.fmean([stred, *straty]),
                         "neighbours": len(susedia), "worst": max(straty, default=stred),
                         "points": [{"param": b["param"], "value": b["value"], "step": b["step"], "loss": s}
                                    for b, s in susedia]})
    vybrana = min(vysledky, key=lambda v: v["robust"])
    return {"candidates": vysledky, "chosen": vybrana["epoch"], "best_epoch": scored[0][0].number}


# --------------------------------------------------------------------------- #
# overenie
# --------------------------------------------------------------------------- #


def verify(runner: NativeRunner, plan: Plan, profile: str | None, params: dict[str, Any],
           tuned: "str | Iterable[str]", wallet: float = 10000,
           windows: tuple[str, ...] = REFERENCE_WINDOWS) -> list[dict[str, Any]]:
    """Parametre na referenčných oknách (jedna dávka) — záznamy v tvare, aký čaká `hyperopt.verdict`."""
    spec = runner.spec
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    cj = config_json(cfg.to_dict(), type(cfg), plan, params)
    ladene = [tuned] if isinstance(tuned, str) else list(tuned)
    okna = list(windows) + [w for w in ladene if w not in windows]
    out = []
    for okno, res in zip(okna, runner.run_many([(cj, w) for w in okna])):
        s = summary_of(res, runner.inst, runner.fee, wallet)
        out.append({"status": "done" if s is not None else "failed", "result": s or {},
                    "settings": {"timerange": okno, "fee": runner.fee}, "tuned": okno in ladene})
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


def _folds_table(folds: list[dict[str, Any]]) -> str:
    lines = [f"{'fold':>4}  {'ladene':>37}  {'test':>17}  {'ladene skore':>12}  {'test BE %':>9}  {'nad popl.':>9}"]
    for f in folds:
        r = f.get("result") or {}
        lines.append(f"{f['fold'] + 1:>4}  {'+'.join(f['train'])[-37:]:>37}  {f['test']:>17}  "
                     f"{'-' if f.get('train_score') is None else round(f['train_score'], 4):>12}  "
                     f"{'-' if r.get('break_even_pct') is None else r['break_even_pct']:>9}  "
                     f"{'-' if f.get('edge') is None else round(f['edge'], 4):>9}")
    return "\n".join(lines)


def _windows_arg(text: str | None) -> list[str] | None:
    if not text:
        return None
    if text.strip() == "ref":
        return list(REFERENCE_WINDOWS)
    return [w.strip() for w in text.split(",") if w.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--instrument", required=True, help="kľúč z tradebot.core.types.INSTRUMENTS")
    ap.add_argument("--timeframe", help="default = TF stratégie")
    ap.add_argument("--timerange", default="20240904-20250904")
    ap.add_argument("--param", action="append", default=[], metavar="POLE=OD:DO:KROK|A,B,C")
    ap.add_argument("--suggested", action="store_true", help="priestor, ktorý odporúča stratégia")
    ap.add_argument("--goal", default="break_even", choices=("break_even", "profit", "winrate", "drawdown", "pf"))
    ap.add_argument("--max-dd", type=float)
    ap.add_argument("--min-trades", type=int, help="obchodov za rok")
    ap.add_argument("--epochs", type=int, default=200, help="epoch (pri walk-forward na každý fold)")
    ap.add_argument("--sampler", default="tpe", choices=SAMPLERS)
    ap.add_argument("--windows", help="okná kritéria oddelené čiarkou, alebo `ref` (päť referenčných); "
                                      "bez toho len --timerange")
    ap.add_argument("--aggregate", default="min", choices=AGGREGATES,
                    help="skóre z viacerých okien: min = najhoršie okno, median, mean")
    ap.add_argument("--objectives", help="ďalšie ciele k --goal, napr. drawdown,trades (Pareto; nsga2 alebo tpe)")
    ap.add_argument("--select", default="best", choices=SELECTS, help="víťaz: najlepšia epocha alebo najlepšie okolie")
    ap.add_argument("--walk-forward", action="store_true", help="ladiť na okne N, merať na N+1 (okná z --windows, inak ref)")
    ap.add_argument("--anchored", action="store_true", help="walk-forward: ladiť na všetkých oknách do N")
    ap.add_argument("--continue", dest="cont", help="JSON z predošlého --out: jeho epochy sa vložia a hľadá sa ďalej")
    ap.add_argument("--jobs", type=int, default=0, help="pracovné procesy C# (0 = všetky jadrá); dávka sampleru je rovnaká")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--wallet", type=float, default=10000)
    ap.add_argument("--out", help="JSON s epochami a overením (default: nič sa neukladá)")
    a = ap.parse_args(argv)

    from .hyperopt import suggested

    space = dict(p.split("=", 1) for p in a.param)
    if a.suggested:
        space = {**suggested(a.strategy), **space}
    if not space:
        ap.error("aspoň jeden --param (alebo --suggested)")
    plan = build_plan(space, strategy=a.strategy, goal=a.goal, max_dd=a.max_dd, min_trades=a.min_trades)
    spec = get_spec(a.strategy)
    tf = timeframe_minutes(a.timeframe or spec.default_timeframe)
    runner = NativeRunner(a.strategy, INSTRUMENTS[a.instrument], tf, a.fee, a.jobs)
    objectives = [o.strip() for o in (a.objectives or "").split(",") if o.strip()]
    okna = _windows_arg(a.windows)

    if a.walk_forward:
        wf_okna = okna or list(REFERENCE_WINDOWS)
        print(f"walk-forward {a.strategy} {a.instrument} {tf}m: {len(wf_okna) - 1} foldov po {a.epochs} epoch, "
              f"sampler {a.sampler}" + (", anchored" if a.anchored else ""))
        wf = walk_forward(runner, plan, a.profile, wf_okna, epochs=a.epochs, anchored=a.anchored, sampler=a.sampler,
                          seed=a.seed, wallet=a.wallet, aggregate_how=a.aggregate, select=a.select,
                          batch=a.jobs or None)
        print(f"\n{len(wf.epochs)} epoch za {wf.seconds:.1f} s\n")
        print(_folds_table(wf.folds))
        print("\n" + wf.verdict)
        if wf.last:
            print(f"\nparametre posledneho foldu: {json.dumps(wf.last, ensure_ascii=False)}")
        if a.out:
            Path(a.out).write_text(json.dumps({
                "mode": "walkforward", "plan": plan.to_dict(), "instrument": a.instrument, "timeframe": tf,
                "windows": wf_okna, "anchored": a.anchored, "sampler": a.sampler, "fee": a.fee,
                "seconds": wf.seconds, "folds": wf.folds, "verdict": wf.verdict, "last": wf.last,
                "epochs": [e.to_dict() for e in wf.epochs],
            }, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
            print(f"\nulozene: {a.out}")
        return 0

    warm = None
    if a.cont:
        warm = json.loads(Path(a.cont).read_text(encoding="utf-8")).get("epochs") or []
    print(f"natívny hyperopt {a.strategy} {a.instrument} {tf}m {', '.join(okna or [a.timerange])}: {a.epochs} epoch, "
          f"sampler {a.sampler}, kritérium {a.goal}" + (f" ({a.aggregate} cez okná)" if okna and len(okna) > 1 else "")
          + (f", ciele {', '.join(objectives)}" if objectives else "") + (", výber podľa okolia" if a.select == "plateau" else ""))
    search = run_search(runner, plan, a.profile, (okna or [a.timerange])[-1], epochs=a.epochs, sampler=a.sampler,
                        batch=a.jobs or None, seed=a.seed, wallet=a.wallet, windows=okna, aggregate_how=a.aggregate,
                        objectives=objectives, select=a.select, warm=warm)
    print(f"\n{len(search.epochs)} epoch ({search.distinct} roznych backtestov) za {search.seconds:.1f} s\n")
    print(table(search.epochs, plan))
    if search.pareto:
        print(f"\nPareto hranica ({len(search.pareto)} epoch): {', '.join(map(str, search.pareto[:30]))}")
    if search.best is None:
        print("\nziadna epocha nesplnila mantinely - overenie sa nerobi")
        return 1
    best = overrides(plan, search.best.params)
    print(f"\nvitaz: {json.dumps(best, ensure_ascii=False)}\n")
    tuned = list(search.windows)
    records = verify(runner, plan, a.profile, search.best.params, tuned, a.wallet)
    print(_verification_table(records))
    print("\n" + verdict(records, tuned))
    if a.out:
        Path(a.out).write_text(json.dumps({
            "mode": "search", "plan": plan.to_dict(), "instrument": a.instrument, "timeframe": tf,
            "timerange": a.timerange, "windows": tuned, "aggregate": a.aggregate, "objectives": list(search.objectives),
            "select": a.select, "sampler": a.sampler, "fee": a.fee, "seconds": search.seconds, "best": best,
            "pareto": search.pareto, "plateau": search.plateau,
            "epochs": [e.to_dict() for e in search.epochs], "verification": records,
        }, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nulozene: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
