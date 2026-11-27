"""Kúp na otvorení dňa po zavretí nad EMA 10 (predtým pod), drž 10 obchodných dní, predaj na zavretí 10. dňa.
Počas držania sa nové signály ignorujú. Porovnanie: kúp a drž, a náhodné vstupy s tým istým držaním (1000×)."""
import sys, numpy as np
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
from ema_study import daily, SYMS
HOLD = 10
rng = np.random.default_rng(7)
def run(d, entries):
    tr, eq, i = [], [1.0], 50
    while i < len(d) - 1:
        if entries[i] and i + HOLD < len(d):
            r = d["close"].iloc[i + HOLD] / d["open"].iloc[i + 1] - 1
            tr.append(r); eq.append(eq[-1] * (1 + r)); i += HOLD + 1
        else:
            i += 1
    e = np.array(eq); dd = (1 - e / np.maximum.accumulate(e)).max()
    return np.array(tr), e[-1] - 1, dd
print(f"{'akcia':6s} {'obch':>5s} {'zisk %':>7s} {'priem.':>7s} {'spolu':>8s} {'max DD':>7s} {'v trhu':>7s} | {'kúp+drž':>8s} {'DD':>5s} | náhoda: {'zisk %':>6s} {'spolu':>7s}")
T, R = [], []
for s in SYMS:
    d = daily(s); c, e = d["close"], d["e10"]
    sig = ((c > e) & (c.shift() <= e.shift())).values
    tr, tot, dd = run(d, sig)
    days = len(tr) * (HOLD + 1) / (len(d) - 50)
    bh = d["close"].iloc[-1] / d["open"].iloc[51] - 1
    eqb = d["close"].iloc[50:] / d["close"].iloc[50]; bdd = (1 - eqb / eqb.cummax()).max()
    # náhoda: rovnaký počet vstupov v náhodných dňoch, rovnaké držanie
    rw, rt = [], []
    for _ in range(300):
        rs = np.zeros(len(d), bool); rs[rng.choice(np.arange(50, len(d) - HOLD - 1), size=len(tr), replace=False)] = True
        t2, tt, _ = run(d, rs); rw.append((t2 > 0).mean()); rt.append(tt)
    T.append(tr); R.append(np.mean(rw))
    print(f"{s:6s} {len(tr):5d} {100*(tr>0).mean():6.1f}% {100*tr.mean():+6.2f}% {100*tot:+7.0f}% {100*dd:6.1f}% {100*days:6.0f}% | {100*bh:+7.0f}% {100*bdd:4.0f}% | {100*np.mean(rw):6.1f}% {100*np.median(rt):+6.0f}%")
a = np.concatenate(T)
print(f"\nSPOLU: {len(a)} obchodov, ziskových {100*(a>0).mean():.1f} % (náhodné 10-dňové držanie: {100*np.mean(R):.1f} %), "
      f"priemer {100*a.mean():+.2f} % na obchod, medián {100*np.median(a):+.2f} %, najhorší {100*a.min():+.1f} %, najlepší {100*a.max():+.1f} %")
