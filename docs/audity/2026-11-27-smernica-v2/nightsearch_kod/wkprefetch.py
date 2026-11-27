"""Paralelný prepočet úloh zo zberu wkfinal.py (wkfinal_jobs.json) do wkfinal_cache.json."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = "/Users/martin/IBS/.nightsearch"
DUMMY = {"trades": 0, "wins": 0, "winrate": 0.0, "pnl_abs": 0.0, "profit_factor": 0.0, "max_drawdown_abs": 0.0, "payoff_r": 0.0}


def job(a):
    from allcore import evaluate
    k, (p, tf, tr, inst) = a
    try:
        return k, evaluate(p, tf, tr, inst)
    except Exception:
        return k, dict(DUMMY)


if __name__ == "__main__":
    jobs = json.load(open(f"{ROOT}/wkfinal_jobs.json"))
    cf = f"{ROOT}/wkfinal_cache.json"
    cache = json.load(open(cf)) if os.path.exists(cf) else {}
    todo = [(k, v) for k, v in jobs.items() if k not in cache]
    print("prepočet:", len(todo), flush=True)
    with ProcessPoolExecutor(int(os.environ.get("WK_WORKERS", "9"))) as ex:
        for i, (k, r) in enumerate(ex.map(job, todo, chunksize=2)):
            cache[k] = r
            if i % 100 == 0:
                json.dump(cache, open(cf, "w")); print(i, flush=True)
    json.dump(cache, open(cf, "w")); print("hotovo", len(cache))
