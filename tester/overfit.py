"""Štatistické brány SMERNICE V2 (krok 7, zadanie U9): PBO, haircut, Sortino, hranice a stav ✅ 🟡 ⏳ ⚠ ❌.

* **PBO** — *Probability of Backtest Overfitting* (Bailey, Borwein, López de Prado, Zhu 2015), metóda CSCV. Matica
  *konfigurácie × bloky*: mesačný PnL **všetkých** konfigurácií hypotézy z registra (`tester.register`) spojený do
  `S = 16` súvislých blokov. Všetky delenia blokov na polovicu „ladenie“ / „test“ (C(16,8) = 12 870); v každom sa
  vyberie víťaz ladiacej polovice a zmeria sa jeho poradie v teste. PBO = podiel delení, v ktorých skončil pod
  mediánom. Hranica **≤ 0,20**.
* **Haircut** — Harvey & Liu (2015), BHY: Sharpe najlepšej z `M` skúšok (M = N_eff, s ekonomickým dôvodom ½ N_eff)
  sa prepočíta cez p-hodnotu upravenú Benjamini–Hochberg–Yekutieli na „ohaircutovaný“ Sharpe. Ten musí byť > 0;
  PF po haircute = 1 + (PF − 1) × SR_h / SR, pod **1,10** je výsledok najviac ⏳.
* **PF_MC** — veľkosť pozície (krok 8b): 1 + (PF − 1) / 2, kým je obchodov < 300 (`pf_mc`, nie haircut).
* **Sortino** — ročné z denného PnL (každý pracovný deň, bez obchodu = 0), len z walk-forward OOS a trezorov, ≥ 1,0.
* **DSR** (`tester.robust.deflated_sharpe`) — ≥ 0,95 pri N_eff **a** ≥ 0,50 pri surovom N.
* **Stav** (`status`) — z brán: ❌ hypotéza uzavretá, ⏳ chýba meranie alebo PF po haircute < 1,10, 🟡 brány prešli
  (bez trezoru, legacy, hypotéza zo štúdie), ✅ len s podpisom používateľa v registri, ⚠ legacy so zápornou správou.

    PY -m tester.overfit pbo <hypotéza>                 # PBO z mesačného PnL registra
    PY -m tester.overfit haircut --sr 1.4 --days 900 --tests 40 --pf 1.45
    PY -m tester.overfit blocks 20211001-20250904 16    # bloky obdobia pre native_hyperopt --pbo
"""

from __future__ import annotations

import argparse
import itertools
import math
from datetime import datetime, timedelta, timezone
from statistics import NormalDist
from typing import Any, Iterable, Sequence

__all__ = ["blocks", "cscv", "pbo_of_epochs", "pbo_of_register", "month_blocks", "haircut_hl", "pf_after_haircut",
           "pf_mc", "sortino", "gates", "status", "GATES", "PBO_BLOCKS", "STATUS_TEXT", "main"]

#: Bloky CSCV (V2 U9: S = 16 blokov mesačného PnL).
PBO_BLOCKS = 16
#: Hranice brán SMERNICE V2 (krok 7 a 6, zadanie U9 / U8).
GATES = {"dsr_neff_min": 0.95, "dsr_n_min": 0.50, "pbo_max": 0.20, "pf_haircut_min": 1.10, "sortino_min": 1.0,
         "wf_pf_min": 1.15, "wfe_min": 0.5, "wf_positive_min": 0.75}
STATUS_TEXT = {"✅": "schválené (podpis používateľa)", "🟡": "brány prešli – demo, malá veľkosť",
               "⏳": "chýba meranie alebo slabý výsledok", "⚠": "legacy so zápornou správou", "❌": "hypotéza uzavretá"}


def blocks(timerange: str, n: int = PBO_BLOCKS) -> list[str]:
    """`YYYYMMDD-YYYYMMDD` rozdelené na `n` súvislých blokov po celých dňoch (posledný dostane zvyšok)."""
    a, b = (datetime.strptime(x, "%Y%m%d").replace(tzinfo=timezone.utc) for x in timerange.split("-"))
    days = (b - a).days
    if n < 2 or days < n:
        raise ValueError(f"obdobie {timerange} sa nedá rozdeliť na {n} blokov")
    out, start = [], a
    for i in range(n):
        end = b if i == n - 1 else a + timedelta(days=round(days * (i + 1) / n))
        out.append(f"{start:%Y%m%d}-{end:%Y%m%d}")
        start = end
    return out


def cscv(matrix: Sequence[Sequence[float]]) -> dict[str, Any]:
    """PBO z matice skúšky × bloky (vyššie = lepšie). Počet blokov párny, aspoň 4; skúšok aspoň 2.

    Vráti `pbo`, `logits` (λ každého delenia), `splits`, `trials`, `blocks`, `oos_median_rank` (medián relatívneho
    poradia víťaza v teste) a `degradation` (sklon OOS proti IS: záporný = čím lepšie v ladení, tým horšie v teste)."""
    import numpy as np

    m = np.asarray([list(map(float, r)) for r in matrix], dtype="float64")
    if m.ndim != 2 or m.shape[0] < 2 or m.shape[1] < 4 or m.shape[1] % 2:
        raise ValueError(f"CSCV chce aspoň 2 skúšky a párny počet blokov >= 4 (dostal {m.shape})")
    n, s = m.shape
    combos = np.array(list(itertools.combinations(range(s), s // 2)), dtype="int64")
    mask = np.zeros((s, len(combos)))
    mask[combos.T, np.arange(len(combos))] = 1.0
    is_perf = (m @ mask) / (s // 2)                       # skúšky × delenia
    oos_perf = (m @ (1.0 - mask)) / (s // 2)
    # víťaz ladenia: najvyššie IS, pri zhode nižší index
    best = np.argmax(is_perf, axis=0)
    cols = np.arange(len(combos))
    v = oos_perf[best, cols]
    below = (oos_perf < v).sum(axis=0)
    equal = (oos_perf == v).sum(axis=0)
    w = (below + (equal + 1) / 2) / (n + 1)
    lam = np.log(w / (1 - w))
    x, y = is_perf[best, cols], v
    var = float(((x - x.mean()) ** 2).sum())
    slope = float(((x - x.mean()) * (y - y.mean())).sum() / var) if var > 0 else 0.0
    return {"pbo": float((lam <= 0).mean()), "logits": lam.tolist(), "splits": int(len(combos)), "trials": int(n),
            "blocks": int(s), "oos_median_rank": float(np.sort(w)[len(w) // 2]), "degradation": slope}


def pbo_of_epochs(epochs: Iterable[Any], windows: Sequence[str], metric: str = "pnl_pct") -> dict[str, Any] | None:
    """PBO z epoch hyperoptu, ktorý mal za okná kritéria bloky obdobia (`blocks`). Metrika bloku je `metric`
    z `Epoch.windows[blok]`. Blok bez obchodov má 0, epocha bez výsledku v niektorom bloku sa vynechá."""
    matrix = []
    for e in epochs:
        per = getattr(e, "windows", None) if not isinstance(e, dict) else e.get("windows")
        if not per:
            continue
        row = []
        for w in windows:
            cell = per.get(w)
            if cell is None:
                break
            v = cell.get(metric)
            row.append(float(v) if v is not None else 0.0)
        else:
            matrix.append(row)
    if len(matrix) < 2:
        return None
    out = cscv(matrix)
    out.pop("logits")
    out["metric"] = metric
    return out


def month_blocks(months: Sequence[str], n: int = PBO_BLOCKS) -> list[list[str]]:
    """Zoradené mesiace `YYYY-MM` rozdelené na `n` súvislých blokov (prvé bloky dostanú zvyšok)."""
    ms = sorted(dict.fromkeys(months))
    if len(ms) < n:
        raise ValueError(f"{len(ms)} mesiacov sa nedá rozdeliť na {n} blokov")
    out, start = [], 0
    for i in range(n):
        size = len(ms) // n + (1 if i < len(ms) % n else 0)
        out.append(ms[start:start + size])
        start += size
    return out


def pbo_of_register(rows: Sequence[dict[str, Any]], n_blocks: int = PBO_BLOCKS) -> dict[str, Any] | None:
    """PBO hypotézy z registra (V2 U9): mesačný PnL všetkých konfigurácií (bez WF) v `n_blocks` blokoch.
    Mesiac, v ktorom konfigurácia nemá obchod, je 0. None, keď sú menej ako 2 konfigurácie s mesačným PnL."""
    from .register import config_id

    per: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.get("source") in ("wf", "legacy", "study") or not r.get("monthly"):
            continue
        per.setdefault(config_id(r), {m["month"]: float(m["pnl"]) for m in r["monthly"] if "month" in m})
    if len(per) < 2:
        return None
    months = sorted({m for v in per.values() for m in v})
    try:
        bl = month_blocks(months, n_blocks)
    except ValueError:
        return None
    matrix = [[sum(v.get(m, 0.0) for m in b) for b in bl] for v in per.values()]
    out = cscv(matrix)
    out.pop("logits")
    out.update(months=len(months), source="register")
    return out


def haircut_hl(sr_annual: float, n_days: int, tests: float, *, periods: int = 252) -> dict[str, Any]:
    """Harvey & Liu (2015), BHY: ohaircutovaný ročný Sharpe najlepšej z `tests` skúšok pri `n_days` denných
    pozorovaniach. `ratio` = SR_h / SR (0 = edge zmizol), `haircut` = 1 − ratio."""
    out: dict[str, Any] = {"sr": sr_annual, "n_days": int(n_days), "tests": float(tests)}
    if not (sr_annual > 0) or n_days < 2:
        out.update(sr_haircut=0.0 if sr_annual is not None and sr_annual <= 0 else None, ratio=0.0, haircut=1.0)
        return out
    nd = NormalDist()
    years = n_days / periods
    t = sr_annual * math.sqrt(years)
    p = 2 * (1 - nd.cdf(t))
    m = max(1.0, float(tests))
    mi = max(1, int(round(m)))
    c = sum(1.0 / i for i in range(1, mi + 1))
    p_adj = min(1.0, p * m * c)
    t_adj = nd.inv_cdf(1 - p_adj / 2) if p_adj < 1.0 else 0.0
    sr_h = max(0.0, t_adj / math.sqrt(years))
    ratio = sr_h / sr_annual
    out.update(t=t, p=p, p_bhy=p_adj, sr_haircut=sr_h, ratio=ratio, haircut=1 - ratio)
    return out


def pf_after_haircut(pf: float | None, ratio: float | None) -> float | None:
    """PF po haircute: edge nad 1 skrátený pomerom SR_h / SR. Pod 1 sa neuberá."""
    if pf is None or ratio is None or not math.isfinite(pf):
        return None
    return 1 + (pf - 1) * ratio if pf > 1 else pf


def pf_mc(pf: float | None, trades: int | None = None) -> float | None:
    """PF pre Monte Carlo a veľkosť pozície (krok 8b): 1 + (PF − 1) / 2, kým je obchodov < 300."""
    if pf is None or not math.isfinite(pf):
        return None
    if trades is not None and trades >= 300:
        return pf
    return 1 + (pf - 1) / 2 if pf > 1 else pf


def sortino(daily: Sequence[float], periods: int = 252) -> float | None:
    """Ročné Sortino z denného PnL (bez obchodu = 0, deň má byť v zozname): priemer / downside odchýlka × √252."""
    xs = [float(x) for x in daily]
    if len(xs) < 2:
        return None
    downside = math.sqrt(sum(min(0.0, x) ** 2 for x in xs) / len(xs))
    mean = sum(xs) / len(xs)
    if downside == 0:
        return math.inf if mean > 0 else None
    return mean / downside * math.sqrt(periods)


def gates(*, dsr_neff: float | None = None, dsr_n: float | None = None, pbo: float | None = None,
          walk_forward: dict[str, Any] | str | None = None, pf: float | None = None, haircut_ratio: float | None = None,
          sortino_oos: float | None = None, legacy: bool = False, limits: dict[str, float] | None = None) -> dict[str, Any]:
    """Brány z čísel, ktoré sú: `True` / `False`, `None` = nezmerané. `passed` len keď sú zmerané a prejdú všetky
    povinné. Pri legacy (a hypotéze zo štúdie) sú DSR, PBO a haircut len informácia (`info`), nie podmienka."""
    lim = {**GATES, **(limits or {})}
    pf_h = pf_after_haircut(pf, haircut_ratio)
    if isinstance(walk_forward, str):
        wf_ok: bool | None = walk_forward.upper().startswith("WALK-FORWARD DRZI") if walk_forward else None
    elif isinstance(walk_forward, dict):
        wf_ok = walk_forward.get("passed")
    else:
        wf_ok = None
    dsr_ok = None
    if dsr_neff is not None and dsr_n is not None:
        dsr_ok = dsr_neff >= lim["dsr_neff_min"] and dsr_n >= lim["dsr_n_min"]
    elif dsr_neff is not None and dsr_neff < lim["dsr_neff_min"]:
        dsr_ok = False
    out: dict[str, Any] = {
        "dsr": dsr_ok,
        "pbo": None if pbo is None else pbo <= lim["pbo_max"],
        "walk_forward": wf_ok,
        "haircut": None if pf_h is None else (pf_h >= lim["pf_haircut_min"] and (haircut_ratio or 0) > 0),
        "sortino": None if sortino_oos is None else sortino_oos >= lim["sortino_min"],
        "pf_live": pf_h, "legacy": legacy,
        "info": ["dsr", "pbo", "haircut"] if legacy else [],
    }
    povinne = [k for k in ("dsr", "pbo", "walk_forward", "haircut", "sortino") if k not in out["info"]]
    out["required"] = povinne
    out["missing"] = [k for k in povinne if out[k] is None]
    out["failed"] = [k for k in povinne if out[k] is False]
    out["passed"] = not out["missing"] and not out["failed"]
    return out


def status(g: dict[str, Any], *, vault: str | None = None, year_a_pf: float | None = None, signed: bool = False,
           negative: bool = False, from_study: bool = False) -> tuple[str, str]:
    """Stav (✅ 🟡 ⏳ ⚠ ❌) a dôvod. `vault` = výsledok trezoru 8b („✅“, „🟡“, „⏳“, „❌“ alebo None = neotvorený),
    `year_a_pf` = PF na roku A (len negatívna kontrola: < 1,0 → ❌), `signed` = podpis používateľa v registri."""
    if year_a_pf is not None and year_a_pf < 1.0:
        return "❌", f"rok A PF {year_a_pf:.2f} < 1,0"
    if vault == "❌":
        return "❌", "trezor neprešiel"
    hard = [k for k in g.get("failed") or [] if k in ("walk_forward", "dsr", "pbo", "sortino")]
    if hard:
        return "❌", "neprešlo: " + ", ".join(hard)
    if g.get("legacy"):
        return ("⚠", "legacy so zápornou správou") if negative else ("🟡" if g.get("passed") else "⏳",
                                                                     "legacy: DSR, PBO a haircut len informácia, najviac 🟡")
    if g.get("missing"):
        return "⏳", "chýba: " + ", ".join(g["missing"])
    if "haircut" in (g.get("failed") or []):
        return "⏳", "PF po haircute < 1,10"
    if vault in (None, "⏳") or from_study:
        return "🟡", "brány prešli; trezor " + ("neotvorený" if vault is None else "⏳") + (" (hypotéza zo štúdie)" if from_study else "")
    if vault == "🟡":
        return "🟡", "trezor 🟡"
    if vault == "✅" and signed:
        return "✅", "trezor ✅ a podpis používateľa"
    return "🟡", "trezor ✅, čaká na podpis používateľa"


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.overfit", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    bp = sub.add_parser("blocks", help="rozdeliť obdobie na bloky pre native_hyperopt --pbo")
    bp.add_argument("timerange")
    bp.add_argument("n", type=int, nargs="?", default=PBO_BLOCKS)
    pp = sub.add_parser("pbo", help="PBO hypotézy z mesačného PnL registra (16 blokov)")
    pp.add_argument("hypothesis")
    pp.add_argument("--blocks", type=int, default=PBO_BLOCKS)
    hp = sub.add_parser("haircut", help="Harvey–Liu haircut Sharpe a PF")
    hp.add_argument("--sr", type=float, required=True, help="ročný Sharpe")
    hp.add_argument("--days", type=int, required=True, help="počet denných pozorovaní")
    hp.add_argument("--tests", type=float, required=True, help="N_eff (s ekonomickým dôvodom ½ N_eff)")
    hp.add_argument("--pf", type=float)
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.cmd == "blocks":
        print(",".join(blocks(a.timerange, a.n)))
        return 0
    if a.cmd == "pbo":
        from .register import attempts

        r = pbo_of_register(attempts(a.hypothesis), a.blocks)
        if r is None:
            print(f"{a.hypothesis}: PBO sa nedá spočítať (menej ako 2 konfigurácie s mesačným PnL alebo málo mesiacov)")
            return 1
        print(f"{a.hypothesis}: PBO {r['pbo']:.3f} ({r['trials']} konfigurácií × {r['blocks']} blokov z {r['months']} mesiacov, "
              f"{r['splits']} delení) — hranica ≤ {GATES['pbo_max']:.2f}: {'prešlo' if r['pbo'] <= GATES['pbo_max'] else 'NEPREŠLO'}")
        return 0
    h = haircut_hl(a.sr, a.days, a.tests)
    print(f"SR {a.sr:.3f} pri {a.days} dňoch a {a.tests:g} skúškach -> po haircute {h['sr_haircut']:.3f} "
          f"(haircut {h['haircut'] * 100:.0f} %, p {h.get('p', float('nan')):.2e} -> BHY {h.get('p_bhy', float('nan')):.2e})"
          + (f"; PF {a.pf:.3f} -> {pf_after_haircut(a.pf, h['ratio']):.3f}" if a.pf is not None else ""))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
