"""VWAP ORB: rovnaké obchody bez ohľadu na to, odkiaľ sa začne počítať (problém TradingView „po reštarte iné obchody").
Celý rok vs. štart v rôznych dňoch / uprostred seansy; porovnávajú sa obchody otvorené po štarte + 1 deň."""
import json,sys,glob,os
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
profs=["/Users/martin/IBS/tradebot/strategies/vwaporb/configs/"+x for x in os.listdir("/Users/martin/IBS/tradebot/strategies/vwaporb/configs")]
profs+=sorted(glob.glob("/Users/martin/IBS/tester/profiles/VWOP_*.json"))[:6]
F,T=timerange_ms("20250904-20260904")
starts=["2025-11-03 00:00","2026-01-14 15:47","2026-03-02 00:00","2026-04-15 14:13","2026-06-01 00:00","2026-07-22 13:31"]
for p in profs:
    cfg,_=load_profile(p,engine="multicharts")
    d=json.load(open(p)); tf=int(str(d.get("_timeframe","5m")).rstrip("m"))
    full=trades(cfg,tf,F,T); bad=0; tot=0
    for s in starts:
        sm=int(pd.Timestamp(s,tz="UTC").value//10**6)
        part=trades(cfg,tf,sm,T)
        cut=pd.Timestamp(s,tz="UTC")+pd.Timedelta(days=1)
        a=[x for x in full if pd.Timestamp(x[0])>=cut]; b=[x for x in part if pd.Timestamp(x[0])>=cut]
        tot+=len(a)
        if a!=b:
            bad+=1
            sa,sb=set(a),set(b); print("   ROZDIEL od", s, "| len v celom:", sorted(sa-sb)[:2], "| len v štarte:", sorted(sb-sa)[:2])
    print(os.path.basename(p), tf, "m | obchodov:", len(full), "| štartov s rozdielom:", bad, "z", len(starts), "| porovnaných obchodov:", tot)
