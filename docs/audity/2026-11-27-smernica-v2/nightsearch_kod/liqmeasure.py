"""Meranie likvidity na MNQ: berie cena nevybraté swing vrcholy/dná častejšie než náhodné úrovne?

Pre TF (5m, 15m, 1h, 4h) a silu pivotu (N barov z každej strany) nájde swing vrcholy (buy-side
likvidita nad nimi) a dná (sell-side pod nimi). Úroveň je k dispozícii až po potvrdení pivotu
(N barov vpravo). Potom meria na 5m baroch:

- ako často a za koľko ju cena zoberie (1 deň, 5 dní, 20 dní),
- to isté pre náhodnú úroveň v rovnakej vzdialenosti od ceny v náhodnom čase (baseline),
- čo sa deje po vybratí na TF úrovne: zavretie späť za úroveň do K barov (sweep/otočka)
  vs. pokračovanie, a medián pohybu v ATR oboma smermi.

Voliteľne len „výrazné“ swingy: cena z pivotu odišla aspoň o `disp` ATR do N barov.
"""
import sys, json
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core.candles import resample_ohlcv
from tradebot.core.types import INSTRUMENTS
from tester import engines

START, END = "2019-06-01", "2026-09-05"
DAY5 = 276           # ~5m barov za obchodný deň (23 h)
HOR = {"1 den": DAY5, "5 dni": 5 * DAY5, "20 dni": 20 * DAY5}
K = 6                # barov TF úrovne na posúdenie reakcie po vybratí


def load():
    m1 = pd.read_feather(engines.one_minute_file(INSTRUMENTS["mnq_databento"]))
    m1 = m1[(m1.date >= START) & (m1.date < END)].reset_index(drop=True)
    return m1


def atr(df, n=14):
    pc = df.close.shift(1)
    tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def first_hit(arr_extreme, start_idx, level, above, horizon):
    seg = arr_extreme[start_idx:start_idx + horizon]
    hit = seg > level if above else seg < level
    i = np.argmax(hit)
    return i if hit.size and hit[i] else -1


def measure(args):
    tf, N, disp = args
    m1 = load()
    b5 = resample_ohlcv(m1, 5).reset_index(drop=True)
    t5 = b5.date.astype("int64").to_numpy() // 10**6
    h5, l5, c5 = b5.high.to_numpy(), b5.low.to_numpy(), b5.close.to_numpy()
    bt = resample_ohlcv(m1, tf).reset_index(drop=True)
    tt = bt.date.astype("int64").to_numpy() // 10**6
    H, L, C = bt.high.to_numpy(), bt.low.to_numpy(), bt.close.to_numpy()
    A = atr(bt)
    tf_ms = tf * 60_000
    rng = np.random.default_rng(7)

    res = {"tf": tf, "N": N, "disp": disp}
    for side in ("buy", "sell"):   # buy-side = nad vrcholmi, sell-side = pod dnami
        above = side == "buy"
        levels = []
        for i in range(N, len(bt) - N - K - 1):
            win = H[i - N:i + N + 1] if above else L[i - N:i + N + 1]
            v = H[i] if above else L[i]
            if above and not (v == win.max() and (win[:N] < v).all()):
                continue
            if not above and not (v == win.min() and (win[:N] > v).all()):
                continue
            a = A[i]
            if a <= 0:
                continue
            away = (v - L[i + 1:i + N + 1].min()) if above else (H[i + 1:i + N + 1].max() - v)
            if away < disp * a:
                continue
            conf_ms = tt[i + N] + tf_ms          # pivot je známy po uzavretí N-tého baru vpravo
            levels.append((conf_ms, v, a))
        hits = {k: 0 for k in HOR}; base = {k: 0 for k in HOR}
        times, sweep, cont_mv, back_mv = [], 0, [], []
        taken_n = 0
        b_sweep, b_n, b_cont, b_back = 0, 0, [], []
        for conf_ms, v, a in levels:
            j = np.searchsorted(t5, conf_ms)
            if j >= len(t5) - 1:
                continue
            ext = h5 if above else l5
            k = first_hit(ext, j, v, above, HOR["20 dni"])
            dist = abs(v - c5[j - 1]) if j > 0 else abs(v - c5[j])
            for name, hz in HOR.items():
                if 0 <= k < hz:
                    hits[name] += 1
            # baseline: rovnaká vzdialenosť, rovnaká strana, náhodný čas
            r = int(rng.integers(1, len(t5) - HOR["20 dni"] - 1))
            lv = c5[r - 1] + dist if above else c5[r - 1] - dist
            kb = first_hit(ext, r, lv, above, HOR["20 dni"])
            for name, hz in HOR.items():
                if 0 <= kb < hz:
                    base[name] += 1
            if kb >= 0:   # reakcia pri náhodnej úrovni — rovnaké meranie
                qb = np.searchsorted(tt, t5[r + kb], side="right") - 1
                ab = A[qb] if A[qb] > 0 else a
                sc = C[qb:qb + K + 1]
                if above:
                    b_sweep += int((sc < lv).any()); b_cont.append((H[qb:qb + K + 1].max() - lv) / ab)
                    b_back.append((lv - L[qb:qb + K + 1].min()) / ab)
                else:
                    b_sweep += int((sc > lv).any()); b_cont.append((lv - L[qb:qb + K + 1].min()) / ab)
                    b_back.append((H[qb:qb + K + 1].max() - lv) / ab)
                b_n += 1
            if k < 0:
                continue
            taken_n += 1
            times.append(k * 5 / 60.0)
            # reakcia na TF úrovne: bar TF, v ktorom sa úroveň zobrala
            take_ms = t5[j + k]
            q = np.searchsorted(tt, take_ms, side="right") - 1
            seg_c = C[q:q + K + 1]
            if above:
                back = (seg_c < v).any()
                cont_mv.append((H[q:q + K + 1].max() - v) / a)
                back_mv.append((v - L[q:q + K + 1].min()) / a)
            else:
                back = (seg_c > v).any()
                cont_mv.append((v - L[q:q + K + 1].min()) / a)
                back_mv.append((H[q:q + K + 1].max() - v) / a)
            sweep += int(back)
        n = len(levels)
        res[side] = {
            "urovni": n,
            "vybrate": {k: round(100 * hits[k] / max(n, 1), 1) for k in HOR},
            "nahoda": {k: round(100 * base[k] / max(n, 1), 1) for k in HOR},
            "median_h": round(float(np.median(times)), 1) if times else None,
            "sweep_pct": round(100 * sweep / max(taken_n, 1), 1),
            "pokracovanie_atr": round(float(np.median(cont_mv)), 2) if cont_mv else None,
            "navrat_atr": round(float(np.median(back_mv)), 2) if back_mv else None,
            "nahoda_sweep_pct": round(100 * b_sweep / max(b_n, 1), 1),
            "nahoda_pokr_atr": round(float(np.median(b_cont)), 2) if b_cont else None,
            "nahoda_navrat_atr": round(float(np.median(b_back)), 2) if b_back else None,
        }
    return res


if __name__ == "__main__":
    cfgs = [(tf, N, d) for tf in (5, 15, 60, 240) for N in (3, 5, 10) for d in (0.0, 1.5)]
    with ProcessPoolExecutor(8) as ex:
        out = list(ex.map(measure, cfgs))
    json.dump(out, open("/Users/martin/IBS/.nightsearch/liqmeasure.json", "w"), indent=1)
    for r in out:
        for side in ("buy", "sell"):
            s = r[side]
            print(f"{r['tf']:>4}m N={r['N']:>2} disp={r['disp']} {side:4} n={s['urovni']:6} "
                  f"vybraté {s['vybrate']} náhoda {s['nahoda']} med {s['median_h']} h "
                  f"sweep {s['sweep_pct']}/{s['nahoda_sweep_pct']} % pokr {s['pokracovanie_atr']}/{s['nahoda_pokr_atr']} navrat {s['navrat_atr']}/{s['nahoda_navrat_atr']}")
