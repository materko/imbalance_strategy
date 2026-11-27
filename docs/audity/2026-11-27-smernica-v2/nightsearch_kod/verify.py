"""Overenie kandidatov na piatich referencnych oknach."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
from search import work_tr

WIN = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904"]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30

def main():
    rs = [json.loads(l) for l in open("/Users/martin/IBS/.nightsearch/results.jsonl")]
    rs = [d for d in rs if d["r"]]
    cands = []
    for s in ["ibszones", "ibsentry"]:
        seen = set()
        pool = sorted([d for d in rs if d["strat"] == s and d["r"]["winrate"] >= 80], key=lambda d: -d["r"]["trades"])
        pool += sorted([d for d in rs if d["strat"] == s and d["r"]["winrate"] >= 82], key=lambda d: -d["r"]["trades"])[:10]
        for d in pool:
            k = json.dumps(d["p"], sort_keys=True)
            if k in seen:
                continue
            seen.add(k); cands.append(d)
            if len(seen) >= N:
                break
    jobs = [(i, w) for i in range(len(cands)) for w in WIN]
    with ProcessPoolExecutor(9) as ex:
        res = list(ex.map(work_tr, [cands[i]["strat"] for i, w in jobs], [cands[i]["p"] for i, w in jobs], [w for i, w in jobs]))
    out = []
    for c in cands:
        c["win"] = {"20250904-20260904": c["r"]}
    for (i, w), (_, _, r, err) in zip(jobs, res):
        cands[i]["win"][w] = r
    json.dump(cands, open("/Users/martin/IBS/.nightsearch/verified.json", "w"))
    print("hotovo", len(cands))

if __name__ == "__main__":
    main()
