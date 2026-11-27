"""Krok 1 smernice — naživo = história pre ľubovoľnú stratégiu a profil (emulátor MultiCharts, s poplatkom).
python livecheck.py <stratégia> <profil.json> [TF min] [inštrument]
1a: štarty v rôznych dňoch aj uprostred seansy → obchody v prekryve rovnaké (a od koľkých dní rozbehu);
1b: dáta utnuté hneď po vstupe (50 obchodov) → ten istý vstup; 1c: utnutie uprostred vyššieho TF (45 min pred vstupom)
→ rozhodnutia pred utnutím rovnaké."""
import json, sys, random
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tester.webapp.results import timerange_ms
FEE = 1.755e-05
key, prof = sys.argv[1], sys.argv[2]
d = json.load(open(prof))
tf = int(sys.argv[3]) if len(sys.argv) > 3 else int(str(d.get("_timeframe", "5m")).rstrip("m"))
K = sys.argv[4] if len(sys.argv) > 4 else d.get("_instrument", "mnq_databento")
inst = INSTRUMENTS[K]; m = A.m1(K)
p = dict(d); p["_strategy"] = key; p["_instrument"] = K
A.TMP.joinpath("lc.json").write_text(json.dumps(p)); cfg, _ = load_profile(A.TMP / "lc.json", engine="multicharts")
F, T = timerange_ms("20250904-20260904")
def run(f, t):
    res, _ = emulate(cfg, inst, m, tf, from_ms=f, to_ms=t, fee=FEE)
    return rows_from_trades(res.trades, inst, FEE, 1.0)
def sig(r, full=True):
    base = (r["open_date"], bool(r["is_short"]), r["open_rate"], r["initial_stop_loss_abs"], r.get("initial_take_profit_abs"))
    return base + ((r["close_date"], r["close_rate"], r["exit_reason"]) if full else ())
full = run(F, T); print(f"{key} {prof.split('/')[-1]} {tf}m: celý rok {len(full)} obchodov")
ms = lambda s: int(pd.Timestamp(s, tz="America/New_York").tz_convert("UTC").value // 10**6)
starts = ["2025-11-03 00:00", "2025-12-15 00:00", "2026-01-12 09:00", "2026-02-20 09:00", "2026-04-15 11:00", "2026-06-17 11:37"]
bad1a, warm = 0, 0
for s in starts:
    part = run(ms(s), T)
    A_ = [sig(r) for r in full if r["open_date"] >= pd.Timestamp(s, tz="America/New_York").tz_convert("UTC").isoformat()]
    B_ = [sig(r) for r in part]
    # od koľkých dní rozbehu sú zhodné
    for dd in range(0, 31):
        cut = (pd.Timestamp(s, tz="America/New_York") + pd.Timedelta(days=dd)).tz_convert("UTC").isoformat()
        a = [x for x in A_ if x[0] >= cut]; b = [x for x in B_ if x[0] >= cut]
        if a == b:
            warm = max(warm, dd); break
    else:
        bad1a += 1; sa, sb = set(A_), set(B_)
        print("   1a ROZDIEL od", s, "len v celom:", sorted(sa - sb)[:2], "len v štarte:", sorted(sb - sa)[:2])
print(f"1a štarty: {len(starts) - bad1a}/{len(starts)} zhodné, rozbeh najviac {warm} dní")
random.seed(3); sample = random.sample(full, min(50, len(full))); bad1b = 0
for r in sample:
    od = pd.Timestamp(r["open_date"])
    got = [x for x in run(int((od - pd.Timedelta(days=max(12, warm + 10))).value // 10**6), int((od + pd.Timedelta(minutes=1)).value // 10**6))
           if x["open_date"] == r["open_date"]]
    if not got or sig(got[0], False) != sig(r, False):
        bad1b += 1; print("   1b NESEDÍ", r["open_date"], sig(r, False)[1:], got and sig(got[0], False)[1:])
print(f"1b utnutie po vstupe: {len(sample) - bad1b}/{len(sample)} zhodné")
bad1c = 0; sample2 = sample[:20]
for r in sample2:
    od = pd.Timestamp(r["open_date"]); cut = od - pd.Timedelta(minutes=45)
    f = int((od - pd.Timedelta(days=max(12, warm + 10))).value // 10**6)
    a = [sig(x, False) for x in run(f, int((od + pd.Timedelta(minutes=1)).value // 10**6)) if pd.Timestamp(x["open_date"]) < cut]
    b = [sig(x, False) for x in run(f, int(cut.value // 10**6))]
    if a != b:
        bad1c += 1; print("   1c NESEDÍ pred", cut, set(a) ^ set(b))
print(f"1c utnutie uprostred vyššieho TF: {len(sample2) - bad1c}/{len(sample2)} zhodné")
print("VÝSLEDOK KROKU 1:", "PREŠIEL" if not (bad1a or bad1b or bad1c) else "NEPREŠIEL")
