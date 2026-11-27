"""VWAP ORB naživo: pre vzorku obchodov sa dáta utnú tesne po vstupe (ako naživo — budúce sviečky neexistujú)
a overí sa, že vstup vznikne v tom istom čase, na tej istej cene, s tým istým stopom a cieľom."""
import json,sys,random
sys.path.insert(0,"/Users/martin/IBS/.nightsearch"); sys.path.insert(0,"/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tester.webapp.results import timerange_ms
K="mnq_databento"; inst=INSTRUMENTS[K]; m=A.m1(K)
def rows(cfg,tf,f,t):
    res,_=emulate(cfg,inst,m,tf,from_ms=f,to_ms=t,fee=0.0); return rows_from_trades(res.trades,inst,0.0,1.0)
F,T=timerange_ms("20250904-20260904")
for name,ov in {"východiskový":{},"VWAP stop":{"vwapStop":True},"NY + Londýn":{"sessionMode":"both","vwapAnchor":"session"},
                "smer + prerazovacia":{"vwapRule":"direction","entryTiming":"break_candle"}}.items():
    p=dict(json.load(open("/Users/martin/IBS/tradebot/strategies/vwaporb/configs/mnq_databento_5m.json")),**ov)
    A.TMP.joinpath("l.json").write_text(json.dumps(p)); cfg,_=load_profile(A.TMP/"l.json",engine="multicharts")
    full=rows(cfg,5,F,T); random.seed(1); sample=random.sample(full,min(15,len(full))); bad=0
    for r in sample:
        od=pd.Timestamp(r["open_date"]); f=int((od-pd.Timedelta(days=3)).value//10**6); t=int((od+pd.Timedelta(minutes=1)).value//10**6)
        got=[x for x in rows(cfg,5,f,t) if x["open_date"]==r["open_date"]]
        ok=got and got[0]["open_rate"]==r["open_rate"] and got[0]["initial_stop_loss_abs"]==r["initial_stop_loss_abs"] \
            and got[0].get("initial_take_profit_abs")==r.get("initial_take_profit_abs") and got[0]["is_short"]==r["is_short"]
        if not ok: bad+=1; print("   NESEDÍ", r["open_date"], r["open_rate"], got[:1] and (got[0]["open_rate"], got[0]["initial_stop_loss_abs"]))
    print(f"{name}: {len(sample)} obchodov skontrolovaných s dátami utnutými po vstupe, nesedí {bad}")
