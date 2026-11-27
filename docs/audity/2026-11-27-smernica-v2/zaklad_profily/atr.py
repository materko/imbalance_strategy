"""Medián denného ATR(14) pre trhy V2 a pomery ATR domov → M v spoločnom okne (SMERNICA V2, krok 3a bod 5).

Okno páru = prienik období L oboch trhov. Ak je kratší ako 1 rok (MNQ↔MGC, 6E↔MGC), má každý trh ATR zo SVOJHO L —
okná sú rôzne, lebo prienik celých dát by obsahoval roky trezoru a rok A (§1 trezor mimo štúdií); výnimka sa nerobí.
Výstup `atr.json` vedľa skriptu: hodnoty na L každého trhu (informatívne), `pairs` (pomery, ktoré berie build.py) a `_meta`.
Spustenie z koreňa repozitára: `.venv/bin/python -I docs/audity/2026-11-27-smernica-v2/zaklad_profily/atr.py`.
"""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

B = "/Users/martin/IBS/data/archive/tester"
SER = {"mnq_databento": (f"{B}/databento/futures/MNQ_USD-1m", "2019-05-05", "2022-09-30"),
       "es_databento": (f"{B}/databento/futures/ES_USD-1m", "2015-01-01", "2025-09-03"),
       "mym_databento": (f"{B}/databento/futures/MYM_USD-1m", "2019-06-02", "2022-09-30"),
       "mgc_databento": (f"{B}/databento/futures/MGC_USD-1m", "2023-01-01", "2025-09-03"),
       "6e_databento": (f"{B}/databento/futures/6E_USD-1m", "2016-01-03", "2021-09-30"),
       "btcusdt_binance": (f"{B}/binance/futures/BTC_USDT_USDT-1m-futures", "2019-09-08", "2022-09-30")}
#: domovy z domov.json, ktoré majú bodové prahy
HOMES = ("mnq_databento", "es_databento", "6e_databento")
METODA = ("medián kĺzavého ATR(14) z denných sviečok (resample 1D UTC z 1m archívu, celé dni bez dier), "
          "px_* = medián denného zavretia; okno páru = prienik L; pod 1 rok každý trh na svojom L (rôzne okná), "
          "nikdy nie celé dáta — tie obsahujú roky trezoru a rok A (§1)")


def daily(pre):
    fs = sorted(glob.glob(pre + ".*.feather"))
    df = pd.concat([pd.read_feather(f, columns=["date", "high", "low", "close"]) for f in fs])
    df["date"] = pd.to_datetime(df["date"], utc=True)
    d = df.set_index("date").resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    tr = np.maximum(d.high - d.low, np.maximum(abs(d.high - d.close.shift()), abs(d.low - d.close.shift())))
    d["atr"] = tr.rolling(14).mean()
    return d.dropna()


def med(d, a, b):
    x = d[(d.index >= pd.Timestamp(a, tz="UTC")) & (d.index <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    return float(x.atr.median()), float(x.close.median()), len(x)


def main():
    D = {k: daily(pre) for k, (pre, _, _) in SER.items()}
    full = {k: (d.index[0].strftime("%Y-%m-%d"), d.index[-1].strftime("%Y-%m-%d")) for k, d in D.items()}
    out = {"_meta": {"metoda": METODA, "obdobia": {k: f"{a} – {b}" for k, (_, a, b) in SER.items()},
                     "cele_data": {k: f"{a} – {b}" for k, (a, b) in full.items()}}}
    for k, (_, a, b) in SER.items():
        atr, px, _ = med(D[k], a, b)
        out[k], out["px_" + k] = round(atr, 6), round(px, 6)
    pairs = {}
    for h in HOMES:
        for m in SER:
            if m == h:
                continue
            a, b = max(SER[h][1], SER[m][1]), min(SER[h][2], SER[m][2])
            if (pd.Timestamp(b) - pd.Timestamp(a)).days >= 365:
                zdroj, okno = "spoločné L (prienik L)", f"{a} – {b}"
                ah, _, nh = med(D[h], a, b)
                am, _, nm = med(D[m], a, b)
            else:
                zdroj = ("rôzne okná: každý trh na svojom L — spoločné L chýba (prienik kratší ako 1 rok) a celé dáta "
                         "by obsahovali roky trezoru a rok A (§1)")
                okno = f"{h} {SER[h][1]} – {SER[h][2]}, {m} {SER[m][1]} – {SER[m][2]}"
                ah, _, nh = med(D[h], SER[h][1], SER[h][2])
                am, _, nm = med(D[m], SER[m][1], SER[m][2])
            pairs[f"{h}->{m}"] = {"pomer": float(f"{am / ah:.8g}"), "atr_domov": round(ah, 6), "atr_m": round(am, 6),
                                  "okno": okno, "zdroj": zdroj, "dni": [nh, nm],
                                  "pomer_rozne_L": float(f"{out[m] / out[h]:.8g}")}
            print(h, "->", m, pairs[f"{h}->{m}"])
    out["pairs"] = pairs
    json.dump(out, open(Path(__file__).with_name("atr.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
