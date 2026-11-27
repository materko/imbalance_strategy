import json, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]

def ev(args):
    from evalcore import evaluate
    import io, contextlib
    p, w = args
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        return evaluate({k: v for k, v in p.items() if k != "_tf"}, int(p["_tf"]), w, fee="market")

def main():
    rs = [json.loads(l) for l in open("/Users/martin/IBS/.nightsearch/div2.jsonl")]
    ok = [d for d in rs if d["r"] and d["r"].get("prev") and d["r"]["pnl_abs"] > 0 and d["r"]["prev"]["pnl_abs"] > 0]
    picks, seen = [], set()
    def add(lst, n):
        for d in lst:
            k = json.dumps(d["p"], sort_keys=True)
            if k in seen: continue
            sig = (d["r"]["trades"], round(d["r"]["pnl_abs"]))
            if any(sig == (x["r"]["trades"], round(x["r"]["pnl_abs"])) for x in picks): continue
            seen.add(k); picks.append(d); n -= 1
            if n == 0: return
    add(sorted(ok, key=lambda d: -min(d["r"]["pnl_abs"], d["r"]["prev"]["pnl_abs"])), 8)               # najvyssi zisk v horsom z 2 rokov
    add(sorted([d for d in ok if d["r"]["trades"] >= 100], key=lambda d: -(d["r"]["profit_factor"] + d["r"]["prev"]["profit_factor"])), 6)  # najvyssi PF
    add(sorted([d for d in ok if d["r"]["trades"] >= 80], key=lambda d: -(d["r"]["winrate"] + d["r"]["prev"]["winrate"])), 6)              # najvyssi WR
    add(sorted([d for d in ok if d["r"]["trades"] >= 100], key=lambda d: d["r"]["max_drawdown_pct"] + d["r"]["prev"]["max_drawdown_pct"]), 4)  # najnizsi DD
    jobs = [(p["p"], w) for p in picks for w in W]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(ev, jobs))
    for i, p in enumerate(picks):
        p["win"] = dict(zip(W, res[i * 5:(i + 1) * 5]))
    json.dump(picks, open("/Users/martin/IBS/.nightsearch/divverified.json", "w"))
    for p in picks:
        ws = [p["win"][w] for w in W]
        print(p["p"]["_tf"], [(w["trades"], w["winrate"], w["profit_factor"], round(w["pnl_abs"])) for w in ws])

if __name__ == "__main__":
    main()
