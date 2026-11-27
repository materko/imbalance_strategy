import json, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
from search import work_tr

def main():
    W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
    def load(fn):
        return [d for d in (json.loads(l) for l in open(fn)) if d["r"]]
    r1, r2 = load("results.jsonl"), load("results2.jsonl")
    C = []
    def pick(label, s, pool, key):
        f = [d for d in pool if d["strat"] == s]
        f = [d for d in f if key(d)]
        if not f: return
        b = max(f, key=lambda d: (d["r"]["trades"], d["r"]["winrate"]))
        sig = (s, b["r"]["trades"], b["r"]["winrate"], b["r"]["pnl_abs"])
        if any(c["sig"] == sig for c in C): return
        C.append({"label": label, "strat": s, "p": b["p"], "sig": sig})
    pv = lambda d: d["r"].get("prev") and d["r"]["prev"]["winrate"] >= 75
    for s in ["ibszones", "ibsentry"]:
        pick("A max obchodov (WR>=80 posl. rok)", s, r1 + r2, lambda d: d["r"]["winrate"] >= 80)
        pick("B stabilny (80 %, predch. rok >=75 %)", s, r2, lambda d: d["r"]["winrate"] >= 80 and pv(d))
        for lo in (81, 82, 83, 85):
            pick(f"C WR>={lo} % stabilny", s, r2, lambda d, lo=lo: d["r"]["winrate"] >= lo and pv(d))
        f = [d for d in r2 if d["strat"] == s and d["r"]["winrate"] >= 80 and d["r"]["trades"] >= 180 and d["r"].get("prev")]
        if f:
            b = max(f, key=lambda d: d["r"]["prev"]["winrate"])
            C.append({"label": "D najstabilnejsi (max WR predch. roka)", "strat": s, "p": b["p"], "sig": None})
    jobs = [(i, w) for i in range(len(C)) for w in W]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(work_tr, [C[i]["strat"] for i, _ in jobs], [C[i]["p"] for i, _ in jobs], [w for _, w in jobs]))
    for c in C: c["win"] = {}
    for (i, w), (_, _, r, e) in zip(jobs, res):
        C[i]["win"][w] = r
    json.dump(C, open("final.json", "w"))
    for c in C:
        print(c["strat"], c["label"], [(c["win"][w] or {}).get("trades") for w in W], [(c["win"][w] or {}).get("winrate") for w in W])

if __name__ == "__main__":
    main()
