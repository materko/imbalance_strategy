"""Obchod proti prvému pohybu po CPI / NFP (a pre porovnanie FOMC): po rokoch, s poplatkom.

Vstup: close baru T+k (k min po správe) PROTI smeru pohybu open(T) → close(T+k); výstup close T+k+h.
Voliteľne stop za extrémom prvého pohybu (high/low T..T+k). PnL v bodoch a v $ (1 kontrakt), poplatok smernice.
"""

from __future__ import annotations

import sys
from datetime import timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad")
sys.path.insert(0, "/Users/martin/document/IBS")
from news_study import close_at, event_times, load, price_at  # noqa: E402
from tradebot.core.types import INSTRUMENTS  # noqa: E402

FEE = 1.755e-05


def sim(df, inst, when, k, h, use_stop, direction=-1):
    rows = []
    for t in when:
        o = price_at(df, t, "o")
        c1 = close_at(df, t + timedelta(minutes=k))
        if o is None or c1 is None or c1 == o:
            continue
        first = 1 if c1 > o else -1
        side = direction * first                         # −1 = proti prvému pohybu
        seg = df.loc[t: t + timedelta(minutes=k - 1)]
        ext = seg.h.max() if first > 0 else seg.l.min()  # extrém prvého pohybu
        stop = ext if use_stop and side == -first else None
        path = df.loc[t + timedelta(minutes=k): t + timedelta(minutes=k + h - 1)]
        if path.empty:
            continue
        exit_px = float(path.c.iloc[-1])
        reason = "čas"
        if stop is not None:
            hit = path[(path.h >= stop)] if side < 0 else path[(path.l <= stop)]
            if not hit.empty:
                exit_px, reason = stop, "stop"
        pts = side * (exit_px - c1)
        fee_pts = FEE * (c1 + exit_px)
        rows.append({"t": t, "year": t.year, "pts": pts - fee_pts, "reason": reason,
                     "usd": (pts - fee_pts) * inst.point_value / inst.tick_size * inst.tick_size})
    return pd.DataFrame(rows)


def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l else float("inf")


def main():
    cfgs = [("CPI+NFP", ["CPI", "NFP"], 15, 60), ("CPI+NFP", ["CPI", "NFP"], 15, 120),
            ("CPI+NFP", ["CPI", "NFP"], 30, 60), ("FOMC", ["FOMC"], 15, 60)]
    for key in ("mnq_databento", "es_databento"):
        inst = INSTRUMENTS[key]
        df = load(key)
        for name, ev, k, h in cfgs:
            for use_stop in (False, True):
                r = sim(df, inst, event_times(ev), k, h, use_stop)
                if r.empty:
                    continue
                by = r.groupby("year").pts.agg(lambda x: pf(x)).round(2).to_dict()
                n_by = r.groupby("year").size().to_dict()
                print(f"{key[:3].upper()} {name} k={k} h={h} stop={'áno' if use_stop else 'nie'}: n={len(r)} "
                      f"WR {100*(r.pts>0).mean():.0f} % PF {pf(r.pts):.2f} spolu {r.pts.sum():+.0f} bodov | "
                      + " ".join(f"{y}:{by[y]}({n_by[y]})" for y in sorted(by)))


if __name__ == "__main__":
    main()
