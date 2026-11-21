"""SPRÁVY na EUR/USD (6E): ako sa 6E správa okolo správ ECB a USA — trend alebo návrat (21. 11. 2026, Mac mini).

Pre každú udalosť T: noha close(T+a) → close(T+b) (a = 0 = open baru T), pokračovanie close(T+b) → close(T+b+h) v smere nohy.
Kladné p = trend pokračuje, záporné = návrat (fade). Kontrola: tie isté časy v dňoch bez správ (rovnaké typy dní).
Udalosti: USA z kalendára SPRÁV (tradebot/strategies/spravy/calendar.json, 2021+), ECB z ecb.europa.eu (2016+, čas
Frankfurt: rozhodnutie 13:45 alebo 14:15 — ktorý, určí najväčší pohyb minúty).
"""
from __future__ import annotations

import glob, json, math, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

NY, FR = ZoneInfo("America/New_York"), ZoneInfo("Europe/Berlin")
FEE = 1.755e-05
ROOT = "/Users/martin/IBS"


def load():
    fs = sorted(glob.glob(f"{ROOT}/data/archive/tester/databento/futures/6E_USD-1m.*.feather"))
    df = pd.concat([pd.read_feather(f) for f in fs])
    c = [x for x in df.columns if "date" in x.lower()][0]
    df = df.rename(columns={c: "t"}).set_index("t").sort_index()
    df = df[~df.index.duplicated()]
    return df[df.index >= "2016-01-01"]


def ecb_dates():
    raw = open(f"{ROOT}/.nightsearch/spravyeur/ecb_raw.txt").read().splitlines()[0].split("|")
    return sorted(datetime.strptime(x.strip(), "%d %B %Y").date() for x in raw)


def us_events():
    cal = json.load(open(f"{ROOT}/tradebot/strategies/spravy/calendar.json"))["events"]
    out = []
    for typ, v in cal.items():
        hh, mm = map(int, v["time_et"].split(":"))
        for d in v["dates"]:
            y, m, dd = map(int, d.split("-"))
            out.append((typ, datetime(y, m, dd, hh, mm, tzinfo=NY).astimezone(ZoneInfo("UTC"))))
    return out


def px(df, t, col="close"):
    t = pd.Timestamp(t).tz_convert("UTC") if pd.Timestamp(t).tzinfo else pd.Timestamp(t, tz="UTC")
    i = df.index.searchsorted(t)
    if i >= len(df) or abs((df.index[i] - t).total_seconds()) > 120:
        return None
    return float(df[col].iloc[i])


def ecb_events(df):
    """Rozhodnutie ECB a tlačovka v čase Frankfurt: do 9. 6. 2022 13:45 / 14:30, od 21. 7. 2022 14:15 / 14:45
    (zmena overená na 6E — najväčší pohyb minúty sa presunul práve vtedy)."""
    out = []
    for d in ecb_dates():
        new = d >= datetime(2022, 7, 21).date()
        for typ, (hh, mm) in (("ECB", (14, 15) if new else (13, 45)), ("ECB_TK", (14, 45) if new else (14, 30))):
            out.append((typ, datetime(d.year, d.month, d.day, hh, mm, tzinfo=FR).astimezone(ZoneInfo("UTC")), f"{hh}:{mm:02d}"))
    return out


def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l else float("inf")


def run(df, atr, when, a, b, h, min_atr=0.0):
    rows = []
    for t in when:
        p0 = px(df, t, "open") if a == 0 else px(df, t + timedelta(minutes=a))
        p1, p2 = px(df, t + timedelta(minutes=b)), px(df, t + timedelta(minutes=b + h))
        at = atr.get(pd.Timestamp(t.date()))
        if None in (p0, p1, p2) or p1 == p0 or at is None or at != at or abs(p1 - p0) < min_atr * at:
            continue
        s = 1 if p1 > p0 else -1
        rows.append((t.year, s * (p2 - p1) - FEE * (p1 + p2)))
    return pd.DataFrame(rows, columns=["y", "p"])


def stat(r):
    if len(r) < 12:
        return None
    x = r.p.values
    sd = x.std(ddof=1)
    yr = r.groupby("y").p.apply(pf)
    tr = r.groupby("y").p.apply(lambda v: pf(-v))
    return dict(n=len(r), cont=100 * (x > 0).mean(), pf_trend=pf(r.p), pf_fade=pf(-r.p),
                t=x.mean() / (sd / math.sqrt(len(x))) if sd else 0, yrs_trend=f"{int((yr > 1).sum())}/{len(yr)}",
                yrs_fade=f"{int((tr > 1).sum())}/{len(tr)}")


def main():
    df = load()
    d1 = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    tr = pd.concat([d1.high - d1.low, (d1.high - d1.close.shift()).abs(), (d1.low - d1.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().shift(1)
    atr.index = atr.index.tz_localize(None) if atr.index.tz else atr.index
    ecb = ecb_events(df)
    groups = {"ECB": [x[1] for x in ecb if x[0] == "ECB"], "ECB_TK": [x[1] for x in ecb if x[0] == "ECB_TK"]}
    for typ, t in us_events():
        if t < datetime(2021, 1, 1, tzinfo=ZoneInfo("UTC")) or pd.Timestamp(t) > df.index[-1]:
            continue
        groups.setdefault(typ, []).append(t)
    groups["USA 8:30 (CPI NFP PCE GDP PPI RETAIL)"] = sorted(sum((groups.get(k, []) for k in ("CPI", "NFP", "PCE", "GDP", "PPI", "RETAIL")), []))
    ev_days = {t.date() for v in groups.values() for t in v}
    rows = []
    for g, when in groups.items():
        when = sorted(set(when))
        # kontrola: rovnaký čas dňa (NY) v pracovných dňoch bez správ
        ctrl = []
        for t in when[:1]:
            tny = t.astimezone(FR if g.startswith("ECB") else NY)
            for d in pd.bdate_range("2016-01-01" if g.startswith("ECB") else "2021-01-01", df.index[-1].date()):
                if d.date() in ev_days:
                    continue
                ctrl.append(datetime(d.year, d.month, d.day, tny.hour, tny.minute, tzinfo=tny.tzinfo).astimezone(ZoneInfo("UTC")))
        for a, b in ((0, 5), (0, 15), (0, 30), (0, 60), (15, 60)):
            for h in (30, 60, 120, 240):
                for mn in (0.0, 0.15, 0.3):
                    s = stat(run(df, atr, when, a, b, h, mn))
                    if not s:
                        continue
                    c = stat(run(df, atr, ctrl[::3], a, b, h, mn)) if ctrl else None
                    rows.append(dict(správa=g, noha=f"{a}→{b}", h=h, min_atr=mn, **s,
                                     ctrl_cont=round(c["cont"], 1) if c else None, ctrl_t=round(c["t"], 2) if c else None))
    out = pd.DataFrame(rows)
    out.to_csv(f"{ROOT}/.nightsearch/spravyeur/study.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
    best = out[(out.n >= 30)].assign(at=lambda x: x.t.abs()).sort_values("at", ascending=False)
    print(best.head(60).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
