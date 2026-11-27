import sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
from allcore import evaluate
F = {"useFibo": True}
V = [("bez fibo (default)", {}),
     ("fibo 38,2–78,6 %", F),
     ("fibo 50–78,6 %", {**F, "fibMinPct": 50}),
     ("fibo 61,8–78,6 %", {**F, "fibMinPct": 61.8}),
     ("fibo 38,2–61,8 %", {**F, "fibMaxPct": 61.8}),
     ("fibo, len retest", {**F, "tradeMode": "retest"}),
     ("fibo, len dotyk", {**F, "tradeMode": "rejection"}),
     ("fibo, IBS / pin bar", {**F, "entryModel": "any"}),
     ("fibo, stop za nohu, cieľ extenzia 27 %", {**F, "slMode": "leg", "tpMode": "extension"}),
     ("fibo, stop 1,5 ATR, cieľ extenzia 27 %", {**F, "tpMode": "extension"})]
print("| variant | obch | WR | PF | zisk | maxDD | 24/25: obch | WR | PF | zisk |"); print("|---|---|---|---|---|---|---|---|---|---|")
for name, p in V:
    q = {"_strategy": "svp", **p}
    a = evaluate(q, 5, "20250904-20260904", "mnq_databento"); b = evaluate(q, 5, "20240904-20250904", "mnq_databento")
    print(f"| {name} | {a['trades']} | {a['winrate']:.1f} % | {a['profit_factor']:.2f} | {a['pnl_abs']:+.0f} | {a['max_drawdown_abs']:.0f} | "
          f"{b['trades']} | {b['winrate']:.1f} % | {b['profit_factor']:.2f} | {b['pnl_abs']:+.0f} |")
