import pandas as pd, glob, json, numpy as np
B="/Users/martin/IBS/data/archive/tester"
SER={"mnq_databento":(f"{B}/databento/futures/MNQ_USD-1m","2019-05-05","2022-09-30"),
"es_databento":(f"{B}/databento/futures/ES_USD-1m","2015-01-01","2025-09-03"),
"mym_databento":(f"{B}/databento/futures/MYM_USD-1m","2019-06-02","2022-09-30"),
"mgc_databento":(f"{B}/databento/futures/MGC_USD-1m","2023-01-01","2025-09-03"),
"6e_databento":(f"{B}/databento/futures/6E_USD-1m","2016-01-03","2021-09-30"),
"btcusdt_binance":(f"{B}/binance/futures/BTC_USDT_USDT-1m-futures","2019-09-08","2022-09-30"),
"nas100_dukascopy":(f"{B}/dukascopy/futures/NAS100_USD-1m","2021-10-01","2025-09-03"),
"xau_dukascopy":(f"{B}/dukascopy/futures/XAU_USD-1m","2021-10-01","2025-09-03"),
"eurusd_dukascopy":(f"{B}/dukascopy/futures/EURUSD_USD-1m","2021-10-01","2025-09-03"),
"btcusdt_binance_spot":(f"{B}/binance/spot/BTC_USDT-1m","2019-09-08","2022-09-30")}
out={}
for k,(pre,a,b) in SER.items():
    fs=sorted(glob.glob(pre+".*.feather"))
    if not fs: print("chýba",k,pre); continue
    df=pd.concat([pd.read_feather(f) for f in fs if a[:4]<=f.split(".")[-2]<=b[:4]])
    df["date"]=pd.to_datetime(df["date"],utc=True); df=df[(df.date>=a)&(df.date<=b)].set_index("date")
    d=df.resample("1D").agg({"high":"max","low":"min","close":"last"}).dropna()
    tr=np.maximum(d.high-d.low,np.maximum(abs(d.high-d.close.shift()),abs(d.low-d.close.shift())))
    atr=tr.rolling(14).mean().median()
    out[k]=round(float(atr),6); out["px_"+k]=round(float(d.close.median()),6); print(k,out[k],out["px_"+k])
json.dump(out,open("/private/tmp/claude-501/-Users-martin-IBS/b71b5de5-7d7c-4c94-9a99-dbafbd991bc0/scratchpad/zaklad/atr.json","w"),indent=1)
