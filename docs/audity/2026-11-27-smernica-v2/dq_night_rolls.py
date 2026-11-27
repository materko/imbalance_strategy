"""Nočné pokrytie a prepínanie kontraktov (len čítanie). nice -n 19, po jednom súbore. Výstup kritika/data_noc_roly.json"""
import json, collections
from pathlib import Path
import pandas as pd
R = Path("/Users/martin/IBS/data/archive/tester/databento/futures")
NIGHT = {"MNQ": (23*60, 13*60), "MYM": (23*60, 13*60), "ES": (23*60, 13*60), "MGC": (0, 7*60), "6E": (0, 7*60)}
out = {}
for sym, (a, b) in NIGHT.items():
    yrs = {}
    for f in sorted(R.glob(f"{sym}_USD-1m.*.feather")):
        y = int(f.name.split(".")[-2]); t = pd.to_datetime(pd.read_feather(f, columns=["date"])["date"], utc=True)
        m = t.dt.hour * 60 + t.dt.minute; wd = t.dt.weekday
        if a > b:   # cez polnoc: večer (po–št) + ráno (ut–pi) ; dĺžka
            inw = ((m >= a) & (wd <= 3)) | ((m < b) & (wd >= 1) & (wd <= 4)); L = (24*60 - a) + b
            key = (t - pd.Timedelta(minutes=b)).dt.date
        else:
            inw = (m >= a) & (m < b) & (wd <= 4); L = b - a; key = t.dt.date
        n = key[inw].nunique()
        yrs[y] = round(inw.sum() / (n * L) * 100, 1) if n else 0.0
    best = max(yrs.values())
    rolls = json.loads((R / f"{sym}_USD-1m.rolls.json").read_text())
    per = collections.Counter(r["date"][:4] for r in rolls)
    seen, back = set(), []
    for r in rolls:
        if r["contract"] in seen: back.append(r)
        seen.add(r["contract"])
    out[sym] = {"night_cov": yrs, "night_rel_to_best": {y: round(v / best * 100, 1) for y, v in yrs.items()},
                "rolls_per_year": dict(sorted(per.items())), "back_and_forth": back}
Path("/Users/martin/IBS/.nightsearch/kritika/data_noc_roly.json").write_text(json.dumps(out, indent=1))
for s, v in out.items():
    print(s, "noc rel:", v["night_rel_to_best"]); print("   roly/rok:", v["rolls_per_year"], "tam-späť:", len(v["back_and_forth"]), v["back_and_forth"][:3])
