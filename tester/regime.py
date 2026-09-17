"""V akom stave bol trh, keď obchod vznikol — vlastnosti známe **pri vstupe**.

### Načo to je
Analytika vie rozdeliť obchody podľa toho, čo je v nich uložené: hodina, deň, smer,
vzdialenosť stopu. To sú vlastnosti **obchodu**. Chýbala vlastnosť **trhu** — či bol
v trende alebo v rozsahu, či bola volatilita vysoká alebo nízka, či sa vstupovalo pri
kraji rozsahu alebo v jeho strede.

Práve tam býva zvyšný edge. Rada, ktorá zaznie pri každom patterne s nulovou výhodou, je
„pridaj filter režimu" — a bez týchto čísel sa taký filter nedá ani navrhnúť, ani overiť.

### Prečo sú to legitímne filtre
Všetky štyri sa počítajú **z barov uzavretých pred vstupom** (čas zatvorenia baru
`<= open_date`), takže v okamihu rozhodnutia sú známe. To je rozdiel oproti „dôvodu
výstupu" alebo „ako hlboko šiel obchod proti nám" — tie sa vedia až potom a filter sa na
nich postaviť nedá.

Bar, v ktorom vstup nastal, sa **nepoužije**: pri vstupe na jeho otvorení alebo uprostred
neho (limitka s 1m detailom) jeho high/low/close ešte nie sú známe. Prvá verzia brala bar
s otváracím časom `<= open_date` a zmena samotnej vstupnej sviečky preklopila
`regime_align` zo „s trendom" na „proti trendu" (audit A9). Pri bežnom vstupe na otvorení
nasledujúceho baru je posledný použitý bar práve bar signálu — ten istý, na ktorého close
sa stratégia rozhodla.

### Čo sa meria

``regime_trend`` — **efektivita pohybu** (0 až 1)
    Čistá zmena ceny delená súčtom absolútnych zmien po baroch. Priamka hore dá 1,
    pílka okolo jednej úrovne dá takmer 0. Je to Kaufmanova efficiency ratio: robustnejšia
    než ADX a nepotrebuje ďalšie parametre.

``regime_vol`` — **volatilita voči normálu**
    ATR posledného uzavretého baru delené mediánom ATR za predošlých `VOL_DAYS` dní
    (rolling, len minulosť). 1,0 je typický stav, 2,0 dvojnásobne rozkolísaný. Je to
    náhrada za „pozri sa na VIX", ktorá funguje na každom trhu.

    Medián celej série (prvá verzia) niesol budúcnosť: pri zlievaní rokov je to len
    posun mierky a kvartily by sa nezmenili, ale číslo „2,0" by pri vstupe nebolo známe.
    Okno je to isté ako v AI vrstve (`tradebot.adapters.freqtrade.ai.VOL_DAYS`), aby model
    aj analytika merali volatilitu rovnako.

``regime_pos`` — **kde v rozsahu sa vstupovalo, v smere obchodu** (0 až 1)
    1 = cena už došla na koniec rozsahu v smere obchodu (long na vrchu, short na spodku),
    0 = na opačnom konci. Pri prerazení je to kľúčové: vstup na hrane rozsahu je iná vec
    než v jeho strede.

    Musí to byť **v smere obchodu**, nie surová poloha. Prvá verzia merala surovú polohu
    a na konfigurácii s polovicou shortov sa efekt vyrušil — pre short je spodok rozsahu
    to isté, čo pre long vrch, takže sa tie dve skupiny navzájom prekryli.

``regime_align`` — **s trendom, alebo proti nemu**
    Smer obchodu voči sklonu posledných N barov. Klasický filter „neobchoduj proti trendu"
    sa dá overiť práve týmto rozdelením.

Okno je predvolene 50 barov grafu — dosť na to, aby to bol režim, a nie posledný impulz
(ten meria `tester.character` piatimi barmi).
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any, Sequence

__all__ = ["LOOKBACK", "KEYS", "VOL_DAYS", "annotate", "vol_ratio_of"]

#: Koľko barov grafu tvorí „režim". Menej by bol impulz, viac už iný trh.
LOOKBACK = 50

#: Kľúče, ktoré `annotate` dopĺňa do obchodov.
KEYS = ("_regime_trend", "_regime_vol", "_regime_pos", "_regime_align")

#: Dĺžka ATR — tá istá ako v jadre (`tradebot.core.history`, Pine `ta.atr(14)`).
ATR_LEN = 14

#: „Normálna" volatilita = medián ATR za toľkoto **predošlých** dní. Rovnaké ako
#: `tradebot.adapters.freqtrade.ai.VOL_DAYS` (test to stráži); odtiaľ sa neimportuje,
#: lebo ten modul ťahá Freqtrade a analytika ho inak nepotrebuje.
VOL_DAYS = 7


def _dt_ms(value: Any) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _atr_series(high, low, close):
    """Wilderov ATR pre celý rad."""
    import numpy as np

    prev = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    atr = np.empty_like(tr)
    atr[:ATR_LEN] = tr[:ATR_LEN].mean() if len(tr) >= ATR_LEN else tr.mean()
    alfa = 1.0 / ATR_LEN
    for i in range(ATR_LEN, len(tr)):
        atr[i] = atr[i - 1] * (1 - alfa) + tr[i] * alfa
    return atr


def _tf_ms(timeframe: str, ts) -> int:
    """Dĺžka baru v ms — z názvu TF, pri neznámom z najčastejšieho rozostupu časov."""
    import numpy as np

    from tradebot.core.candles import timeframe_minutes

    try:
        return timeframe_minutes(timeframe) * 60_000
    except (ValueError, TypeError):
        kroky = np.diff(np.asarray(ts[:1000], dtype=np.int64))
        kroky = kroky[kroky > 0]
        return int(np.median(kroky)) if len(kroky) else 60_000


def vol_bars(timeframe: str) -> int:
    """Počet barov vo `VOL_DAYS` dňoch na danom TF, najmenej dĺžka ATR (ako v AI vrstve)."""
    from tradebot.core.candles import timeframe_minutes

    try:
        minut = max(1, timeframe_minutes(timeframe))
    except (ValueError, TypeError):
        minut = 3
    return max(ATR_LEN, int(VOL_DAYS * 1440 / minut))


def vol_ratio_of(cols, window: int):
    """ATR každého baru delené rolling mediánom ATR po ten bar vrátane — len minulosť.

    Rozbeh ATR (prvých `ATR_LEN` barov) sa do mediánu nepočíta; kým nie je aspoň
    `ATR_LEN` hodnôt, pomer je NaN a `annotate` volatilitu nevyplní.
    """
    import numpy as np
    import pandas as pd

    atr = _atr_series(cols["high"], cols["low"], cols["close"])
    zaklad = pd.Series(atr, dtype=float)
    zaklad.iloc[:ATR_LEN] = np.nan
    typicky = zaklad.rolling(window, min_periods=ATR_LEN).median().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(typicky > 0, atr / typicky, np.nan)


@lru_cache(maxsize=8)
def _vol_cached(pair: str, timeframe: str, mtime_ns: int):
    """Pomer volatility pre celú sériu — raz na (pár, TF, verzia súboru), nie na každý beh.

    Wilderov ATR je rekurzívny cyklus v Pythone nad 1,2M barmi (~0,3 s) a rolling medián
    ďalších ~0,7 s; analytika nad štyridsiatimi behmi by to bez cache počítala
    štyridsaťkrát.
    """
    from .webapp.chart import series

    return vol_ratio_of(series(pair, timeframe)[1], vol_bars(timeframe))


def annotate(trades: Sequence[dict[str, Any]], pair: str, timeframe: str,
             lookback: int = LOOKBACK) -> list[dict[str, Any]]:
    """Doplní obchodom stav trhu pri vstupe. Vracia ten istý zoznam (mení ho na mieste).

    Bez sviečok páru sa nedoplní nič a obchody ostanú, aké boli — analytika si potom tie
    vlastnosti jednoducho nevšimne, namiesto toho, aby ukázala vymyslené čísla. Obchody,
    ktoré stav trhu už nesú, sa preskočia — volanie je idempotentné.
    """
    import numpy as np

    from .webapp.chart import pair_file, series

    out = list(trades)
    todo = [t for t in out if not all(k in t for k in KEYS)]
    if not pair or not todo:
        return out
    try:
        ts, cols = series(pair, timeframe)
    except (FileNotFoundError, ValueError):
        return out
    # Cache len pri skutočnom súbore (kľúč je jeho verzia); séria podstrčená inak
    # (testy, pamäť) sa počíta priamo, aby cache nevrátila cudzie čísla.
    try:
        mtime = pair_file(pair, timeframe).stat().st_mtime_ns
    except (OSError, ValueError):
        mtime = None
    if len(ts) < lookback + ATR_LEN + 2:
        return out
    vol = (_vol_cached(pair, timeframe, mtime) if mtime is not None
           else vol_ratio_of(cols, vol_bars(timeframe)))

    high, low, close = cols["high"], cols["low"], cols["close"]
    # Bar je známy až po zatvorení: berie sa posledný bar so zatvorením `<= open_date`,
    # nie bar, v ktorom vstup nastal (jeho high/low/close sú v tej chvíli budúcnosť).
    dlzka_baru = _tf_ms(timeframe, ts)

    for t in todo:
        cas = _dt_ms(t.get("open_date"))
        if cas is None:
            continue
        i = int(np.searchsorted(ts, cas - dlzka_baru, side="right")) - 1
        if i < lookback:
            continue
        okno = slice(i - lookback, i + 1)
        c = close[okno]

        # Efektivita pohybu: priamka dá 1, pílka okolo jednej úrovne takmer 0.
        kroky = float(np.abs(np.diff(c)).sum())
        t["_regime_trend"] = round(abs(float(c[-1] - c[0])) / kroky, 4) if kroky > 0 else 0.0

        if np.isfinite(vol[i]):
            t["_regime_vol"] = round(float(vol[i]), 3)

        smer = -1.0 if t.get("is_short") else 1.0

        hi, lo = float(high[okno].max()), float(low[okno].min())
        if hi > lo:
            podiel = (float(close[i]) - lo) / (hi - lo)
            # V smere obchodu: pre short je spodok rozsahu to iste, co pre long vrch.
            t["_regime_pos"] = round(podiel if smer > 0 else 1.0 - podiel, 4)

        # Sklon okna voči smeru obchodu. Rovnaké znamienko = s trendom.
        sklon = float(c[-1] - c[0])
        t["_regime_align"] = "s trendom" if sklon * smer > 0 else "proti trendu"
    return out
