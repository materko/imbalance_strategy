import json,sys
sys.path.insert(0,"/Users/martin/IBS/.nightsearch"); sys.path.insert(0,"/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tester.webapp.results import timerange_ms
K="mnq_databento"; inst=INSTRUMENTS[K]; m=A.m1(K)
def trades(cfg, tf, f, t):
    res,_=emulate(cfg,inst,m,tf,from_ms=f,to_ms=t,fee=0.0)
    return [(r["open_date"], r["is_short"], r["open_rate"], r["close_date"], r["close_rate"], r["exit_reason"]) for r in rows_from_trades(res.trades,inst,0.0,1.0)]
V={"VWAP stop":{"vwapStop":True},"VWAP cieľ (TP na cross)":{"vwapTp":True},"výstup zavretím za VWAP":{"exitMode":"vwap"},
   "TP alebo VWAP":{"exitMode":"tp_vwap"},"smer VWAP + prerazovacia sviečka":{"vwapRule":"direction","entryTiming":"break_candle"},
   "NY + Londýn, kotva seansa":{"sessionMode":"both","vwapAnchor":"session"},"VWAP z 5m":{"vwapPeriod":"chart"},
   "limitka + potvrdenie + filtre":{"entryOrderType":"limit","entryConfirm":"any","trendFilter":"with","trendTF":60,"volFilter":"high"}}
F,T=timerange_ms("20250904-20260904")
starts=["2025-11-03 00:00","2026-01-14 15:47","2026-04-15 14:13","2026-07-22 13:31","2026-03-09 03:20"]
for name,ov in V.items():
    p=dict(json.load(open("/Users/martin/IBS/tradebot/strategies/vwaporb/configs/mnq_databento_5m.json")),**ov)
    A.TMP.joinpath("v.json").write_text(json.dumps(p))
    try: cfg,_=load_profile(A.TMP/"v.json",engine="multicharts")
    except Exception as e: print(name, "CHYBA configu:", e); continue
    full=trades(cfg,5,F,T); bad=0; tot=0
    for s in starts:
        sm=int(pd.Timestamp(s,tz="UTC").value//10**6); part=trades(cfg,5,sm,T)
        cut=pd.Timestamp(s,tz="UTC")+pd.Timedelta(days=1)
        a=[x for x in full if pd.Timestamp(x[0])>=cut]; b=[x for x in part if pd.Timestamp(x[0])>=cut]; tot+=len(a)
        if a!=b:
            bad+=1; sa,sb=set(a),set(b); print("   ROZDIEL od",s,"| len v celom:",sorted(sa-sb)[:2],"| len v štarte:",sorted(sb-sa)[:2])
    print(f"{name}: obchodov {len(full)}, štartov s rozdielom {bad} z {len(starts)}, porovnaných {tot}", sorted(set(x[5] for x in full)))
