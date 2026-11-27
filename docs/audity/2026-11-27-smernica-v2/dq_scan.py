"""Ľahká kontrola kvality 1m archívu (len čítanie). nice -n 19, po jednom súbore.
Výstup: kritika/data_kvalita.json. Spustenie: nice -n 19 .venv/bin/python -I .nightsearch/kritika/dq_scan.py"""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/Users/martin/IBS/data/archive/tester")
OUT = Path("/Users/martin/IBS/.nightsearch/kritika/data_kvalita.json")
# jadro seansy v UTC (minúty od polnoci), vnútri seansy v lete aj v zime
WIN = {"us_idx": (14 * 60 + 30, 20 * 60), "fx": (8 * 60, 16 * 60), "dax": (8 * 60 + 30, 15 * 60),
       "jp": (0 * 60 + 30, 5 * 60 + 30), "energy": (14 * 60, 18 * 60), "softs": (14 * 60, 17 * 60),
       "stock": (14 * 60 + 30, 20 * 60), "crypto": (0, 24 * 60)}
def kind(name):
    n = name.upper()
    if any(s in n for s in ("BTC", "ETH")): return "crypto"
    if any(s in n for s in ("ES_", "MNQ", "MYM", "US500", "NAS100", "DJ30")): return "us_idx"
    if n.startswith("DAX"): return "dax"
    if n.startswith("JP225"): return "jp"
    if any(s in n for s in ("WTI", "NGAS")): return "energy"
    if any(s in n for s in ("COCOA", "COFFEE")): return "softs"
    if "/IBKR/" in n: return "stock"
    return "fx"   # FX, XAU, MGC, 6E

files = sorted(p for p in ROOT.rglob("*.feather") if re.search(r"-1m(-futures)?\.\d{4}\.feather$", p.name))
res = {}
prev_close = {}
for i, p in enumerate(files):
    inst = str(p.parent.relative_to(ROOT)) + "/" + re.sub(r"\.\d{4}\.feather$", "", p.name)
    year = int(p.name.split(".")[-2])
    k = kind(str(p))
    try:
        x = pd.read_feather(p, columns=["date", "open", "high", "low", "close", "volume"])
    except Exception as e:
        res.setdefault(inst, {})[year] = {"err": str(e)[:200]}; continue
    t = pd.to_datetime(x["date"], utc=True)
    o, h, l, c, v = (x[col].to_numpy(float) for col in ("open", "high", "low", "close", "volume"))
    d = {"bars": int(len(x)), "first": str(t.iloc[0])[:16] if len(x) else None, "last": str(t.iloc[-1])[:16] if len(x) else None}
    d["dups"] = int(t.duplicated().sum()); d["unsorted"] = int((t.diff().dt.total_seconds() < 0).sum())
    d["nan"] = int(np.isnan(c).sum()); d["nonpos"] = int((c <= 0).sum())
    d["ohlc_bad"] = int(((h < np.maximum(o, c) - 1e-9) | (l > np.minimum(o, c) + 1e-9) | (h < l)).sum())
    d["vol0_pct"] = round(float((v <= 0).mean() * 100), 2) if len(v) else None
    r = np.diff(np.log(c)); ar = np.abs(r); med = np.median(ar[ar > 0]) if (ar > 0).any() else 0
    big = (ar > max(25 * med, 0.003)) if med else np.zeros_like(ar, bool)
    d["spikes"] = int(big.sum())
    rev = big[:-1] & big[1:] & (np.sign(r[:-1]) != np.sign(r[1:]))
    d["bad_ticks"] = int(rev.sum())   # skok a hneď späť = zlý tik
    rng = (h - l) / c; mr = np.median(rng[rng > 0]) if (rng > 0).any() else 0
    d["bigrange"] = int((rng > max(40 * mr, 0.005)).sum()) if mr else 0
    # pokrytie jadra seansy
    a, b = WIN[k]; mins = t.dt.hour * 60 + t.dt.minute
    wd = t.dt.weekday
    inwin = (mins >= a) & (mins < b) & ((wd < 5) if k != "crypto" else True)
    days = t[inwin].dt.date
    nd = days.nunique()
    exp = nd * (b - a)
    d["sess_days"] = int(nd)
    d["sess_cov_pct"] = round(float(inwin.sum()) / exp * 100, 1) if exp else 0.0
    # pracovné dni bez dát v jadre (sviatky v tom)
    if len(x):
        allwd = pd.bdate_range(t.iloc[0].normalize(), t.iloc[-1].normalize()) if k != "crypto" else \
            pd.date_range(t.iloc[0].normalize(), t.iloc[-1].normalize())
        d["days_missing"] = int(len(allwd) - nd)
        per_day = inwin.groupby(t.dt.date).sum()
        d["short_days"] = int((per_day[per_day > 0] < 0.5 * (b - a)).sum())
    gaps = t.diff().dt.total_seconds() / 3600
    g = gaps[(gaps > 2) & inwin]
    d["gaps_in_sess_gt2h"] = int(len(g))
    pc = prev_close.get(inst)
    if pc and len(c):
        d["year_join_jump_pct"] = round(abs(o[0] / pc - 1) * 100, 2)
    if len(c): prev_close[inst] = c[-1]
    res.setdefault(inst, {})[year] = d
    del x
    print(i + 1, len(files), inst, year, d["sess_cov_pct"], d["bad_ticks"], flush=True, file=sys.stderr)

# rolovanie Databento: skok close pred / open po dni rolovania
for rp in (ROOT / "databento/futures").glob("*.rolls.json"):
    inst = "databento/futures/" + rp.name.replace(".rolls.json", "")
    rolls = json.loads(rp.read_text()); jumps = []
    for rr in rolls[1:]:
        y = int(rr["date"][:4]); f = ROOT / f"{inst}.{y}.feather"
        if not f.exists(): continue
        x = pd.read_feather(f, columns=["date", "open", "close"]); t = pd.to_datetime(x["date"], utc=True)
        dt = pd.Timestamp(rr["date"], tz="UTC")
        before = x[t < dt]; after = x[t >= dt]
        if len(before) and len(after):
            jumps.append(round(abs(after["open"].iloc[0] / before["close"].iloc[-1] - 1) * 100, 3))
    res.setdefault(inst, {})["rolls"] = {"n": len(jumps), "med_pct": float(np.median(jumps)) if jumps else None,
                                          "max_pct": max(jumps) if jumps else None}
OUT.write_text(json.dumps(res, indent=1, default=str))
print("OK", OUT, file=sys.stderr)
