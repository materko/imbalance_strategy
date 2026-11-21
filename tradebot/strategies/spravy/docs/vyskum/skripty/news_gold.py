"""Zlato (MGC) po červených správach USA: rozbehne sa trend a pokračuje?

Pre každú udalosť T: smer nohy close(T+a) → close(T+b) (a = 0 znamená open baru T), pokračovanie
close(T+b) → close(T+b+h) v tom smere. Pri udalostiach v ten istý čas sa udalosť priradí najsilnejšej správe
(poradie PRIORITA). Výsledok: n, pokračuje %, PF (po poplatku), t-štatistika, rokov s PF > 1.
"""

from __future__ import annotations

import math
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
from news_events import events  # noqa: E402
from news_study import close_at, daily_atr, load, price_at  # noqa: E402

FEE = 1.755e-05
PRIORITA = ["FOMC", "CPI", "NFP", "PCE", "GDP", "PPI", "RETAIL", "ISM_M", "ISM_S", "JOLTS", "FOMC_MIN", "CLAIMS"]
LEGS = [(0, 15), (0, 30), (0, 60), (15, 60)]
HS = [60, 120, 240]


def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l else float("inf")


def assign() -> dict[str, list]:
    ev = events()
    taken: dict = {}
    for name in PRIORITA:
        for t in ev[name]:
            taken.setdefault(t, name)
    out: dict[str, list] = {n: [] for n in PRIORITA}
    for t, n in taken.items():
        out[n].append(t)
    return out


def run(df, atr, when, a, b, h, min_atr=0.0):
    rows = []
    for t in when:
        p0 = price_at(df, t, "o") if a == 0 else close_at(df, t + timedelta(minutes=a))
        p1 = close_at(df, t + timedelta(minutes=b))
        p2 = close_at(df, t + timedelta(minutes=b + h))
        at = atr.get(pd.Timestamp(t.date()))
        if None in (p0, p1, p2) or p1 == p0 or at is None or at != at:
            continue
        if abs(p1 - p0) < min_atr * at:
            continue
        s = 1 if p1 > p0 else -1
        rows.append((t.year, s * (p2 - p1) - FEE * (p1 + p2), abs(p1 - p0) / at))
    return pd.DataFrame(rows, columns=["y", "p", "leg"])


def stat(r):
    if len(r) < 12:
        return None
    x = r.p.values
    sd = x.std(ddof=1)
    yr = r.groupby("y").p.apply(pf)
    return {"n": len(r), "cont": 100 * (x > 0).mean(), "pf": pf(r.p), "t": x.mean() / (sd / math.sqrt(len(x))) if sd else 0,
            "yrs": f"{int((yr > 1).sum())}/{len(yr)}"}


def main():
    df = load("mgc_databento")
    atr = daily_atr(df)
    groups = assign()
    groups["VŠETKY 8:30 (bez claims)"] = sorted(groups["CPI"] + groups["NFP"] + groups["PCE"] + groups["GDP"]
                                               + groups["PPI"] + groups["RETAIL"])
    groups["VŠETKY 10:00"] = sorted(groups["ISM_M"] + groups["ISM_S"] + groups["JOLTS"])
    rows = []
    for g, when in groups.items():
        for a, b in LEGS:
            for h in HS:
                for mn in (0.0, 0.25):
                    s = stat(run(df, atr, when, a, b, h, mn))
                    if s:
                        rows.append({"správa": g, "noha": f"{a}→{b}", "h": h, "min_ATR": mn, **s})
    out = pd.DataFrame(rows)
    out.to_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/news_gold.csv", index=False)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 500)
    summ = out.groupby("správa").agg(variant=("pf", "size"), medián_PF=("pf", "median"),
                                    podiel_PF_nad_1=("pf", lambda x: (x > 1).mean()),
                                    medián_t=("t", "median"), n=("n", "max")).sort_values("medián_PF", ascending=False)
    print(summ.round(2).to_string())
    print()
    best = out[(out.t.abs() >= 2)].sort_values("t", ascending=False)
    print(best.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
