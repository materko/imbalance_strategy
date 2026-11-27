import json,sys
sys.path.insert(0,"/Users/martin/IBS/.nightsearch"); sys.path.insert(0,"/Users/martin/IBS")
import allcore as A, wksearch as W
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
FEE=1.755e-05; K="mnq_databento"; inst=INSTRUMENTS[K]; m=A.m1(K)
def ev(key,p,tr):
    A.TMP.joinpath("f.json").write_text(json.dumps(dict(W.enc(key,p),_instrument=K))); cfg,_=load_profile(A.TMP/"f.json",engine="multicharts")
    f,t=timerange_ms(tr); res,_=emulate(cfg,inst,m,int(p["_tf"]),from_ms=f,to_ms=t,fee=FEE)
    rows=rows_from_trades(res.trades,inst,FEE,1.0); s,_=summarize(rows,60000.0,res,currency="USD")
    return f"{s['trades']} obch, WR {s['winrate']:.1f} %, PF {s['profit_factor']:.2f}, {s['pnl_abs']:+.0f} $"
def find(key,cond):
    for l in open(f"wk_{key}.jsonl"):
        d=json.loads(l)
        if d["r"] and cond(d): return d["p"]
C=[("SPX sila A (WR 81 %)","mag7",lambda d:d["p"]["_tf"]==5 and d["p"].get("entryEnd")==90 and d["p"].get("rr")==0.5 and d["r"]["trades"]==166),
   ("SPX sila B (PF 1,74)","mag7",lambda d:d["p"]["_tf"]==10 and d["r"]["trades"]==164 and abs(d["r"]["pnl_abs"]-8500)<1),
   ("DAILY OPEN A (WR 68 %)","dailyopen",lambda d:d["r"]["trades"]==158 and abs(d["r"]["winrate"]-67.72)<0.1),
   ("DAILY OPEN B (PF 2,22)","dailyopen",lambda d:d["r"]["trades"]==186 and abs(d["r"]["profit_factor"]-2.22)<0.01),
   ("DAILY OPEN C (331 obch)","dailyopen",lambda d:d["r"]["trades"]==331)]
for name,key,cond in C:
    p=find(key,cond)
    if p is None: print(name,"nenájdené"); continue
    print(f"{name}: posledný rok s poplatkom: {ev(key,p,'20250904-20260904')} | 2021–9/2025 s poplatkom: {ev(key,p,'20211001-20250904')}")
