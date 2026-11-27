"""Skríning stratégií na BTCUSDT.P (Binance futures) — predvolený profil stratégie, parametre v tickoch prepočítané
podľa pomeru volatility BTC / trh profilu (medián rozsahu 5m sviečky v cene), 5 referenčných okien naraz
(20211001-20260904), poplatok podľa inštrumentu (taker 0,05 %). Výsledky btc_screen/vysledky.json."""
import json, subprocess, sys, time, glob
from pathlib import Path
import pandas as pd
ROOT=Path("/Users/martin/IBS"); OUT=ROOT/".nightsearch/btc_screen"; OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
from tradebot.strategies import STRATEGIES
from tradebot.core.types import INSTRUMENTS
PY=str(ROOT/".venv/bin/python"); RES=OUT/"vysledky.json"
YRS=[("21/22","2021-10-01","2022-10-01"),("22/23","2022-10-01","2023-10-01"),("23/24","2023-10-01","2024-09-04"),("24/25","2024-09-04","2025-09-04"),("25/26","2025-09-04","2026-09-04")]
A=ROOT/"data/archive/tester"
SRCF={"mnq_databento":"databento/futures/MNQ_USD-1m","es_databento":"databento/futures/ES_USD-1m","mgc_databento":"databento/futures/MGC_USD-1m",
      "mym_databento":"databento/futures/MYM_USD-1m","btcusdt_binance":"binance/futures/BTC_USDT_USDT-1m-futures"}
_rng={}
def rng5(inst):
    if inst not in _rng:
        p=SRCF.get(inst)
        if not p: return None
        df=pd.concat([pd.read_feather(f) for f in sorted(glob.glob(str(A/p)+".202[1-6].feather"))])
        df["date"]=pd.to_datetime(df["date"],utc=True); b=df.set_index("date").resample("5min").agg({"high":"max","low":"min"}).dropna()
        _rng[inst]=float((b.high-b.low).median())
    return _rng[inst]
SKIP=("net","neteod")
keys=sorted(k for k,s in STRATEGIES.items() if (not getattr(s,"logic_of",None) or s.logic_of==k) and not k.endswith(SKIP))
done=json.loads(RES.read_text()) if RES.exists() else {}
dst=INSTRUMENTS["btcusdt_binance"]
for k in keys:
    if k in done: continue
    s=STRATEGIES[k]; pf=Path(s.profile_dir)/f"{s.default_profile}.json"
    try: d=json.loads(pf.read_text())
    except Exception as e: done[k]={"err":f"profil: {e}"}; continue
    src=d.get("_instrument") or "mnq_databento"; tf=d.get("_timeframe") or "5m"
    if tf=="1m": tf="3m"
    si=INSTRUMENTS.get(src); r_src=rng5(src); r_btc=rng5("btcusdt_binance")
    K=(r_btc/r_src) if r_src else 1.0
    mult=(si.tick_size/dst.tick_size)*K if si else K
    size=set(getattr(s.config_cls,"SIZE_FIELDS",{}) or {})
    for x,v in list(d.items()):
        if isinstance(v,dict) and v.get("unit") in ("ticks",): d[x]={**v,"value":v["value"]*mult}
        elif isinstance(v,dict) and v.get("unit")=="abs" and x not in size: d[x]={**v,"value":v["value"]*K}
        elif isinstance(v,(int,float)) and not isinstance(v,bool) and x.lower().endswith("ticks") and x not in size: d[x]=type(v)(round(v*mult,6))
    if "tickDollarValue" in d: d["tickDollarValue"]=dst.tick_size*dst.point_value
    d["_instrument"]="btcusdt_binance"; d["_timeframe"]=tf; d["_title"]=f"BTC skríning — {k} (predvolený profil, ×{K:.1f})"
    p=OUT/f"{k}.json"; p.write_text(json.dumps(d,ensure_ascii=False,indent=1))
    t0=time.time()
    r=subprocess.run([PY,"-m","tester.webapp.cli","run","--strategy",k,"--profile",str(p),"--pair","BTC/USDT:USDT","--exchange","tester",
                      "--engine","multicharts","--timeframe",tf,"--timerange","20211001-20260904","--wallet","60000",
                      "--note",f"BTC skríning: {k} predvolený profil prepočítaný na BTC (×{K:.1f})"],cwd=ROOT,capture_output=True,text=True)
    line=[l for l in r.stdout.splitlines() if "obchodov" in l and l[:8].isdigit()]
    if not line:
        done[k]={"err":(r.stdout+r.stderr)[-300:],"tf":tf}; print(k,"CHYBA",flush=True)
    else:
        rid=line[-1].split()[0]; tr=json.load(open(ROOT/"tester/runs"/rid/"trades.json"))
        Y={}
        for n,a,b in YRS:
            pp=[t["profit_abs"] for t in tr if a<=t["close_date"][:10]<b]; gw=sum(x for x in pp if x>0); gl=-sum(x for x in pp if x<0)
            Y[n]={"n":len(pp),"pf":round(gw/gl,2) if gl else None,"wr":round(100*sum(x>0 for x in pp)/len(pp),1) if pp else None,"pnl":round(sum(pp))}
        done[k]={"run":rid,"tf":tf,"src":src,"K":round(K,2),"summary":line[-1],"years":Y}
        print(k,round(time.time()-t0),"s",line[-1][40:160],flush=True)
    RES.write_text(json.dumps(done,ensure_ascii=False,indent=1))
print("hotovo",time.strftime("%H:%M"),flush=True)
