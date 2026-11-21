"""Event study: pokračuje trend po červených správach (FOMC, CPI, NFP)? MNQ / ES / MGC 1m, 2021–2026.

Pre každú udalosť v čase T (New York):
  prvý pohyb   = close(T+k) − open(T)               (k = 5, 15, 30 min)
  pokračovanie = close(T+k+h) − close(T+k) v smere prvého pohybu (h = 30, 60, 120 min, do 15:55)
Kontrola: tie isté časy v pracovné dni bez CPI / NFP / FOMC.
Výstup: podiel pokračovaní, priemer v ATR dňa, t-štatistika; aj len pre veľký prvý pohyb (horná polovica).
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/martin/document/IBS")
from tester import engines  # noqa: E402
from tradebot.core.types import INSTRUMENTS  # noqa: E402

NY = ZoneInfo("America/New_York")
CAL = json.load(open("/Users/martin/document/IBS/tester/calendar_us.json"))["events"]
KS = (5, 15, 30)
HS = (30, 60, 120, "close")


def load(inst_key: str) -> pd.Series:
    df = pd.read_feather(engines.one_minute_file(INSTRUMENTS[inst_key]))
    tcol = "date" if "date" in df.columns else df.columns[0]
    df = df[df[tcol] >= "2020-12-01"]
    idx = pd.to_datetime(df[tcol], utc=True).dt.tz_convert(NY)
    return pd.DataFrame({"o": df["open"].values, "h": df["high"].values, "l": df["low"].values,
                         "c": df["close"].values}, index=idx.values).tz_localize(None).set_axis(
        pd.DatetimeIndex(idx.dt.tz_localize(None)))


def daily_atr(df: pd.DataFrame) -> pd.Series:
    d = df.resample("1D").agg({"h": "max", "l": "min", "c": "last"}).dropna()
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().shift(1)   # ATR známy pred dňom


def price_at(df: pd.DataFrame, ts: datetime, col: str) -> float | None:
    """Prvý 1m bar s časom ≥ ts (do 3 min), inak None."""
    i = df.index.searchsorted(ts)
    if i >= len(df) or df.index[i] - ts > timedelta(minutes=3):
        return None
    return float(df[col].iloc[i])


def close_at(df, ts):
    """Close posledného baru, ktorý začal pred ts (stav ceny v čase ts)."""
    i = df.index.searchsorted(ts) - 1
    if i < 0 or ts - df.index[i] > timedelta(minutes=3):
        return None
    return float(df["c"].iloc[i])


def study(df: pd.DataFrame, atr: pd.Series, when: list[datetime]) -> dict:
    out = defaultdict(list)
    for t in when:
        a = atr.get(pd.Timestamp(t.date()))
        o = price_at(df, t, "o")
        if a is None or not a or math.isnan(a) or o is None:
            continue
        for k in KS:
            c1 = close_at(df, t + timedelta(minutes=k))
            if c1 is None:
                continue
            first = (c1 - o) / a
            if first == 0:
                continue
            sgn = 1 if first > 0 else -1
            for h in HS:
                end = (datetime.combine(t.date(), datetime.min.time()) + timedelta(hours=15, minutes=55)
                       if h == "close" else t + timedelta(minutes=k + h))
                if end <= t + timedelta(minutes=k):
                    continue
                c2 = close_at(df, end)
                if c2 is None:
                    continue
                out[(k, h)].append((abs(first), sgn * (c2 - c1) / a))
    res = {}
    for key, v in out.items():
        arr = np.array(v)
        cont = arr[:, 1]
        big = arr[arr[:, 0] >= np.median(arr[:, 0])][:, 1]
        def st(x):
            n = len(x)
            m = x.mean()
            sd = x.std(ddof=1) if n > 1 else 0
            return {"n": n, "p_cont": float((x > 0).mean()), "mean_atr": float(m),
                    "t": float(m / (sd / math.sqrt(n))) if sd > 0 else 0.0}
        res[key] = {"all": st(cont), "big": st(big)}
    return res


def event_times(names) -> list[datetime]:
    out = []
    for n in names:
        hh, mm = map(int, CAL[n]["time_et"].split(":"))
        for d in CAL[n]["dates"]:
            out.append(datetime.combine(date.fromisoformat(d), datetime.min.time()) + timedelta(hours=hh, minutes=mm))
    return sorted(out)


def control_times(hhmm: str, exclude: set) -> list[datetime]:
    hh, mm = map(int, hhmm.split(":"))
    out = []
    d = date(2021, 1, 4)
    while d <= date(2026, 9, 30):
        if d.weekday() < 5 and d not in exclude:
            out.append(datetime.combine(d, datetime.min.time()) + timedelta(hours=hh, minutes=mm))
        d += timedelta(days=1)
    return out


def main():
    ev_days = {date.fromisoformat(x) for n in CAL for x in CAL[n]["dates"]}
    groups = {"CPI+NFP 8:30": event_times(["CPI", "NFP"]), "FOMC 14:00": event_times(["FOMC"]),
              "kontrola 8:30": control_times("08:30", ev_days), "kontrola 14:00": control_times("14:00", ev_days)}
    rows = []
    for inst in ("mnq_databento", "es_databento", "mgc_databento"):
        df = load(inst)
        atr = daily_atr(df)
        for g, when in groups.items():
            r = study(df, atr, when)
            for (k, h), v in sorted(r.items(), key=lambda x: (x[0][0], str(x[0][1]))):
                rows.append({"trh": inst.split("_")[0].upper(), "skupina": g, "k": k, "h": h,
                             **{f"{s}_{m}": v[s][m] for s in ("all", "big") for m in ("n", "p_cont", "mean_atr", "t")}})
        print("hotovo", inst, flush=True)
    out = pd.DataFrame(rows)
    out.to_csv("/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/news_study.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
