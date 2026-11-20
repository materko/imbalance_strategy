"""Štatistika Initial Balance (IB) — tá istá logika, akou počíta IB Lab (app.iblab.io).

### Čo to je

IB je rozpätie prvej hodiny seansy (New York 9:30–10:30 ET, Londýn 3:00–4:00 ET). Pre
každý deň sa z 1m sviečok spočíta, čo IB urobila: ktorý okraj sa prerazil prvý, kedy,
ako ďaleko cena po prieraze zašla (extension), koľko sa vrátila (retracement) a čo
robila pred prierazom. Dashboard potom len filtruje dni a kreslí rozdelenia.

### Odkiaľ je logika

Zreverzovaná 20. 11. 2026 z ich webu: server posiela predpočítané riadky dní
(`/api/data/<inštrument>/stats`), karta *Chart* počíta ten istý deň v prehliadači zo
sviečok (`/api/data/<inštrument>/days/<dátum>` = 5m sviečky seansy, 1m sviečky
prierazového baru, čas IB high/low po minútach). Funkcie nižšie sú prepis toho kódu
(chunk `06sn0_b_6eokn.js`, funkcia dňa a `magic`); agregácia je z `2ld9p3im9pmbm.js`.
Zdroj dát majú rovnaký ako my: Databento CME `ohlcv-1m`, front-month bez back-adjustmentu.

### Definície (všetko v násobkoch rozpätia IB, nie v bodoch)

* **Prieraz** — prvá 5m sviečka po IB, ktorej knôt prekročí IB high / IB low (ostro).
  Keď jedna sviečka prerazí oba okraje, berie sa ako medvedí (tak to robí ich kód).
* **Bias** — poradie, v akom vznikli IB high a IB low (po minútach): `lowFirst` =
  najprv low, býčí bias; `highFirst` = medvedí.
* **Max retracement** — od minúty prierazu do konca seansy najhlbší návrat do IB:
  0 = prerazený okraj, 0,5 = stred IB, 1 = opačný okraj.
* **Max extension** — najďalej za prerazený okraj od prierazovej sviečky do konca seansy.
* **HOS/LOS retracement** („magic") — býčí deň: najnižšie low *pred* maximom seansy
  (od minúty po prieraze); medvedí zrkadlovo. Môže byť záporné (cena ostala nad okrajom).
* **Before-break retracement** — od konca IB po prierazovú sviečku vrátane: najhlbší
  pohyb proti smeru prierazu, meraný od okraja biasu (IB high pri `lowFirst`).
* **IB close** — kde zavrela posledná 5m sviečka IB, meraná od okraja biasu (0 až 1).
* **Zóny** — po 0,1: Z1 = 0,00–0,09, Z2 = 0,10–0,19 …

Spustenie: ``python -m tester.initial_balance --symbol ES [--bias lowFirst] [--dow 2] …``
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from tradebot.core.candles import resample_ohlcv
from tradebot.core.paths import TESTER_ARCHIVE

__all__ = [
    "SESSIONS", "Session", "load_1m", "compute_days", "compute_day", "summary", "select", "Filter",
    "symbols", "data_signature",
    "zone", "signed_zone", "ext_zone", "close_band", "ib_pct_band", "percentile", "median",
]


# ------------------------------------------------------------------------------- seansy


@dataclass(frozen=True)
class Session:
    id: str
    #: minúty od polnoci v New Yorku
    ib_start: int
    ib_end: int
    session_end: int


SESSIONS: dict[str, Session] = {
    "ny": Session("ny", 9 * 60 + 30, 10 * 60 + 30, 16 * 60),
    "london": Session("london", 3 * 60, 4 * 60, 8 * 60 + 30),
}

NY_TZ = "America/New_York"

#: pásma veľkosti IB v % ceny (filter „IB %")
IB_PCT_BANDS: tuple[tuple[float, float, str], ...] = (
    (0.0, 0.2, "0–0.19%"), (0.2, 0.4, "0.2–0.39%"), (0.4, 0.6, "0.4–0.59%"),
    (0.6, 0.8, "0.6–0.79%"), (0.8, 1.1, "0.8–1.09%"), (1.1, math.inf, ">1.1%"),
)


# ------------------------------------------------------------------------------- zóny


def zone(x: float) -> int:
    """Zóna retracementu: Z1 = 0,00–0,09 … (ich `v()`; zaokrúhli na stotiny pred delením)."""
    return math.floor(round(100 * abs(x)) / 100 * 10 + 1e-9) + 1


def signed_zone(x: float) -> int:
    """HOS/LOS: kladné Z, záporné P (cena ostala za okrajom)."""
    z = zone(x)
    return z if x >= 0 else -z


def ext_zone(x: float) -> int:
    """Zóna extension (ich `K()`, bez zaokrúhlenia na stotiny)."""
    return math.floor(10 * x + 1e-9) + 1


def close_band(x: float | None) -> int | None:
    """Pásmo IB close 1–10 (0,00 až −0,09 … −0,90 až −1,00)."""
    if x is None or abs(x) > 1 + 1e-9:
        return None
    return min(10, max(1, math.floor(abs(x) / 0.1 + 1e-9) + 1))


def ib_pct_band(x: float) -> int:
    for i, (lo, hi, _) in enumerate(IB_PCT_BANDS):
        if lo <= x < hi:
            return i
    return len(IB_PCT_BANDS) - 1


# ------------------------------------------------------------------------------- dáta


FUTURES_DIR = TESTER_ARCHIVE / "databento" / "futures"


def _files(symbol: str, root: Path | None = None) -> list[Path]:
    folder = Path(root) if root else FUTURES_DIR
    return sorted(folder.glob(f"{symbol.upper()}_USD-1m.*.feather"))


def symbols(root: Path | None = None) -> list[str]:
    """Korene CME futures, pre ktoré sú v archíve 1m sviečky."""
    folder = Path(root) if root else FUTURES_DIR
    return sorted({f.name.split("_USD-1m.")[0] for f in folder.glob("*_USD-1m.*.feather")})


def data_signature(symbol: str, root: Path | None = None) -> tuple:
    """Mená, veľkosti a časy súborov symbolu — zmení sa, keď importér pridá rok alebo mesiac."""
    return tuple((f.name, f.stat().st_size, f.stat().st_mtime_ns) for f in _files(symbol, root))


def load_1m(symbol: str, root: Path | None = None):
    """1m front-month sviečky CME futures z archívu (`<SYM>_USD-1m.<rok>.feather`)."""
    import pandas as pd

    folder = Path(root) if root else FUTURES_DIR
    files = _files(symbol, root)
    if not files:
        raise FileNotFoundError(f"{folder}: žiadne {symbol.upper()}_USD-1m.*.feather")
    df = pd.concat([pd.read_feather(f) for f in files], ignore_index=True)
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _slot5(m: int) -> str:
    """Čas do 5m slotu — tak ich server ukladá aj časy nájdené v 1m sviečkach."""
    return _hhmm(m // 5 * 5)


def _session_frames(df1m, sess: Session):
    """1m a 5m sviečky seansy, zoskupené po dňoch v New Yorku → {dátum: (c1, c5)}."""
    import numpy as np

    et = df1m["date"].dt.tz_convert(NY_TZ)
    mins = (et.dt.hour * 60 + et.dt.minute).to_numpy()
    mask = (mins >= sess.ib_start) & (mins < sess.session_end) & (et.dt.dayofweek.to_numpy() < 5)
    one = df1m.loc[mask].reset_index(drop=True)
    five = resample_ohlcv(one, 5)

    def split(frame):
        e = frame["date"].dt.tz_convert(NY_TZ)
        day = e.dt.date.to_numpy()
        arr = {
            "t": (e.dt.hour * 60 + e.dt.minute).to_numpy(),
            "o": frame["open"].to_numpy(), "h": frame["high"].to_numpy(),
            "l": frame["low"].to_numpy(), "c": frame["close"].to_numpy(),
        }
        out: dict[date, dict[str, Any]] = {}
        if len(day) == 0:
            return out
        cuts = np.flatnonzero(day[1:] != day[:-1]) + 1
        starts = np.concatenate(([0], cuts))
        ends = np.concatenate((cuts, [len(day)]))
        for s, e_ in zip(starts, ends):
            out[day[s]] = {k: v[s:e_] for k, v in arr.items()}
        return out

    return split(one), split(five)


# ------------------------------------------------------------------------------- jeden deň


def _first_cross(c1b, up: bool, ib_high: float, ib_low: float) -> int:
    """Index minúty v prierazovej sviečke, ktorá prekročila okraj (ich `F`)."""
    if c1b is None:
        return -1
    for i in range(len(c1b["t"])):
        if (c1b["h"][i] > ib_high) if up else (c1b["l"][i] < ib_low):
            return i
    return -1


def _magic(c5, ib_high, ib_low, up, s, c1b, p0):
    """HOS/LOS retracement — doslovný prepis ich funkcie (vrátane okrajových prípadov)."""
    o = ib_high - ib_low
    n5 = len(c5["t"])
    if o <= 0 or n5 <= p0:
        return None
    a = max(p0, s + 1)
    sb = _first_cross(c1b, up, ib_high, ib_low)
    n1 = len(c1b["t"]) if c1b is not None else 0
    H, L, T = c5["h"], c5["l"], c5["t"]
    if up:
        best, li = -math.inf, -1
        for t in range(p0, n5):
            if H[t] > best:
                best, li = H[t], t
        if li < 0:
            return None
        if li == s and sb >= 0:
            r, ai = -math.inf, -1
            for e in range(n1):
                if c1b["h"][e] > r:
                    r, ai = c1b["h"][e], e
            if r != H[li]:
                return None
            u, d = math.inf, -1
            for e in range(sb + 1, ai + 1):
                if c1b["l"][e] < u:
                    u, d = c1b["l"][e], e
            if d < 0:
                return None
            return (ib_high - u) / o, int(c1b["t"][d])
        u, tm = math.inf, None
        if li > s and sb >= 0:
            for e in range(sb + 1, n1):
                if c1b["l"][e] < u:
                    u, tm = c1b["l"][e], int(c1b["t"][e])
        for t in range(a, li + 1):
            if L[t] < u:
                u, tm = L[t], int(T[t])
        if tm is None:
            return None
        return (ib_high - u) / o, tm
    best, li = math.inf, -1
    for t in range(p0, n5):
        if L[t] < best:
            best, li = L[t], t
    if li < 0:
        return None
    if li == s and sb >= 0:
        r, ai = math.inf, -1
        for e in range(n1):
            if c1b["l"][e] < r:
                r, ai = c1b["l"][e], e
        if r != L[li]:
            return None
        u, d = -math.inf, -1
        for e in range(sb + 1, ai + 1):
            if c1b["h"][e] > u:
                u, d = c1b["h"][e], e
        if d < 0:
            return None
        return (u - ib_low) / o, int(c1b["t"][d])
    u, tm = -math.inf, None
    if li > s and sb >= 0:
        for e in range(sb + 1, n1):
            if c1b["h"][e] > u:
                u, tm = c1b["h"][e], int(c1b["t"][e])
    for t in range(a, li + 1):
        if H[t] > u:
            u, tm = H[t], int(T[t])
    if tm is None:
        return None
    return (u - ib_low) / o, tm


def compute_day(day: date, c1: dict, c5: dict, sess: Session) -> dict[str, Any] | None:
    """Jeden deň → riadok štatistiky (polia ako `rows` v IB Lab). `None` = deň bez IB."""
    import numpy as np

    ib1 = c1["t"] < sess.ib_end
    if not ib1.any():
        return None
    ib_high = float(c1["h"][ib1].max())
    ib_low = float(c1["l"][ib1].min())
    rng = ib_high - ib_low
    t_ib = c1["t"][ib1]
    ibhT = int(t_ib[np.argmax(c1["h"][ib1] == ib_high)])
    iblT = int(t_ib[np.argmax(c1["l"][ib1] == ib_low)])
    bias = "highFirst" if ibhT < iblT else "lowFirst" if ibhT > iblT else "tie"

    T, H, L, C = c5["t"], c5["h"], c5["l"], c5["c"]
    p0 = int((T < sess.ib_end).sum())  # prvá 5m sviečka po IB (u nich pevne 12)
    ib_close = None
    if bias != "tie" and rng > 0 and p0 > 0:
        cl = float(C[p0 - 1])
        ib_close = (ib_high - cl) / rng if bias == "lowFirst" else (cl - ib_low) / rng
    mid = (ib_high + ib_low) / 2
    row: dict[str, Any] = {
        "date": day.isoformat(), "dow": day.isoweekday(), "bias": bias,
        "ib_high": ib_high, "ib_low": ib_low, "ibhT": _hhmm(ibhT), "iblT": _hhmm(iblT),
        "ibPct": (ib_high - ib_low) / mid * 100 if mid > 0 else 0.0,
        "ibClose": ib_close, "outcome": "none", "dir": None, "dbl": False,
        "slot": None, "brkET": None, "dblSlot": None,
        "scale": None, "zone": None, "retrSlot": None,
        "ext": None, "extSlot": None,
        "magicScale": None, "magicZone": 0, "magicSlot": None,
        "bbScale": None, "bbZone": None, "bbSlot": None,
    }
    up_i = next((i for i in range(p0, len(T)) if H[i] > ib_high), -1)
    dn_i = next((i for i in range(p0, len(T)) if L[i] < ib_low), -1)
    has_up, has_dn = up_i >= 0, dn_i >= 0
    if not (has_up or has_dn) or rng <= 0:
        return row
    first_up = has_up and (not has_dn or up_i < dn_i)
    s = up_i if first_up else dn_i
    row.update(outcome="high" if first_up else "low", dir="bull" if first_up else "bear",
               dbl=has_up and has_dn, slot=_hhmm(int(T[s])))
    if row["dbl"]:
        row["dblSlot"] = _hhmm(int(T[max(up_i, dn_i)]))

    m1 = (c1["t"] >= T[s]) & (c1["t"] < T[s] + 5)
    c1b = {k: v[m1] for k, v in c1.items()}
    sb = _first_cross(c1b, first_up, ib_high, ib_low)
    # brkET je u nich vždy to isté čo slot; minúta prierazu je navyše (`brkMin`)
    row["brkET"] = row["slot"]
    row["brkMin"] = _hhmm(int(c1b["t"][sb])) if sb >= 0 else row["slot"]
    after = slice(sb + 1, None) if sb >= 0 else slice(0, 0)

    # max retracement a max extension
    if first_up:
        best, tm = math.inf, None
        for lo, t in zip(c1b["l"][after], c1b["t"][after]):
            if lo < best:
                best, tm = lo, int(t)
        for i in range(s + 1, len(T)):
            if L[i] < best:
                best, tm = L[i], int(T[i])
        if tm is not None:
            row["scale"], row["retrSlot"] = max(0.0, (ib_high - best) / rng), _slot5(tm)
        hi_i = s + int(np.argmax(H[s:]))
        row["ext"], row["extSlot"] = max(0.0, (H[hi_i] - ib_high) / rng), _hhmm(int(T[hi_i]))
    else:
        best, tm = -math.inf, None
        for hi, t in zip(c1b["h"][after], c1b["t"][after]):
            if hi > best:
                best, tm = hi, int(t)
        for i in range(s + 1, len(T)):
            if H[i] > best:
                best, tm = H[i], int(T[i])
        if tm is not None:
            row["scale"], row["retrSlot"] = max(0.0, (best - ib_low) / rng), _slot5(tm)
        lo_i = s + int(np.argmin(L[s:]))
        row["ext"], row["extSlot"] = max(0.0, (ib_low - L[lo_i]) / rng), _hhmm(int(T[lo_i]))
    if row["scale"] is not None:
        row["zone"] = zone(row["scale"])

    # before-break retracement — od konca IB po prierazovú sviečku vrátane, od okraja biasu
    low_first = bias == "lowFirst"
    if first_up:
        bi = p0 + int(np.argmin(L[p0:s + 1]))
        x = L[bi]
    else:
        bi = p0 + int(np.argmax(H[p0:s + 1]))
        x = H[bi]
    bb = max(0.0, (ib_high - x) / rng if low_first else (x - ib_low) / rng)
    row["bbScale"], row["bbZone"], row["bbSlot"] = bb, zone(bb), _hhmm(int(T[bi]))

    mg = _magic(c5, ib_high, ib_low, first_up, s, c1b, p0)
    if mg is not None:
        row["magicScale"], row["magicSlot"] = mg[0], _slot5(mg[1])
        row["magicZone"] = signed_zone(mg[0])
    return row


def compute_days(df1m, session: str = "ny") -> list[dict[str, Any]]:
    """Všetky dni s IB v dátach → zoznam riadkov (zoradený podľa dátumu)."""
    sess = SESSIONS[session]
    ones, fives = _session_frames(df1m, sess)
    out = []
    for d in sorted(ones):
        if d not in fives:
            continue
        r = compute_day(d, ones[d], fives[d], sess)
        if r is not None:
            out.append(r)
    return out


# ------------------------------------------------------------------------------- agregácia


def median(xs: Sequence[float]) -> float | None:
    """Ich `T()` — medián zoradeného zoznamu."""
    n = len(xs)
    if not n:
        return None
    return xs[(n - 1) // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def percentile(xs: Sequence[float], p: float) -> float | None:
    """Ich `C()` — lineárna interpolácia na zoradenom zozname."""
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    f = math.floor(k)
    return xs[f] + (k - f) * (xs[f + 1] - xs[f]) if f + 1 < len(xs) else xs[f]


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _slot_floor(hhmm: str, step: int) -> str:
    return _hhmm(_mins(hhmm) // step * step)


PERIODS = ("all", "10y", "covid", "3y", "1y")


def _cutoff(period: str, last: str) -> str | None:
    if period == "all":
        return None
    if period == "covid":
        return "2020-01-01"
    y, m, d = last.split("-")
    return f"{int(y) - int(period[:-1])}-{m}-{d}"


def _news_sets() -> dict[str, set[str]] | None:
    """FOMC / CPI / NFP z `tester.calendar` (len roky, ktoré kalendár pokrýva)."""
    try:
        from tester import calendar as cal
    except ImportError:  # pragma: no cover
        return None
    sets: dict[str, set[str]] = {"fomc": set(), "cpi": set(), "nfp": set(), "holiday": set()}
    for d, (keys, _) in cal.events().items():
        for k in keys.split("+"):
            if k.lower() in sets:
                sets[k.lower()].add(d.isoformat())
    cov = cal.coverage()
    if cov:
        for y in range(cov[0].year, cov[1].year + 1):
            sets["holiday"].update(d.isoformat() for d in cal.us_half_days(y))
    sets["_coverage"] = {cov[0].isoformat(), cov[1].isoformat()} if cov else set()
    return sets


def _news_ok(news: str, day: str, sets: dict[str, set[str]] | None) -> bool:
    if news == "all":
        return True
    if not sets:
        return False
    cov = sorted(sets.get("_coverage") or ())
    if cov and not (cov[0] <= day <= cov[1]):
        return False  # mimo pokrytia kalendára nevieme, či bola správa
    if news == "quiet":
        return not any(day in sets[k] for k in ("fomc", "cpi", "nfp", "holiday"))
    return day in sets.get(news, set())


@dataclass
class Filter:
    """Filtre dashboardu. `scope="pre"` = pred prierazom, `"post"` = po prieraze (`dir`)."""

    scope: str = "pre"
    dir: str = "bull"
    dow: int | None = None
    bias: str = "all"
    bands: frozenset[int] = frozenset()        # IB % pásma (indexy IB_PCT_BANDS)
    close_bands: frozenset[int] = frozenset()  # IB close 1–10, len „pre"
    slots: frozenset[str] = frozenset()        # čas prierazu, len „post"
    slot_step: int = 5
    brk: str = "all"                           # single / double, len „post"
    bias_break: str = "with"                   # with / against, len „pre"
    news: str = "all"
    period: str = "all"

    def match(self, r: dict[str, Any], cutoff: str | None, news_sets) -> bool:
        if cutoff and r["date"] < cutoff:
            return False
        if self.dow is not None and r["dow"] != self.dow:
            return False
        if self.bands and ib_pct_band(r["ibPct"]) not in self.bands:
            return False
        if self.bias != "all" and r["bias"] != self.bias:
            return False
        if not _news_ok(self.news, r["date"], news_sets):
            return False
        if self.scope == "pre":
            return not self.close_bands or close_band(r["ibClose"]) in self.close_bands
        if r["dir"] != self.dir:
            return False
        if self.slots and _slot_floor(r["slot"], self.slot_step) not in self.slots:
            return False
        return self.brk == "all" or (self.brk == "double") == bool(r["dbl"])


def _hist_time(rows, field: str, sess: Session, gran: int) -> dict[str, Any]:
    vals = sorted(_mins(r[field]) for r in rows if r.get(field))
    if not vals:
        return {"n": 0}
    start, end = sess.ib_end, sess.session_end - 5
    counts: dict[str, int] = {}
    for v in vals:
        if start <= v <= end:
            k = _hhmm(start + (v - start) // gran * gran)
            counts[k] = counts.get(k, 0) + 1
    med, p70 = median(vals), percentile(vals, 70)

    def slot_end(x: float) -> str:  # karta ukazuje koniec 5m slotu s mediánom
        return _hhmm(int(start + (math.floor((x - start) / 5) + 1) * 5))

    return {"n": len(vals), "median": slot_end(med), "p70": slot_end(p70),
            "pct": {k: 100 * c / len(rows) for k, c in sorted(counts.items())}}


def _hist_zone(rows, scale: str, zfield: str, signed: bool = False, invert: bool = False,
               cut: float = 3.0) -> dict[str, Any]:
    inside = [r for r in rows if r.get(scale) is not None and abs(r[scale]) < cut]
    if not inside:
        return {"n": 0, "excluded": len(rows)}
    xs = sorted(r[scale] if signed else abs(r[scale]) for r in inside)
    counts: dict[int, int] = {}
    for r in inside:
        counts[r[zfield]] = counts.get(r[zfield], 0) + 1
    return {"n": len(inside), "excluded": len(rows) - len(inside),
            "median": median(xs), "p70": percentile(xs, 30 if invert else 70),
            "pct": {(f"Z{z}" if z > 0 else f"P{-z}"): 100 * c / len(inside)
                    for z, c in sorted(counts.items())}}


def _hist_ext(rows, max_zone: int = 30) -> dict[str, Any]:
    xs = sorted(r["ext"] for r in rows if r.get("ext") is not None)
    if not xs:
        return {"n": 0}
    counts: dict[int, int] = {}
    for x in xs:
        if ext_zone(x) <= max_zone:
            counts[ext_zone(x)] = counts.get(ext_zone(x), 0) + 1
    return {"n": len(xs), "excluded": len(xs) - sum(counts.values()),
            "median": median(xs), "p70": percentile(xs, 70),
            "pct": {f"Z{z}": 100 * c / len(xs) for z, c in sorted(counts.items())}}


def select(days: Sequence[dict[str, Any]], flt: Filter) -> list[dict[str, Any]]:
    """Dni, ktoré prejdú filtrom (obdobie sa ráta od posledného dňa v dátach)."""
    if not days:
        return []
    cutoff = _cutoff(flt.period, days[-1]["date"])
    news_sets = _news_sets() if flt.news != "all" else None
    return [r for r in days if flt.match(r, cutoff, news_sets)]


def summary(days: Sequence[dict[str, Any]], flt: Filter | None = None, session: str = "ny",
            gran: int = 15) -> dict[str, Any]:
    """Karty a histogramy dashboardu pre vyfiltrované dni (ako „Statistics before/after break").

    Ako u nich: high/low/none sa počíta zo všetkých dní, single break zo všetkých dní
    s prierazom, všetko ostatné len z dní, kde po prieraze ešte niečo bolo (max retracement
    existuje) — deň s prierazom v poslednej sviečke seansy do rozdelení nejde.
    """
    flt = flt or Filter()
    sess = SESSIONS[session]
    if not days:
        return {"n": 0}
    sel = select(days, flt)
    brk = [r for r in sel if r["outcome"] != "none"]
    stats = [r for r in brk if r["scale"] is not None]
    if flt.scope == "pre":
        out: dict[str, Any] = {"scope": "pre", "n": len(sel)}
        n = len(sel) or 1
        out["break_high_pct"] = 100 * sum(r["outcome"] == "high" for r in sel) / n
        out["break_low_pct"] = 100 * sum(r["outcome"] == "low" for r in sel) / n
        out["no_break_pct"] = 100 * sum(r["outcome"] == "none" for r in sel) / n
        # pri zvolenom biase len dni s prvým prierazom v smere biasu (alebo proti nemu)
        if flt.bias in ("lowFirst", "highFirst"):
            want = "bull" if flt.bias == "lowFirst" else "bear"
            if flt.bias_break == "against":
                want = "bear" if want == "bull" else "bull"
            stats = [r for r in stats if r["dir"] == want]
        bb_pos = [r for r in stats if (r["bbScale"] or 0) > 0]
        out["break_time"] = _hist_time(stats, "slot", sess, gran)
        out["before_break_retr"] = _hist_zone(bb_pos, "bbScale", "bbZone",
                                              invert=flt.bias_break == "against")
        out["before_break_time"] = _hist_time(bb_pos, "bbSlot", sess, gran)
        return out
    out = {"scope": "post", "n": len(stats)}
    out["single_break_pct"] = 100 * sum(not r["dbl"] for r in brk) / (len(brk) or 1)
    n = len(stats) or 1
    for key, field, thr in (("ext_over_025", "ext", .25), ("retr_over_025", "scale", .25),
                            ("retr_over_05", "scale", .5), ("magic_over_05", "magicScale", .5)):
        out[key + "_pct"] = 100 * sum((r[field] or 0) >= thr for r in stats) / n
    retr = [r for r in stats if r["scale"] > 0]
    magic = [r for r in stats if r["magicZone"] != 0]
    out["max_retr"] = _hist_zone(retr, "scale", "zone")
    out["max_retr_time"] = _hist_time(retr, "retrSlot", sess, gran)
    out["max_ext"] = _hist_ext(stats)
    out["max_ext_time"] = _hist_time(stats, "extSlot", sess, gran)
    out["magic"] = _hist_zone(magic, "magicScale", "magicZone", signed=True)
    out["magic_time"] = _hist_time(magic, "magicSlot", sess, gran)
    out["double_break_time"] = _hist_time([r for r in stats if r["dbl"]], "dblSlot", sess, gran)
    return out


# ------------------------------------------------------------------------------- CLI


def _fmt_summary(s: dict[str, Any]) -> str:
    def z(h):
        if not h or not h.get("n"):
            return "—"
        return f"medián {h['median']:.2f} · 70 % {h['p70']:.2f} · n={h['n']}"

    def t(h):
        if not h or not h.get("n"):
            return "—"
        return f"medián {h['median']} · 70 % {h['p70']} · n={h['n']}"

    lines = [f"dní: {s['n']}"]
    if s.get("scope") == "pre":
        lines += [f"prieraz high {s['break_high_pct']:.1f} % · low {s['break_low_pct']:.1f} % · "
                  f"bez prierazu {s['no_break_pct']:.1f} %",
                  f"čas prierazu: {t(s['break_time'])}",
                  f"before-break retracement: {z(s['before_break_retr'])}",
                  f"čas before-break: {t(s['before_break_time'])}"]
    elif s.get("n"):
        lines += [f"single break {s['single_break_pct']:.1f} % · ext ≥0,25 {s['ext_over_025_pct']:.1f} % · "
                  f"retr ≥0,25 {s['retr_over_025_pct']:.1f} % · retr ≥0,5 {s['retr_over_05_pct']:.1f} % · "
                  f"HOS/LOS ≥0,5 {s['magic_over_05_pct']:.1f} %",
                  f"max retracement: {z(s['max_retr'])} · čas {t(s['max_retr_time'])}",
                  f"max extension: {z(s['max_ext'])} · čas {t(s['max_ext_time'])}",
                  f"HOS/LOS: {z(s['magic'])} · čas {t(s['magic_time'])}",
                  f"double break: {t(s['double_break_time'])}"]
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m tester.initial_balance",
                                description="Štatistika Initial Balance (logika IB Lab).")
    p.add_argument("--symbol", default="ES", help="koreň CME futures v archíve (ES, MNQ, MGC, …)")
    p.add_argument("--data-dir", type=Path, help="adresár s <SYM>_USD-1m.<rok>.feather")
    p.add_argument("--session", choices=sorted(SESSIONS), default="ny")
    p.add_argument("--scope", choices=("pre", "post"), default="pre")
    p.add_argument("--dir", choices=("bull", "bear"), default="bull")
    p.add_argument("--dow", type=int, choices=range(1, 6))
    p.add_argument("--bias", choices=("all", "lowFirst", "highFirst"), default="all")
    p.add_argument("--bias-break", choices=("with", "against"), default="with")
    p.add_argument("--close-band", type=int, action="append", default=[], help="1–10, opakovateľné")
    p.add_argument("--ib-band", type=int, action="append", default=[], help="0–5, opakovateľné")
    p.add_argument("--slot", action="append", default=[], help="čas prierazu HH:MM (post)")
    p.add_argument("--slot-step", type=int, choices=(5, 15, 30), default=5)
    p.add_argument("--break", dest="brk", choices=("all", "single", "double"), default="all")
    p.add_argument("--news", choices=("all", "fomc", "cpi", "nfp", "holiday", "quiet"), default="all")
    p.add_argument("--period", choices=PERIODS, default="all")
    p.add_argument("--gran", type=int, choices=(5, 15), default=15, help="šírka časových stĺpcov")
    p.add_argument("--days-json", type=Path, help="zapíš riadky všetkých dní do JSON")
    p.add_argument("--json", action="store_true", help="súhrn ako JSON namiesto textu")
    return p


def main(argv: Iterable[str] | None = None) -> int:
    a = _build_parser().parse_args(list(argv) if argv is not None else None)
    days = compute_days(load_1m(a.symbol, a.data_dir), a.session)
    if a.days_json:
        a.days_json.write_text(json.dumps(days, ensure_ascii=False), encoding="utf-8")
    flt = Filter(scope=a.scope, dir=a.dir, dow=a.dow, bias=a.bias, bias_break=a.bias_break,
                 close_bands=frozenset(a.close_band), bands=frozenset(a.ib_band),
                 slots=frozenset(a.slot), slot_step=a.slot_step, brk=a.brk, news=a.news,
                 period=a.period)
    s = summary(days, flt, a.session, a.gran)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        rng = f"{days[0]['date']} – {days[-1]['date']}" if days else "—"
        print(f"{a.symbol.upper()} · {a.session} · {rng}")
        print(_fmt_summary(s))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
