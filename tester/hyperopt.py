"""Hyperopt pre testera: to isté zadanie ako sweep, len sa v ňom hľadá namiesto prechádzania.

    PY -m tester.webapp.cli hyperopt --param rrRatio=2:8:0.5 --param slLookback=5:40:1 \\
        --goal winrate --max-dd 15 --epochs 200 --timerange 20250904-20260904

### Sweep vs hyperopt
Zadanie je **rovnaké** — tie isté `--param`, tie isté kritériá aj mantinely (`tester.sweep`).
Líši sa, čo sa s ním stane:

| | sweep | hyperopt |
|---|---|---|
| čo urobí | prejde všetky body mriežky | hľadá v rozsahu, učí sa z odpovedí |
| koľko behov | presne toľko, koľko bodov | koľko epoch zadáš |
| `2:8:0.5` | 13 hodnôt | spojito medzi 2 a 8, po desatinách |
| `3,5,8` | 3 hodnoty | 3 možnosti (aj tu) |
| výsledok v histórii | každý bod ako beh | víťaz ako beh, epochy v `.fthypt` |
| kedy | 1–2 parametre, chcem vidieť tvar | 3 a viac parametrov |

Preto sa zadanie neprepisuje: tester napíše hodnoty raz a rozhodne sa až, čo s nimi
(`sweep.to_knob`).

### Prečo je overenie na ďalších oknách povinná časť, nie doplnok
Hyperopt nájde optimum ladeného okna. To nie je to isté ako dobrá stratégia: prvá verzia
priestoru ladila desať prahov a víťazná epocha mala na ladenom roku +34,8 %, kým **všetky
štyri** ostatné roky boli stratové (−11 % až −65 %), viď
[docs/merania/HYPEROPT_btcusdt_2026-09-04.md]. Preto `hyperopt` po skončení pustí víťazné
parametre ako obyčajné backtesty na referenčných oknách a výsledky ukáže vedľa seba.
Ladené okno je medzi nimi označené — je to jediné, ktoré optimalizátor videl.

Behy sú obyčajné behy v histórii (`tester/runs/`), takže sa dajú otvoriť, porovnať aj
prehnať Monte Carlom, a nesú značku `hyperopt`, aby sa k celku dalo vrátiť.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from tradebot.adapters.freqtrade.hyperplan import Plan, knowledge
from tradebot.core.paths import REPO
from tradebot.strategies import get_spec

from . import sweep as sweep_mod

__all__ = [
    "REFERENCE_WINDOWS", "DEFAULT_EPOCHS", "LOSS_CLASS", "RESULTS_DIR", "Epoch",
    "build_plan", "suggested", "plan_path", "latest_results", "command", "read_results",
    "best", "overrides", "table", "verdict", "knowledge_note", "warnings_for",
    "edge_of", "epochs_from_dicts", "detail", "verification_rows",
]

#: Päť referenčných okien repozitára — na nich sa hodnotí každá zmena parametra.
#: Rovnaké ako v CLAUDE.md; jedno okno o stratégii nepovie nič.
REFERENCE_WINDOWS = (
    "20211001-20221001", "20221001-20231001", "20231001-20241001",
    "20240904-20250904", "20250904-20260904",
)

#: Epoch je celý backtest ladeného okna. 200 je asi hodina na roku s 1m detailom.
DEFAULT_EPOCHS = 200

#: Loss funkcia, ktorá číta kritérium z plánu (deploy/freqtrade/user_data/hyperopts/).
LOSS_CLASS = "TradebotPlanLoss"

#: Kam sa píšu plány behov — vedľa dočasných profilov, aby ich bolo kde nájsť.
PLANS_DIR = REPO / "tester" / "runs" / ".plans"

#: Kam Freqtrade píše epochy (`.fthypt`). Jeho vlastný adresár, nie náš.
RESULTS_DIR = REPO / "deploy" / "freqtrade" / "user_data" / "hyperopt_results"


# --------------------------------------------------------------------------- #
# zadanie
# --------------------------------------------------------------------------- #


def build_plan(space: dict[str, str], *, strategy: str = "ibs", goal: str = "break_even",
               max_dd: float | None = None, min_trades: int | None = None,
               note: str = "", meta: dict[str, Any] | None = None) -> Plan:
    """Plán z toho istého textu, aký tester píše sweepu (`rrRatio=2:8:0.5`)."""
    if goal not in sweep_mod.GOALS:
        raise ValueError(f"neznáme kritérium {goal!r}; známe: {', '.join(sweep_mod.GOALS)}")
    knobs: dict[str, Any] = {}
    for name, text in space.items():
        try:
            knobs[name] = sweep_mod.to_knob(text)
        except ValueError as exc:
            raise ValueError(f"{name}: {exc}") from None
    return Plan.from_dict({"strategy": strategy, "goal": goal, "max_dd": max_dd,
                           "min_trades": min_trades, "note": note, "knobs": knobs,
                           "meta": meta or {}})


def suggested(strategy: str = "ibs") -> dict[str, str]:
    """Odporúčanie stratégie ako text pre formulár — `{"rrRatio": "2:8:0.5", ...}`.

    Odporúčania sú vedomosť stratégie (`hyperopt_cls.SUGGESTED`), nie tohto modulu; tu sa
    len prekladajú do tvaru, v akom ich tester vidí vo formulári a môže prepísať.
    """
    out: dict[str, str] = {}
    for name, opts in knowledge(get_spec(strategy)).suggested_plan().items():
        if "choices" in opts:
            out[name] = ",".join(str(c).lower() if isinstance(c, bool) else str(c)
                                 for c in opts["choices"])
        else:
            krok = opts.get("step") or (1 if float(opts["high"]).is_integer()
                                        and float(opts["low"]).is_integer() else 0.1)
            out[name] = f"{opts['low']:g}:{opts['high']:g}:{krok:g}"
    return out


def plan_path(run_id: str, plan: Plan) -> Path:
    """Zapíše plán na disk — Freqtrade ho vidí len cez `TRADEBOT_HYPEROPT_PLAN`."""
    return plan.save(PLANS_DIR / f"{run_id}.json")


def command(python: str, *, plan: Path, config: Path, userdir: Path, datadir: Path,
            strategy_class: str, pair: str, timerange: str, timeframe: str,
            epochs: int = DEFAULT_EPOCHS, detail: str | None = "1m",
            wallet: float = 10000, fee: float | None = None,
            seed: int | None = None, jobs: int | None = None) -> list[str]:
    """Príkaz `freqtrade hyperopt` pre plán.

    `--analyze-per-epoch` je **povinné**: Freqtrade štandardne počíta `populate_indicators`
    raz pre celý beh a per-epochu prepočítava len `populate_entry_trend`, lebo predpokladá,
    že priestor „buy" ovplyvňuje iba signály. Celý náš engine beží v `populate_indicators`,
    takže bez toho prepínača dá každá epocha ten istý výsledok — prvých 200 epoch malo
    identický PnL, kým sa to našlo.
    """
    cmd = [
        # nie holý freqtrade: obal najprv zaregistruje fiktívnu burzu Tester
        python, "-m", "tester.ftrun", "hyperopt",
        "--config", str(config),
        "--userdir", str(userdir),
        "--datadir", str(datadir),
        "--strategy", strategy_class,
        "--hyperopt-loss", LOSS_CLASS,
        "--spaces", "plan",
        "--analyze-per-epoch",
        "--epochs", str(int(epochs)),
        "--timerange", timerange,
        "--pairs", pair,
        "--timeframe", timeframe,
        "--dry-run-wallet", str(wallet),
    ]
    if detail:
        cmd += ["--timeframe-detail", detail]
    if fee is not None:
        cmd += ["--fee", str(fee)]
    if seed is not None:
        cmd += ["--random-state", str(int(seed))]
    if jobs:
        cmd += ["-j", str(int(jobs))]
    return cmd


def latest_results(after: float = 0.0) -> Path | None:
    """Najnovší `.fthypt` vzniknutý po `after` (čas štartu behu).

    Meno súboru si Freqtrade určuje sám (`strategy_<Trieda>_<čas>.fthypt`) a `hyperopt`
    prepínač na jeho zmenu nemá — `--hyperopt-filename` patrí až `hyperopt-list`. Beh sa
    preto pozná podľa času vzniku, nie podľa mena.
    """
    if not RESULTS_DIR.exists():
        return None
    subory = [f for f in RESULTS_DIR.glob("*.fthypt") if f.stat().st_mtime >= after - 1]
    return max(subory, key=lambda f: f.stat().st_mtime) if subory else None


def knowledge_note(strategy: str = "ibs") -> str:
    """Veta stratégie o tom, čo o jej ladení vieme (`hyperopt_cls.NOTE`)."""
    return knowledge(get_spec(strategy)).NOTE


def warnings_for(space: Iterable[str], strategy: str = "ibs") -> list[str]:
    """Varovania stratégie k vybraným parametrom — nie zákaz, ale nech to tester vie."""
    warn = knowledge(get_spec(strategy)).WARN
    return [f"{name}: {warn[name]}" for name in space if name in warn]


# --------------------------------------------------------------------------- #
# výsledky
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Epoch:
    """Jedna epocha z `.fthypt` — len to, čo tester potrebuje vidieť."""

    number: int
    loss: float
    params: dict[str, Any]
    trades: int
    pnl_pct: float | None
    winrate: float | None
    max_drawdown_pct: float | None
    profit_factor: float | None
    is_best: bool = False

    @property
    def usable(self) -> bool:
        """Epocha mimo mantinelov má penalizované skóre — loss nad tisíc je jej podpis."""
        return self.loss < 1000.0 and self.trades > 0

    def to_dict(self) -> dict[str, Any]:
        return {"epoch": self.number, "loss": self.loss, "params": dict(self.params),
                "trades": self.trades, "pnl_pct": self.pnl_pct, "winrate": self.winrate,
                "max_drawdown_pct": self.max_drawdown_pct, "profit_factor": self.profit_factor,
                "usable": self.usable, "is_best": self.is_best}


def _metric(m: dict[str, Any], key: str, factor: float = 1.0) -> float | None:
    value = m.get(key)
    return None if value is None else round(float(value) * factor, 4)


def read_results(path: str | Path) -> list[Epoch]:
    """Epochy z `.fthypt` (JSON na riadok), v poradí, v akom bežali."""
    out: list[Epoch] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        m = row.get("results_metrics") or {}
        out.append(Epoch(
            number=int(row.get("current_epoch") or len(out) + 1),
            loss=float(row.get("loss", 0.0)),
            params=dict(row.get("params_dict") or {}),
            trades=int(m.get("total_trades") or 0),
            pnl_pct=_metric(m, "profit_total", 100.0),
            winrate=_metric(m, "winrate", 100.0) if "winrate" in m else _winrate(m),
            max_drawdown_pct=_metric(m, "max_drawdown_account", 100.0),
            profit_factor=_metric(m, "profit_factor"),
            is_best=bool(row.get("is_best")),
        ))
    return out


def _winrate(m: dict[str, Any]) -> float | None:
    wins, total = m.get("wins"), m.get("total_trades")
    if not total:
        return None
    return round(float(wins or 0) / float(total) * 100.0, 4)


def epochs_from_dicts(rows: Iterable[dict[str, Any]]) -> list[Epoch]:
    """Epochy z `epochs.json` behu (tvar `Epoch.to_dict`) späť na objekty."""
    out: list[Epoch] = []
    for row in rows:
        out.append(Epoch(
            number=int(row.get("epoch") or len(out) + 1), loss=float(row.get("loss") or 0.0),
            params=dict(row.get("params") or {}), trades=int(row.get("trades") or 0),
            pnl_pct=row.get("pnl_pct"), winrate=row.get("winrate"),
            max_drawdown_pct=row.get("max_drawdown_pct"), profit_factor=row.get("profit_factor"),
            is_best=bool(row.get("is_best")),
        ))
    return out


def best(epochs: Iterable[Epoch]) -> Epoch | None:
    """Najlepšia použiteľná epocha — najmenší loss. `None`, keď žiadna nesplnila mantinely."""
    pouzitelne = [e for e in epochs if e.usable]
    return min(pouzitelne, key=lambda e: e.loss) if pouzitelne else None


def overrides(plan: Plan, params: dict[str, Any]) -> dict[str, Any]:
    """Parametre epochy na hodnoty pre config — `hp_rrRatio: 4.5` → `rrRatio: 4.5`.

    Veľkostné pole sa vráti v tvare `{"value": …, "unit": …}`, teda tak, ako ho prijíma
    profil aj `--set` — víťaz sa dá rovno spustiť ako obyčajný beh alebo uložiť ako profil.
    """
    from tradebot.adapters.freqtrade.hyperplan import knob_kind

    spec = get_spec(plan.strategy)
    out: dict[str, Any] = {}
    for knob in plan.knobs:
        if knob.attr not in params:
            continue
        hodnota = params[knob.attr]
        kind, info = knob_kind(knob.name, spec)
        if kind == "int":
            out[knob.name] = int(hodnota)
        elif kind == "size":
            out[knob.name] = {"value": float(hodnota),
                              "unit": knob.unit or info.get("unit") or "abs"}
        elif kind == "float":
            out[knob.name] = float(hodnota)
        else:
            out[knob.name] = hodnota
    return out


# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "ano" if value else "nie"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def table(epochs: list[Epoch], plan: Plan, limit: int = 10) -> str:
    """Najlepšie epochy ako tabuľka — ASCII, konzola na Windows beží v cp1250."""
    poradie = sorted(epochs, key=lambda e: (not e.usable, e.loss))[:limit]
    if not poradie:
        return "ziadne epochy"
    names = [k.name for k in plan.knobs]
    head = [f"{'epocha':>7}"] + [f"{n[:14]:>14}" for n in names] + \
           [f"{'obchodov':>9}", f"{'PnL %':>8}", f"{'WR %':>7}", f"{'maxDD %':>8}", f"{'skore':>10}"]
    lines = ["  ".join(head), "-" * (len(" ".join(head)) + 2)]
    for e in poradie:
        cells = [f"{e.number:>7}"]
        cells += [f"{_fmt(e.params.get('hp_' + n)):>14}" for n in names]
        cells += [f"{e.trades:>9}", f"{_fmt(e.pnl_pct):>8}", f"{_fmt(e.winrate):>7}",
                  f"{_fmt(e.max_drawdown_pct):>8}", f"{-e.loss:>10.4f}"]
        riadok = "  ".join(cells)
        if not e.usable:
            riadok += "  <- mimo mantinelov"
        elif e is poradie[0]:
            riadok += "  <- najlepsi"
        lines.append(riadok)
    return "\n".join(lines)


def edge_of(record: dict[str, Any]) -> float | None:
    """Break-even behu **mínus poplatok**, s ktorým bežal (v % na stranu).

    Kladný break-even ešte nie je zisk: 0,01 % pri poplatku 0,05 % je strata. Preto sa
    okno hodnotí podľa toho, čo ostane nad nákladom — tá istá latka ako v celom repe.
    """
    r = record.get("result") or {}
    be = r.get("break_even_pct")
    if be is None:
        return None
    fee = float((record.get("settings") or {}).get("fee") or 0.0) * 100.0
    return float(be) - fee


def verdict(records: list[dict[str, Any]], tuned: str) -> str:
    """Jedna veta o tom, či víťaz prežil aj mimo ladeného okna.

    Toto je to, na čo sa hyperopt naráža: optimum ladeného okna nie je dobrá stratégia.
    Preto sa nehodnotí súčet, ale **znamienko po oknách** — a ladené okno sa počíta zvlášť,
    lebo je jediné, ktoré optimalizátor videl. Znamienko je break-even **nad poplatkom**
    behu (`edge_of`), nie nad nulou.
    """
    ostatne = [r for r in records if (r.get("settings", {}).get("timerange")) != tuned]
    hotove = [r for r in ostatne if r.get("status") == "done"]
    if not hotove:
        return "Overovacie behy nedobehli — bez nich sa vysledok hodnotit neda."

    kladne = [r for r in hotove
              if (edge_of(r) or 0) > 0
              and ((r.get("result") or {}).get("trades") or 0) > 0]
    n, k = len(hotove), len(kladne)
    if k == n:
        return (f"VITAZ PREZIL: break-even je nad poplatkom vo vsetkych {n} oknach mimo "
                "ladeneho. To je najlepsie, co sa da o najdenych parametroch povedat.")
    if k == 0:
        return (f"PRETRENOVANE: break-even je nad poplatkom len na ladenom okne, v {n} "
                "ostatnych nie. Optimalizator nasiel tvar TOHO okna, nie strategiu - "
                "parametre nepouzivaj.")
    return (f"NEJASNE: break-even je nad poplatkom v {k} z {n} okien mimo ladeneho. "
            "Pozri znamienko po rokoch, nie sucet; jedno dobre okno nestaci.")


def verification_rows(records: Iterable[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    """Overovacie behy víťaza (`settings.hyperopt_run.id == run_id`), zoradené po oknách."""
    out = [r for r in records
           if (((r.get("settings") or {}).get("hyperopt_run") or {}).get("id")) == run_id]
    return sorted(out, key=lambda r: (r.get("settings") or {}).get("timerange") or "")


def detail(record: dict[str, Any], epochs: Iterable[dict[str, Any]],
           verifications: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Detail hyperoptu — jeden tvar pre webapp endpoint aj CLI, aby sa nerozišli.

    `epochs` sú riadky `epochs.json` behu, `verifications` overovacie behy (hotové aj
    bežiace — kto ich má, ich sem dá).
    """
    from . import sweep as sweep_mod
    from .webapp.store import strategy_of

    nast = record.get("settings") or {}
    zadanie = nast.get("hyperopt") or {}
    overenia = verification_rows(verifications, record.get("id") or "")
    return {
        "id": record.get("id"),
        "status": record.get("status"),
        "error": record.get("error"),
        "note": record.get("note") or "",
        "strategy": strategy_of(record),
        "settings": {k: nast.get(k) for k in
                     ("pair", "timeframe", "timerange", "fee", "wallet", "exchange", "profile")},
        "hyperopt": zadanie,
        "goal_note": sweep_mod.describe(zadanie.get("goal") or "break_even",
                                        zadanie.get("max_dd"), zadanie.get("min_trades")),
        "params": list(zadanie.get("knobs") or {}),
        "epochs": sorted(epochs, key=lambda e: (not e.get("usable"), e.get("loss", 0)))[:60],
        "best": zadanie.get("best"),
        "overrides": zadanie.get("overrides"),
        "verify": [{
            "id": r.get("id"),
            "status": r.get("status"),
            "timerange": (r.get("settings") or {}).get("timerange"),
            "tuned": bool(((r.get("settings") or {}).get("hyperopt_run") or {}).get("tuned")),
            "result": {k: (r.get("result") or {}).get(k) for k in
                       ("trades", "pnl_pct", "winrate", "max_drawdown_pct", "break_even_pct")},
        } for r in overenia],
        "verdict": verdict(overenia, nast.get("timerange")) if overenia else "",
    }
