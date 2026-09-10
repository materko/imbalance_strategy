"""Je ten edge odlíšiteľný od náhody? Porovnanie s náhodným vstupom za rovnakých pravidiel.

### Na akú otázku odpovedá
Break-even 0,107 % je veľa alebo málo? Bez referencie to nie je odpoveď, ale číslo — a je
to tá najdôležitejšia otázka zo všetkých. Dá sa na ňu odpovedať len tak, že sa stratégia
porovná s **niečím, čo edge určite nemá**.

Postaví sa preto „hlúpa" verzia tej istej stratégie: obchoduje rovnako často, rovnakým
smerom, s rovnakým stop lossom aj take profitom a drží rovnako dlho — **len si nevyberá,
kedy vstúpiť**. Takých behov sa spraví tisíc a z nich vznikne rozdelenie, s ktorým sa
skutočný výsledok porovná::

    break-even 0.1071 % oproti nahode 0.0041 % +- 0.0380  ->  2.7 sigma, percentil 99.4
    Edge je odlisitelny od nahody.

### Čo presne sa zachováva
Všetko okrem rozhodnutia **kedy**. Náhodný beh dostane rovnaký počet obchodov, rovnaký
pomer long/short, vzdialenosť stopu a RR vylosované zo skutočných obchodov (teda ten istý
risk management vrátane toho, či je SL tesný alebo široký) a rovnaký strop na dĺžku
držania. Neporovnáva sa teda stratégia s „ničím", ale s tou istou stratégiou bez výberu
vstupu — a rozdiel je presne to, čo výber vstupu prináša.

### Dve rôzne náhody a prečo na tom záleží
``anytime``
    Vstupy kedykoľvek v okne. Porovnanie hovorí o celej stratégii vrátane toho, **kedy**
    obchoduje.
``session``
    Vstupy sa losujú tak, aby mali **rovnaké rozdelenie hodín** ako skutočné obchody.
    Porovnanie potom hovorí len o tom, čo stratégia robí **vnútri** svojho okna.

Rozdiel medzi tými dvoma číslami je hodnota samotného výberu času. Keď je stratégia lepšia
než ``anytime``, ale nie než ``session``, celý jej edge je v tom, že obchoduje v NY seanse —
a to sa dá mať aj bez nej.

### Prečo sa simuluje na 1m sviečkach
Vnútri baru nevieme, či prišiel skôr stop alebo take profit. Pri 3m baroch je tá
nevedomosť veľká a **vychyľuje referenčný bod**: keby sa pri zhode počítal stop, náhoda
by vychádzala horšie, než je, a edge stratégie by tým vyzeral lepší. Simulácia preto beží
na 1m sviečkach — presne z toho istého dôvodu, pre ktorý sa každý backtest púšťa
s ``--timeframe-detail 1m``. Zvyšná nejednoznačnosť vnútri jednej minúty je malá a testy
strážia, že náhoda vychádza na nulu.

### Prečo v jednotkovej veľkosti
Skutočné obchody majú rôzne veľkosti pozície podľa rizika. Keby náhodné mali veľkosť 1
a skutočné rôznu, porovnávali by sa dve rôzne veci. Test preto počíta **obe strany**
s veľkosťou 1; break-even je podiel, takže mu jednotková veľkosť nevadí — len sa musí
použiť rovnako na oboch stranách.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

__all__ = [
    "DEFAULT_ITERATIONS", "MIN_TRADES", "NULLS", "Result",
    "plan_from_trades", "simulate", "compare", "report",
]

#: Koľko náhodných behov. Tisíc stačí na percentil aj sigmu a trvá sekundy.
DEFAULT_ITERATIONS = 1000

#: Pod týmto počtom obchodov je rozdelenie náhody také široké, že jediný poctivý záver
#: je „málo dát" — a presne to má výpis povedať nahlas.
MIN_TRADES = 15

#: Ako sa losuje čas vstupu.
NULLS = {
    "anytime": "vstupy kedykoľvek v okne",
    "session": "vstupy v tých istých hodinách, v akých obchoduje stratégia",
}

#: Strop na dĺžku držania náhodného obchodu, keď sa nedá odvodiť zo skutočných.
FALLBACK_BARS = 200


@dataclass
class Result:
    """Výsledok porovnania s náhodou."""

    metric: str = "break_even_pct"
    observed: float | None = None
    trades: int = 0
    iterations: int = 0
    null: str = "anytime"
    mean: float | None = None
    sd: float | None = None
    percentile: float | None = None
    sigma: float | None = None
    lo: float | None = None
    hi: float | None = None
    sample: list[float] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {k: v for k, v in self.__dict__.items() if k != "sample"}
        data["histogram"] = _histogram(self.sample)
        data["verdict"] = self.verdict
        data["null_note"] = NULLS.get(self.null, "")
        return data

    @property
    def verdict(self) -> str:
        """Jedna veta — a pri malom počte obchodov predovšetkým to, že je ich málo."""
        if self.observed is None or self.sigma is None:
            return "Porovnanie sa nedalo spocitat."
        malo = (f" POZOR: {self.trades} obchodov je na tento test malo, rozdelenie nahody je "
                f"siroke a rozdiel by musel byt velky, aby nieco znamenal."
                if self.trades < MIN_TRADES else "")
        if self.sigma >= 2.0:
            return (f"Edge je odlisitelny od nahody ({self.sigma:.1f} sigma, percentil "
                    f"{self.percentile:.1f}).{malo}")
        if self.sigma >= 1.0:
            return (f"Naznak, ale nie dokaz ({self.sigma:.1f} sigma, percentil "
                    f"{self.percentile:.1f}). Take rozdiely nahoda robi bezne.{malo}")
        if self.sigma <= -1.0:
            return (f"HORSIE nez nahoda ({self.sigma:.1f} sigma). Nahodny vstup za tych istych "
                    f"pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.{malo}")
        return (f"Neodlisitelne od nahody ({self.sigma:+.1f} sigma, percentil "
                f"{self.percentile:.1f}). Vyber vstupu k vysledku nepridava nic, co by sa "
                f"nedalo dostat aj hodom mincou.{malo}")


# --------------------------------------------------------------------------- #
# plán obchodu zo skutočných obchodov
# --------------------------------------------------------------------------- #


def _dt_ms(value: Any) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def plan_from_trades(trades: Sequence[dict[str, Any]], minutes: int) -> dict[str, Any]:
    """Z reálnych obchodov vytiahne to, čo má náhodný beh zachovať.

    Vzdialenosť stopu je **podiel ceny**, nie absolútna hodnota — inak by sa plán nedal
    použiť na inom mieste grafu, kde je cena iná. Berie sa z plánu obchodu (kresby SL/TP),
    a keď ten nie je, aspoň zo skutočne dosiahnutého stopu.
    """
    import numpy as np

    sl: list[float] = []
    rr: list[float] = []
    smery: list[int] = []
    bary: list[int] = []
    hodiny: list[int] = []
    for t in trades:
        smery.append(-1 if t.get("is_short") else 1)
        cas = _dt_ms(t.get("open_date"))
        if cas is not None:
            hodiny.append(datetime.fromtimestamp(cas / 1000, tz=timezone.utc).hour)
        trvanie = t.get("trade_duration")
        if trvanie:
            bary.append(max(1, int(float(trvanie) / max(minutes, 1))))
        podiel = t.get("_sl_pct")
        if podiel is None:
            open_rate = float(t.get("open_rate") or 0)
            close_rate = float(t.get("close_rate") or 0)
            if open_rate and t.get("exit_reason") == "stop_loss":
                podiel = abs(close_rate - open_rate) / open_rate * 100.0
        if podiel:
            sl.append(float(podiel) / 100.0)
            rr.append(float(t.get("_rr_planned") or 1.0))
    return {
        "count": len(trades),
        "sl_frac": np.array(sl or [0.005]),
        "rr": np.array(rr or [2.0]),
        "long_share": float(np.mean([s > 0 for s in smery])) if smery else 1.0,
        "max_bars": int(np.percentile(bary, 90)) if bary else FALLBACK_BARS,
        "hours": np.array(hodiny, dtype=int) if hodiny else np.arange(24),
    }


# --------------------------------------------------------------------------- #
# simulácia
# --------------------------------------------------------------------------- #


def _exits(high, low, close, idx, smery, sl, tp, max_bars: int):
    """Ceny výstupov pre celý náhodný beh naraz.

    Po jednom obchode to bolo pár minút na tisíc obchodov a štyristo opakovaní — do
    stránky sa to takto dať nedá. Trik je, že okno každého obchodu má rovnakú dĺžku, takže
    sa dá postaviť matica `obchody x bary` a hľadať prvý zásah cez `argmax` naraz.

    Keď sa do tej istej minúty zmestí SL aj TP, počíta sa **SL**. Je to zvyšková
    nejednoznačnosť: na 1m sviečkach je zriedkavá, ale nie nulová. Pozor, tu je „opatrné"
    naopak než pri backteste stratégie — podhodnotená náhoda posunie referenčný bod nadol
    a edge stratégie tým vyzerá lepší. Preto sa simuluje na 1m a nie na TF stratégie.
    """
    import numpy as np

    okno = idx[:, None] + np.arange(1, max_bars + 1)[None, :]
    okno = np.minimum(okno, len(close) - 1)
    h, l = high[okno], low[okno]
    dlho = smery[:, None] > 0

    zasah_sl = np.where(dlho, l <= sl[:, None], h >= sl[:, None])
    zasah_tp = np.where(dlho, h >= tp[:, None], l <= tp[:, None])

    # argmax vráti 0 aj keď nie je žiadny zásah — preto sa musí pýtať aj na `any`.
    ma_sl, ma_tp = zasah_sl.any(axis=1), zasah_tp.any(axis=1)
    i_sl = np.where(ma_sl, zasah_sl.argmax(axis=1), max_bars + 1)
    i_tp = np.where(ma_tp, zasah_tp.argmax(axis=1), max_bars + 1)

    posledny = close[okno[:, -1]]
    out = np.where(ma_sl & (i_sl <= i_tp), sl, np.where(ma_tp, tp, posledny))
    return out


def simulate(candles: tuple, plan: dict[str, Any], *, iterations: int = DEFAULT_ITERATIONS,
             null: str = "anytime", seed: int = 12345) -> list[float]:
    """`iterations` náhodných behov; vráti ich break-even poplatky (% na stranu)."""
    import numpy as np

    ts, high, low, close, hodiny = candles
    n = len(close)
    rng = np.random.default_rng(seed)
    pocet = int(plan["count"])
    max_bars = int(plan["max_bars"])
    if n <= max_bars + 2 or pocet <= 0:
        return []

    # `session`: losuje sa len z barov, ktoré padnú do tých istých hodín, v akých
    # stratégia obchoduje. Inak by sa meral aj výber času, nie len výber vstupu.
    if null == "session":
        povolene = np.flatnonzero(np.isin(hodiny[: n - max_bars - 1], np.unique(plan["hours"])))
        if len(povolene) < pocet:
            povolene = np.arange(n - max_bars - 1)
    else:
        povolene = np.arange(n - max_bars - 1)

    out: list[float] = []
    for _ in range(iterations):
        idx = rng.choice(povolene, size=pocet, replace=True)
        smery = np.where(rng.random(pocet) < plan["long_share"], 1, -1)
        sl_frac = rng.choice(plan["sl_frac"], size=pocet, replace=True)
        rr = rng.choice(plan["rr"], size=pocet, replace=True)

        entry = close[idx]
        sl = entry * (1 - smery * sl_frac)
        tp = entry * (1 + smery * sl_frac * rr)
        exit_price = _exits(high, low, close, idx, smery, sl, tp, max_bars)

        gross = float(((exit_price - entry) * smery).sum())
        volume = float((entry + exit_price).sum())
        if volume > 0:
            out.append(gross / volume * 100.0)
    return out


def _histogram(sample: Sequence[float], bins: int = 30) -> dict[str, list[float]]:
    if not sample:
        return {"edges": [], "counts": []}
    import numpy as np

    counts, edges = np.histogram(np.asarray(sample, dtype=float), bins=bins)
    return {"edges": [round(float(e), 6) for e in edges], "counts": [int(c) for c in counts]}


# --------------------------------------------------------------------------- #
# porovnanie
# --------------------------------------------------------------------------- #


def compare(trades: Sequence[dict[str, Any]], *, pair: str, timeframe: str,
            timerange: str | None = None, iterations: int = DEFAULT_ITERATIONS,
            null: str = "anytime", seed: int = 12345) -> Result:
    """Porovná skutočný break-even s rozdelením náhodných behov."""
    import numpy as np

    from tradebot.core.candles import timeframe_minutes

    from . import analytics as an
    from .webapp.chart import series

    if null not in NULLS:
        raise ValueError(f"neznáma náhoda {null!r}; známe: {', '.join(NULLS)}")
    out = Result(iterations=iterations, null=null, trades=len(trades))
    if not trades:
        out.note = "žiadne obchody"
        return out

    # Obe strany v jednotkovej veľkosti - inak by sa porovnával aj sizing, nie len vstup.
    jednotkove = [{**t, "amount": 1.0} for t in trades]
    out.observed = an.break_even_pct(jednotkove)

    # 1m, nie TF strategie: vnutri baru nevieme poradie SL/TP a pri 3m by tá nevedomost
    # posunula referencny bod. To iste robi kazdy nas backtest cez --timeframe-detail 1m.
    try:
        ts, cols = series(pair, "1m")
    except (FileNotFoundError, ValueError) as exc:
        out.note = str(exc)
        return out
    if timerange:
        try:
            a, b = timerange.split("-")
            od = int(datetime.strptime(a, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
            do = int(datetime.strptime(b, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
            i, j = int(np.searchsorted(ts, od)), int(np.searchsorted(ts, do))
            ts, cols = ts[i:j], {k: v[i:j] for k, v in cols.items()}
        except ValueError:
            pass

    hodiny = ((ts // 3_600_000) % 24).astype(int)
    # Plán drží dĺžku držania v baroch TF stratégie; simulácia beží na minútach.
    plan = plan_from_trades(trades, timeframe_minutes(timeframe))
    plan["max_bars"] = max(1, int(plan["max_bars"] * timeframe_minutes(timeframe)))
    vzorka = simulate((ts, cols["high"], cols["low"], cols["close"], hodiny), plan,
                      iterations=iterations, null=null, seed=seed)
    if not vzorka:
        out.note = "náhodné behy sa nedali zostaviť (málo sviečok alebo obchodov)"
        return out

    pole = np.asarray(vzorka, dtype=float)
    out.sample = [float(x) for x in pole]
    out.mean = round(float(pole.mean()), 6)
    out.sd = round(float(pole.std(ddof=1)), 6)
    out.lo = round(float(np.percentile(pole, 5)), 6)
    out.hi = round(float(np.percentile(pole, 95)), 6)
    out.percentile = round(float((pole < out.observed).mean() * 100), 2)
    out.sigma = round((out.observed - out.mean) / out.sd, 2) if out.sd > 0 else None
    return out


def report(result: Result, label: str = "") -> str:
    """Výpis — ASCII, konzola na Windows beží v cp1250."""
    if result.observed is None or result.sigma is None:
        return f"porovnanie s nahodou sa nedalo spocitat: {result.note or '?'}"
    return "\n".join([
        f"=== test proti nahode{': ' + label if label else ''} ===",
        f"nahoda: {NULLS[result.null]}",
        "",
        f"{'obchodov':<26}{result.trades}",
        f"{'nahodnych behov':<26}{result.iterations}",
        f"{'break-even strategie':<26}{result.observed:.4f} %",
        f"{'break-even nahody':<26}{result.mean:.4f} % +- {result.sd:.4f}",
        f"{'5-95 % nahody':<26}{(result.lo if result.lo is not None else float('nan')):.4f} az "
        f"{(result.hi if result.hi is not None else float('nan')):.4f} %",
        f"{'percentil':<26}{result.percentile:.1f}",
        f"{'sigma':<26}{result.sigma:+.2f}",
        "",
        result.verdict,
    ])
