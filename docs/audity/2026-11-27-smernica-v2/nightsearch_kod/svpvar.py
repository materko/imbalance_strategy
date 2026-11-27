import sys, json
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
from allcore import evaluate
V = [("dotyk + retest, limitka (default)", {}),
     ("len odmietnutie, limitka", {"tradeMode": "rejection"}),
     ("len retest po prerazení, limitka", {"tradeMode": "retest"}),
     ("dotyk + retest, IBS / pin bar", {"entryModel": "any"}),
     ("len odmietnutie, IBS / pin bar", {"tradeMode": "rejection", "entryModel": "any"}),
     ("len retest, IBS / pin bar", {"tradeMode": "retest", "entryModel": "any"}),
     ("vyvíjajúci sa POC, limitka", {"pocSource": "developing"}),
     ("cieľ na hrane value area", {"tpMode": "va_edge"})]
print("| variant | obch | WR | PF | zisk | maxDD | 24/25: obch | WR | PF | zisk |"); print("|---|---|---|---|---|---|---|---|---|---|")
for name, p in V:
    q = {"_strategy": "svp", **p}
    a = evaluate(q, 5, "20250904-20260904", "mnq_databento"); b = evaluate(q, 5, "20240904-20250904", "mnq_databento")
    print(f"| {name} | {a['trades']} | {a['winrate']:.1f} % | {a['profit_factor']:.2f} | {a['pnl_abs']:+.0f} | {a['max_drawdown_abs']:.0f} | "
          f"{b['trades']} | {b['winrate']:.1f} % | {b['profit_factor']:.2f} | {b['pnl_abs']:+.0f} |")
