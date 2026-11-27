import json, glob, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]

def ev(a):
    import io, contextlib
    from evalcore import evaluate
    p, tf, w = a
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        return evaluate(p, tf, w, fee="market")

if __name__ == "__main__":
    fs = sorted(glob.glob("/Users/martin/IBS/tester/profiles/LQW_*.json"))
    jobs = []
    for f in fs:
        p = json.load(open(f)); tf = int(p["_timeframe"][:-1])
        jobs += [(p, tf, w) for w in W]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(ev, jobs))
    out = {}
    for i, f in enumerate(fs):
        ws = res[i * 5:(i + 1) * 5]; n = f.split("/")[-1][:-5]
        out[n] = {"pnl": [round(w["pnl_abs"]) for w in ws], "sum": round(sum(w["pnl_abs"] for w in ws)),
                  "pos": sum(1 for w in ws if w["pnl_abs"] > 0)}
        print(n, out[n])
    json.dump(out, open("/Users/martin/IBS/.nightsearch/lqw_costs.json", "w"))
