import json, glob, re
rows = {}
for p in sorted(glob.glob("/Users/martin/document/IBS/tester/runs/20261029-*/run.json")):
    d = json.load(open(p)); n = d.get("note", "")
    m = re.match(r"SPRAVY RRR: pravidlo (\d) (\w+) (\S+), .* (\d{8}-\d{8})$", n)
    if not m or d.get("status") != "done": continue
    rows[(m[1] + " " + m[2], m[3], m[4])] = d["result"]
W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
for rule in sorted({k[0] for k in rows}):
    print(f"\n{rule}")
    for v in ["rr0_stopdnes", "rr2_stopdnes", "rr1.5_stopza", "rr2_stopza", "rr3_stopza"]:
        rs = [rows.get((rule, v, w)) for w in W]
        if None in rs: print(" ", v, "chýba"); continue
        g = sum(r["pnl_abs"] for r in rs); n = sum(r["trades"] for r in rs); pos = sum(r["pnl_abs"] > 0 for r in rs)
        pfs = " · ".join(f"{r['profit_factor']:.2f}" for r in rs); last = rs[-1]
        print(f"  {v:13} PF {pfs} | okien+ {pos}/5 obch {n:3} zisk {g:+7.0f} $ maxDD {max(r['max_drawdown_abs'] for r in rs):5.0f} | posl. rok PF {last['profit_factor']:.2f} {last['pnl_abs']:+.0f} $")
