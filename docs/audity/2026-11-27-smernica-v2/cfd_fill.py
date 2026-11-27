"""19_B: meranie fillov EA/NT zo zrkadla proti m1 brokera (bid). Len čítanie.
Spúšťať: .venv/bin/python -I .nightsearch/kritika/cfd_fill.py > .nightsearch/kritika/cfd_fill_out.txt
"""
import collections as C
import json
import sqlite3
import statistics as S
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

DB = "/Users/martin/IBS/tester/live/mirror.sqlite"
CAL = "/Users/martin/IBS/tester/calendar_us.json"
NY = ZoneInfo("America/New_York")
PT = {"US100.cash": 0.01, "US500.cash": 0.01, "XAUUSD": 0.01, "EURUSD": 0.00001,
      "MNQ": 0.25, "MES": 0.25, "MGC": 0.1, "MNQ 12-26": 0.25}

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
inst = {}
for i, plat, acc, sym, tf in c.execute("select id,platform,account,symbol,tf from instances"):
    inst[i] = (plat, acc, sym.split(" ")[0] if plat == "ninjatrader" else sym, tf)

news = []
for k, b in json.load(open(CAL))["events"].items():
    hh, mm = map(int, (b.get("time_et") or "08:30").split(":"))
    for d in b.get("dates", []):
        y, m, dd = map(int, d.split("-"))
        news.append(datetime(y, m, dd, hh, mm, tzinfo=NY).timestamp() * 1000)


def window(ms):
    if any(abs(ms - n) <= 5 * 60000 for n in news):
        return "news"
    t = datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(NY)
    mins = t.hour * 60 + t.minute
    return "nyopen" if 570 <= mins < 580 else "normal"


m1 = {}            # (acc,sym) -> {bt: (o,h,l,c)}
orders = C.defaultdict(list)   # (inst,id) -> [(t,body)]
cancels = C.defaultdict(list)
fills = {}
for iid, kind, t, body in c.execute(
        "select instance,kind,t,body from events where kind in ('m1','order','fill')"):
    plat, acc, sym, tf = inst[iid]
    d = json.loads(body)
    if kind == "m1":
        m1.setdefault((acc, sym), {}).setdefault(d["bt"], (d["o"], d["h"], d["l"], d["c"]))
    elif kind == "order" and d.get("ready"):
        (orders if d["a"] == "entry" else cancels)[(iid, d["id"])].append((t, d))
    elif kind == "fill" and d.get("ready"):
        fills[(iid, d["id"], d["side"], d["ft"])] = d

out = C.defaultdict(list)       # (plat,sym,kind,win) -> [adverse slip in points]
spr = C.defaultdict(list)       # (sym,win) -> fill - m1 open for buy market fills in first 3 s of minute
sellchk = C.Counter()
lat = C.defaultdict(list)
pos = {}
rows = []
for (iid, oid, side, ft), d in sorted(fills.items(), key=lambda x: x[0][3]):
    plat, acc, sym, tf = inst[iid]
    if iid.endswith("_ibsnet"):
        continue   # stare skusky s trailingom a MNQ profilom na EURUSD / US100 1m
    pt = PT.get(sym, 0.01)
    ent = [o for t, o in orders.get((iid, oid), []) if t <= d["t"] + 1000]
    if not ent:
        continue
    t_ord = max(t for t, o in orders[(iid, oid)] if t <= d["t"] + 1000)
    o = ent[-1]
    p, dr = o["p"], o["p"]["dir"]
    px = d["price"]
    bar = m1.get((acc, sym), {}).get(ft // 60000 * 60000)
    w = window(ft)
    if side == "in":
        kind = "limit_in" if o["ot"] == "Limit" else ("stop_in" if o["ot"] == "Stop" else "market_in")
        out[(plat, sym, kind + ("_L" if dr == 1 else "_S"), w)].append((px - p["e"]) * dr / pt)
        rows.append((iid[-14:], oid, kind, dr, w, p["e"], px, bar))
        if kind == "market_in":
            lat[(plat, sym, "bar->order")].append(t_ord - (o["bt"] + tf * 60000))
            lat[(plat, sym, "order->fill")].append(ft - t_ord)
            if bar:
                out[(plat, sym, "market_in_vs_m1open", w)].append((px - bar[0]) * dr / pt)
        pos[(iid, oid)] = (p, dr, ft, acc, sym)
        buy = dr == 1
    else:
        ex = d["exit"]
        if ex in ("sltp", "Stop loss", "Profit target"):
            if ex == "sltp":
                ex = "Stop loss" if abs(px - p["sl"]) < abs(px - p["tp"]) else "Profit target"
            lvl = p["sl"] if ex == "Stop loss" else p["tp"]
            out[(plat, sym, ("SL" if ex == "Stop loss" else "TP") + ("_L" if dr == 1 else "_S"), w)].append((lvl - px) * dr / pt)
            rows.append((iid[-14:], oid, ex, dr, w, lvl, px, bar))
        buy = dr == -1
    if plat == "mt5" and bar:
        o_, h, l, cl = bar
        if buy:
            if ft % 60000 < 3000:
                spr[(sym, w)].append((px - o_) / pt)
            sellchk[(sym, "buy_above_high")] += px > h + 1e-9
            sellchk[(sym, "buy_n")] += 1
        else:
            sellchk[(sym, "sell_outside")] += not (l - 1e-9 <= px <= h + 1e-9)
            sellchk[(sym, "sell_n")] += 1
            if ft % 60000 < 3000:
                spr[(sym + "_SELLkontrola", w)].append((px - o_) / pt)

# dotyk limitu bez fillu (len live limit vstupy)
touch = C.defaultdict(list)
filled_ids = {(k[0], k[1]) for k in fills if k[2] == "in"}
for (iid, oid), lst in orders.items():
    plat, acc, sym, tf = inst[iid]
    t0, o = lst[-1]
    if o["ot"] != "Limit":
        continue
    pt = PT.get(sym, 0.01)
    f = [k[3] for k in fills if k[0] == iid and k[1] == oid and k[2] == "in"]
    cl = [t for t, _ in cancels.get((iid, oid), []) if t >= t0]
    end = min(f) if f else (min(cl) if cl else None)
    if end is None:
        continue
    bars = m1.get((acc, sym), {})
    b0 = (t0 // 60000 + 1) * 60000
    pen = []
    b = b0
    while b + 60000 <= end + (60000 if f else 0) and b < b0 + 3 * 86400000:
        if b in bars:
            _, h, l, _ = bars[b]
            pen.append((o["p"]["e"] - l) / pt if o["p"]["dir"] == 1 else (h - o["p"]["e"]) / pt)
        b += 60000
    if pen:
        touch[(plat, sym, o["p"]["dir"], bool(f))].append(max(pen))


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def fmt(v):
    return f"n={len(v)} med={S.median(v):.1f} p25={q(v,.25):.1f} p75={q(v,.75):.1f} p90={q(v,.9):.1f} min={min(v):.1f} max={max(v):.1f}"


print("== sklz (kladne = horsie, v bodoch brokera 0.01; NT v tickoch) ==")
for k in sorted(out):
    pt = PT.get(k[1], 0.01)
    v = out[k] if k[0] == "mt5" else [x * pt / PT[k[1]] for x in out[k]]
    print(k, fmt(v))
print("== spread odhad: buy fill - m1 bid open (fill do 3 s od zaciatku minuty) ==")
for k in sorted(spr):
    print(k, fmt(spr[k]))
print("== konzistencia m1 = bid ==")
for k in sorted(sellchk):
    print(k, sellchk[k])
print("== latencia ms ==")
for k in sorted(lat):
    print(k, fmt(lat[k]))
print("== limit vstup: max prienik bid sviecky za limit pocas zivota (body) ==")
for k in sorted(touch):
    v = touch[k]
    print(k, fmt(v), "dotkol sa (>=0):", sum(x >= 0 for x in v))

print("== detail ==")
for r in rows:
    print(r)
