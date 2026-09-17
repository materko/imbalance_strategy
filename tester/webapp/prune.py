"""Odpratanie histórie behov do tvaru, ktorý patrí do gitu — `cli prune`.

    python -m tester.webapp.cli prune                  # len plán: čo a koľko by sa odpratalo
    python -m tester.webapp.cli prune --apply          # vykonať
    python -m tester.webapp.cli prune --apply --keep-charts   # kresby presunúť do cache, nemazať

Dve veci, ktoré do histórie v gite nepatria:

1. **Kresby grafu** (`runs/<id>/chart.json.gz`) — megabajt na beh. Graf sa dá z configu
   behu prepočítať (`tester.webapp.replay`). Skôr než kresby zmiznú, vyberie sa z nich
   `plan.json` (SL/TP obchodov), aby analytika Freqtrade behov nestratila plánované RR.
2. **Body mriežok, buniek matíc, overení a susedov víťaza hyperoptu** — behy so značkou
   `sweep`/`matrix`/`hyperopt_run`/`plateau`. Najprv sa prevedú do `tester/sweeps/`
   (tabuľka bodov s celým configom a výsledkom, pri overení aj interval víťaza z Monte Carla),
   až potom sa ich adresáre zmažú. Nič sa nestratí: každý bod sa dá prehrať (`cli replay`).

Bez `--apply` sa nič nezapíše ani nezmaže. Poradie pri vykonaní je zámerne „najprv zapíš,
potom maž": keby sa niečo pokazilo uprostred, ostane viac, nie menej.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .batches import add_to, batch_tag, new_batch
from .store import CHART_FILE, PLAN_FILE, RunStore, plan_objects, read_chart_file, strategy_of, write_plan

__all__ = ["Plan", "plan", "report", "apply"]


def _dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


@dataclass
class Plan:
    runs: int = 0
    runs_bytes: int = 0
    #: (run_id, bajty) kresieb v adresároch behov, ktoré ostávajú v histórii
    charts: list[tuple[str, int]] = field(default_factory=list)
    #: behy s kresbami a obchodmi, ktorým chýba `plan.json` (vyberie sa pred zmazaním)
    plans_to_extract: int = 0
    #: druh -> celok -> [(run_id, bajty adresára)]
    children: dict[str, dict[str, list[tuple[str, int]]]] = field(default_factory=dict)
    #: celky, ktoré už v `sweeps/` sú (body sa do nich doplnia)
    existing_batches: int = 0
    #: odhad veľkosti súborov v `sweeps/` po prevode (bez intervalov víťaza)
    batches_bytes: int = 0

    @property
    def child_runs(self) -> int:
        return sum(len(v) for celky in self.children.values() for v in celky.values())

    @property
    def child_bytes(self) -> int:
        return sum(b for celky in self.children.values() for v in celky.values() for _, b in v)

    @property
    def chart_bytes(self) -> int:
        return sum(b for _, b in self.charts)


def plan(store: RunStore) -> Plan:
    """Čo by `apply` spravil — nič nezapisuje."""
    out = Plan()
    celky: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in store.all():
        run_id = rec["id"]
        d = store.root / run_id
        velkost = _dir_size(d)
        out.runs += 1
        out.runs_bytes += velkost
        found = batch_tag(rec.get("settings"))
        if found is not None:
            kind, tag = found
            out.children.setdefault(kind, {}).setdefault(str(tag["id"]), []).append((run_id, velkost))
            kluc = (kind, str(tag["id"]))
            celky.setdefault(kluc, new_batch(rec))
            add_to(celky[kluc], {k: v for k, v in rec.items() if k != "series"})
            continue
        chart = d / CHART_FILE
        if chart.exists():
            out.charts.append((run_id, chart.stat().st_size))
            if not (d / PLAN_FILE).exists() and (d / "trades.json").exists() \
                    and ((rec.get("result") or {}).get("trades") or 0) > 0:
                out.plans_to_extract += 1
    out.batches_bytes = sum(len(json.dumps(d, ensure_ascii=False, indent=1, default=str).encode("utf-8"))
                            for d in celky.values())
    out.existing_batches = sum(1 for kind, celky in out.children.items() for bid in celky
                               if store.batches.get(kind, bid) is not None)
    return out


def _mb(n: int) -> str:
    return f"{n / 1e6:,.1f} MB".replace(",", " ")


def report(p: Plan) -> str:
    zostane = p.runs_bytes - p.child_bytes - p.chart_bytes
    riadky = [
        f"historia: {p.runs} behov, {_mb(p.runs_bytes)}",
        "",
        f"1) kresby grafu v adresaroch behov: {len(p.charts)} suborov, {_mb(p.chart_bytes)}",
        f"   plan.json sa pred zmazanim vyberie z {p.plans_to_extract} behov (SL/TP pre analytiku)",
        "",
        f"2) body hromadnych behov: {p.child_runs} behov, {_mb(p.child_bytes)} "
        "(prevedu sa do tester/sweeps/, adresare sa zmazu)",
        f"   tester/sweeps/ po prevode: ~{_mb(p.batches_bytes)}",
    ]
    for kind in ("sweep", "matrix", "hyperopt_run", "plateau"):
        celky = p.children.get(kind) or {}
        if celky:
            riadky.append(f"   {kind:<13} {len(celky):>4} celkov, {sum(len(v) for v in celky.values()):>5} "
                          f"behov, {_mb(sum(b for v in celky.values() for _, b in v))}")
    if p.existing_batches:
        riadky.append(f"   ({p.existing_batches} celkov uz v tester/sweeps/ je - body sa doplnia)")
    riadky += ["", f"po odpratani ostane v tester/runs/ {p.runs - p.child_runs} behov, "
                   f"~{_mb(max(zostane, 0))} (bez kresieb a bodov)"]
    return "\n".join(riadky)


def apply(store: RunStore, p: Plan | None = None, *, keep_charts: bool = False,
          log: Callable[[str], None] = print) -> dict[str, Any]:
    """Vykoná plán: zapíše celky a plány, potom maže. Vracia počty."""
    from .. import plateau as pl

    p = p or plan(store)
    zapisane_celky = 0
    for kind, celky in p.children.items():
        for batch_id, behy in celky.items():
            data = store.batches.get(kind, batch_id)
            for run_id, _ in sorted(behy):
                rec = store.get(run_id)
                if rec is None:
                    continue
                data = data or new_batch(rec)
                extra: dict[str, Any] = {}
                if kind == "hyperopt_run":
                    lo, hi = pl.winner_ci(rec, store.trades(run_id))
                    if lo is not None:
                        extra["break_even_ci"] = {"lo": lo, "hi": hi,
                                                  "trades": (rec.get("result") or {}).get("trades"),
                                                  "iterations": pl.MC_ITERATIONS, "seed": pl.MC_SEED}
                rec.pop("series", None)
                add_to(data, rec, extra)
            if data is not None:
                store.batches.write(data)
                zapisane_celky += 1
    log(f"zapisane celky: {zapisane_celky}")

    plany = 0
    for run_id, _ in p.charts:
        d = store.root / run_id
        if (d / PLAN_FILE).exists() or not (d / "trades.json").exists():
            continue
        rec = store.get(run_id) or {}
        trades = store.trades(run_id)
        if trades:
            write_plan(d / PLAN_FILE, plan_objects(read_chart_file(d / CHART_FILE), trades,
                                                   strategy_of(rec),
                                                   (rec.get("settings") or {}).get("engine") or ""))
            plany += 1
    log(f"vybrane plan.json: {plany}")

    # az teraz maze
    kresby = 0
    for run_id, _ in p.charts:
        zdroj = store.root / run_id / CHART_FILE
        if not zdroj.exists():
            continue
        if keep_charts:
            store.put_chart(run_id, zdroj, {"source": "legacy", "match": True})
        else:
            zdroj.unlink()
        kresby += 1
    body = 0
    for celky in p.children.values():
        for batch_id, behy in celky.items():
            for run_id, _ in behy:
                if store.batches.find(run_id) is None:
                    log(f"POZOR: {run_id} sa v tester/sweeps/ nenasiel, adresar ostava")
                    continue
                shutil.rmtree(store.root / run_id, ignore_errors=True)
                body += 1
    log(f"kresby {'presunute do cache' if keep_charts else 'zmazane'}: {kresby}, zmazane adresare bodov: {body}")
    return {"batches": zapisane_celky, "plans": plany, "charts": kresby, "child_runs": body}
