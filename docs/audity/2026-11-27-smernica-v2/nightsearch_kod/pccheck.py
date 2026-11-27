"""Craig Percoco 1.0 — kontrola na reálnych dátach: obchody (vstup = stred FVG, stop = low pohybu, cieľ 4R, okno),
kresby (štítok a boxy len pri skutočných obchodoch) a rovnaké obchody pri inom štarte (naživo vs história)."""
import json,sys
sys.path.insert(0,"/Users/martin/IBS/.nightsearch"); sys.path.insert(0,"/Users/martin/IBS")
import pandas as pd
import allcore as A
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.core.drawing import DrawRegistry
from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
from tester.webapp.results import timerange_ms
for K,prof,tr in (("btcusdt_binance","btcusdt_binance_1m.json","20260601-20260904"),("mnq_databento","mnq_databento_1m.json","20260601-20260904")):
    inst=INSTRUMENTS[K]; m=A.m1(K)
    cfg,_=load_profile(f"/Users/martin/IBS/tradebot/strategies/percoco/configs/{prof}",engine="multicharts")
    f,t=timerange_ms(tr)
    res,draws=emulate(cfg,inst,m,1,from_ms=f,to_ms=t,fee=0.0)
    rows=rows_from_trades(res.trades,inst,0.0,1.0); s,_=summarize(rows,10000.0,res,currency=inst.quote_currency)
    print(K, {k:s[k] for k in ("trades","winrate","pnl_abs","profit_factor","max_drawdown_abs")})
    bad=0
    for r in rows:
        risk=abs(r["open_rate"]-r["initial_stop_loss_abs"]); tp=abs(r["initial_take_profit_abs"]-r["open_rate"])
        ny=pd.Timestamp(r["open_date"]).tz_convert("America/New_York"); mm=ny.hour*60+ny.minute
        if abs(tp-4*risk)>2*inst.tick_size+1e-9 or not (570<=mm<=720) or ny.weekday()>=5: bad+=1; print("  ", r["open_date"], round(tp/risk,2), mm)
    print("   obchodov mimo pravidiel (4R, okno 9:30–12:00, pracovný deň):", bad, "| výstupy:", sorted(set(r["exit_reason"] for r in rows)))
    try:
        reg=DrawRegistry(); reg.extend(draws)
        objs=reg.objects(); lab=[o for o in objs if str(o.kind.value)=="pc_entry"]; tpb=[o for o in objs if str(o.kind.value)=="tp_box"]
        print("   kresby: štítkov vstupu", len(lab), "TP boxov", len(tpb), "obchodov", len(rows))
    except Exception as e: print("   kresby: neviem prečítať", type(draws), e)
    # iný štart (ako po reštarte)
    s2=int(pd.Timestamp("2026-07-15 14:07",tz="UTC").value//10**6)
    res2,_=emulate(cfg,inst,m,1,from_ms=s2,to_ms=t,fee=0.0)
    a=[(x["open_date"],x["open_rate"],x["close_date"]) for x in rows if pd.Timestamp(x["open_date"])>=pd.Timestamp("2026-07-16",tz="UTC")]
    b=[(x["open_date"],x["open_rate"],x["close_date"]) for x in rows_from_trades(res2.trades,inst,0.0,1.0) if pd.Timestamp(x["open_date"])>=pd.Timestamp("2026-07-16",tz="UTC")]
    print("   štart 15. 7. 14:07 UTC: rovnaké obchody od 16. 7.:", a==b, len(a), len(b))
