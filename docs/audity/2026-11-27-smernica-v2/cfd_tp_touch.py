"""19_B: TP/SL dotknuté bid sviečkou bez výstupu (minúty pred minútou výstupu). Len MT5, body 0.01."""
import json, sqlite3, collections as C
c = sqlite3.connect("file:/Users/martin/IBS/tester/live/mirror.sqlite?mode=ro", uri=True)
inst = {i: (p, a, s) for i, p, a, s in c.execute("select id,platform,account,symbol from instances")}
m1, orders, fills = {}, C.defaultdict(list), {}
for iid, kind, t, b in c.execute("select instance,kind,t,body from events where kind in ('m1','order','fill') and instance like 'mt5%' and instance not like '%_ibsnet'"):
    p, a, s = inst[iid]; d = json.loads(b)
    if kind == "m1": m1.setdefault((a, s), {}).setdefault(d["bt"], (d["h"], d["l"]))
    elif kind == "order" and d.get("ready") and d["a"] == "entry": orders[(iid, d["id"])].append((t, d["p"]))
    elif kind == "fill" and d.get("ready"): fills.setdefault((iid, d["id"], d["side"]), d)
res = C.defaultdict(list)
for (iid, oid, side), d in fills.items():
    if side != "in" or (iid, oid, "out") not in fills or not orders.get((iid, oid)): continue
    p = [q for t, q in orders[(iid, oid)] if t <= d["t"] + 1000][-1]
    x = fills[(iid, oid, "out")]; a, s = inst[iid][1:]
    b0, b1 = (d["ft"] // 60000 + 1) * 60000, x["ft"] // 60000 * 60000
    tpen = slpen = -1e9; b = b0
    while b < b1:
        if b in m1.get((a, s), {}):
            h, l = m1[(a, s)][b]
            tpen = max(tpen, (h - p["tp"]) if p["dir"] == 1 else (p["tp"] - l))
            slpen = max(slpen, (p["sl"] - l) if p["dir"] == 1 else (h - p["sl"]))
        b += 60000
    if tpen > -1e9:
        res[(s, "TP_L" if p["dir"] == 1 else "TP_S")].append(round(tpen * 100))
        res[(s, "SL_L" if p["dir"] == 1 else "SL_S")].append(round(slpen * 100))
for k in sorted(res):
    v = sorted(res[k]); print(k, "n=", len(v), "dotyk>=0 bez vystupu:", [x for x in v if x >= 0], "najblizsie pod:", v[-3:])
