"""Doplní tretí a štvrtý rok (23/24, 22/23) najlepším dvojročným záznamom víkendového hľadania (pred prechodom na tri roky).
python wkbf.py — výstup wkbf_<stratégia>.jsonl"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import wksearch as W

TOP = 30
THR = [round(0.9 * rr, 3) for rr in W.RRS] + [2.3]


def job(a):
    key, d = a
    from allcore import evaluate
    try:
        if not d.get("rp2"):
            d["rp2"] = evaluate(W.enc(key, d["p"]), int(d["p"]["_tf"]), W.PREV2, d["inst"])
        r2 = d["rp2"]
        d["rp3"] = evaluate(W.enc(key, d["p"]), int(d["p"]["_tf"]), W.PREV3, d["inst"]) \
            if r2 and r2["pnl_abs"] > 0 and r2["trades"] >= 100 else None
    except Exception as e:
        d["rp3"] = None; d["err"] = str(e)[:200]
    return key, d


if __name__ == "__main__":
    jobs = []
    for key in W.KEYS:
        groups = {}
        for l in [*open(W.ROOT / ".nightsearch" / f"wk_{key}.jsonl"), *open(W.ROOT / ".nightsearch" / f"wkbf_{key}.jsonl")]:
            try:
                d = json.loads(l)
            except ValueError:
                continue
            r, rp = d["r"], d.get("rp")
            if not r or not rp or d.get("rp3") or r["trades"] < 150 or r["pnl_abs"] <= 0 or rp["pnl_abs"] <= 0 or rp["trades"] < 120:
                continue
            r2 = d.get("rp2")
            if r2 and (r2["pnl_abs"] <= 0 or r2["trades"] < 120):
                continue
            p = min(W.pay(r), W.pay(rp), *([W.pay(r2)] if r2 else []))
            for i in range(len(W.RRS)):
                if THR[i] <= p and W.pay(r) < THR[i + 1]:
                    groups.setdefault((d["inst"], i), []).append(d)
        for g in groups.values():
            g.sort(key=lambda d: (d.get("rp2") is None, -min(d["r"]["winrate"], d["rp"]["winrate"], (d.get("rp2") or d["rp"])["winrate"])))
            jobs += [(key, d) for d in g[:TOP]]
    print("na doplnenie:", len(jobs), flush=True)
    fh = {k: open(W.ROOT / ".nightsearch" / f"wkbf2_{k}.jsonl", "a") for k in W.KEYS}
    with ProcessPoolExecutor(int(os.environ.get("WK_WORKERS", "6"))) as ex:
        for i, (key, d) in enumerate(ex.map(job, jobs, chunksize=4)):
            fh[key].write(json.dumps(d) + "\n"); fh[key].flush()
            if i % 200 == 0:
                print(i, flush=True)
    print("hotovo")
