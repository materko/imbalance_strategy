import json, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
from search import work_tr
def main():
    C = json.load(open("final.json"))
    idx = [0, 1, 5, 6, 7, 10]
    ps = []
    for i in idx:
        p = dict(C[i]["p"]); p["enableEngulfingEntry"] = True; ps.append(p)
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(work_tr, [C[i]["strat"] for i in idx], ps, ["20250904-20260904"] * 6))
    for i, (_, _, r, e) in zip(idx, res):
        print(C[i]["strat"], C[i]["label"], r and (r["trades"], r["winrate"], r["profit_factor"]), e)
if __name__ == "__main__":
    main()
