"""Slabne edge? Posledné obdobie proti vlastnej minulosti.

### Na akú otázku odpovedá
Backtest za päť rokov dá jedno číslo za celé obdobie. To číslo ale môže vzniknúť dvoma
úplne rôznymi spôsobmi: buď stratégia zarábala rovnomerne, alebo zarobila v rokoch
2021-2023 a odvtedy stojí. Rozdiel je pre rozhodnutie „ideme s tým naostro“ zásadný —
a zo súhrnu behu ho vidieť nie je.

Edge sa opotrebúva: čo fungovalo, kým to robilo málo ľudí, prestane fungovať, keď sa to
rozšíri, keď sa zmení mikroštruktúra trhu alebo keď sa zmení režim. Toto je test, ktorý sa
pýta priamo na to: **je posledné obdobie ešte v medziach toho, čo tá istá stratégia
robievala?**

### Prečo sa to nedá porovnať s celkovým číslom
Toto je miesto, kde sa dá ľahko pomýliť. Posledná štvrtina má rádovo štyrikrát menej
obchodov než celok, takže je aj **prirodzene rozkolísanejšia**. Porovnať jej break-even
s break-evenom celku (alebo s úzkym intervalom okolo neho) by znamenalo hlásiť úpadok
zakaždým, keď je posledné obdobie zhodou okolností slabšie — čo je asi v polovici prípadov.

Správna referencia je iná: **ako by vyzeral úsek tej istej dĺžky, keby sa edge nemenil.**
Z celej histórie sa preto blokovým bootstrapom (`tester.montecarlo`) natiahnu vzorky
presne takej veľkosti, akú má testované obdobie, a z nich vznikne rozdelenie. Až voči nemu
sa namerané číslo porovnáva. Blok drží série za sebou idúcich strát pokope — bez neho by
bolo rozdelenie príliš úzke a test by hlásil úpadok pričasto.

### Čo ešte test sleduje
Okrem posledného obdobia sú tu **všetky** obdobia s percentilom, takže je vidieť, či ide
o jednorazový výpadok alebo o klesajúci rad. A počet obchodov na mesiac: keď stratégia
prestane nachádzať signály, je to úpadok rovnako ako klesajúci break-even, len sa
v break-evene neprejaví.

### Čo to NErieši
**Nerozlíši úpadok edge od nepriaznivého režimu.** Slabá posledná štvrtina môže znamenať,
že stratégia dohorela, alebo že trh bol práve v režime, ktorý jej nesvedčí — z tých istých
dát sa to oddeliť nedá. Odpoveď na to je `tester.regime` (v akom stave bol trh) a čas.

**Percentil platí pre posledné obdobie, lebo to bolo vybraté vopred.** Percentily ostatných
období sú opis, nie test: keď sa pozerá na štyri obdobia, jedno pod piatym percentilom
vyjde náhodou zhruba v jednom prípade z piatich.

**Nič to nehovorí o budúcnosti.** „Drží“ znamená, že úpadok v dátach vidieť nie je — nie
že nepríde.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from .montecarlo import _chunks, block_size, per_trade

__all__ = [
    "PARTS", "MIN_TRADES", "MIN_PART_TRADES", "CONF", "Period", "Decay", "analyze", "report",
]

#: Na koľko období sa história delí. Štyri sú kompromis: menej období nezachytí priebeh,
#: viac ich má každé tak málo obchodov, že sa nedá povedať nič.
PARTS = 4

#: Pod týmto počtom obchodov nemá delenie na obdobia zmysel — jediný poctivý záver
#: je „málo dát“.
MIN_TRADES = 60

#: A toľko musí mať samotné testované obdobie.
MIN_PART_TRADES = 12

#: Šírka intervalu v percentách. 90 % znamená hranice na 5. a 95. percentile.
CONF = 90.0

#: Koľko vzoriek sa ťahá. Pri 2000 je piaty percentil určený na desatinu percenta presne.
ITERATIONS = 2000

#: Dĺžka bloku — tá istá úvaha ako v Monte Carle: desať obchodov je zhruba jeden režim.
BLOCK = 10


@dataclass(frozen=True)
class Period:
    """Jedno obdobie histórie."""

    label: str
    start: str
    end: str
    trades: int
    break_even_pct: float | None
    winrate: float | None
    #: obchodov na mesiac — klesajúci počet signálov je úpadok tiež
    per_month: float | None
    #: kde v rozdelení vzoriek tej istej veľkosti obdobie leží (0-100)
    percentile: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Decay:
    """Výsledok testu."""

    periods: list[Period] = field(default_factory=list)
    trades: int = 0
    whole_break_even: float | None = None
    #: hranice intervalu pre úsek veľkosti posledného obdobia
    lo: float | None = None
    hi: float | None = None
    median: float | None = None
    sd: float | None = None
    #: sklon break-evenu naprieč obdobiami (na jedno obdobie)
    slope: float | None = None
    verdict: str = ""
    note: str = ""

    @property
    def last(self) -> Period | None:
        return self.periods[-1] if self.periods else None

    def to_dict(self) -> dict[str, Any]:
        out = {k: v for k, v in self.__dict__.items() if k != "periods"}
        out["periods"] = [p.to_dict() for p in self.periods]
        return out


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        out = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo else out.replace(tzinfo=timezone.utc)


def _break_even(trades: Sequence[dict[str, Any]]) -> float | None:
    from .analytics import break_even_pct

    return break_even_pct(trades)


def _winrate(trades: Sequence[dict[str, Any]]) -> float | None:
    if not trades:
        return None
    return round(sum(1 for t in trades if float(t.get("profit_abs") or 0) > 0) / len(trades) * 100, 2)


def _split_time(trades: list[tuple[datetime, dict[str, Any]]],
                parts: int) -> list[tuple[datetime, datetime, list[dict[str, Any]]]]:
    """Rovnako dlhé kalendárne úseky. Úpadok je kalendárny jav, nie poradový."""
    od, do = trades[0][0], trades[-1][0]
    span = (do - od) or timedelta(seconds=1)
    krok = span / parts
    out = []
    for i in range(parts):
        a = od + krok * i
        b = do if i == parts - 1 else od + krok * (i + 1)
        posledny = i == parts - 1
        vyber = [t for cas, t in trades if a <= cas <= b] if posledny else \
                [t for cas, t in trades if a <= cas < b]
        out.append((a, b, vyber))
    return out


def _split_count(trades: list[tuple[datetime, dict[str, Any]]],
                 parts: int) -> list[tuple[datetime, datetime, list[dict[str, Any]]]]:
    """Rovnako početné úseky. Pre riedke obchody, kde by kalendárny úsek ostal prázdny."""
    n = len(trades)
    out = []
    for i in range(parts):
        a, b = n * i // parts, n * (i + 1) // parts
        kus = trades[a:b]
        if not kus:
            continue
        out.append((kus[0][0], kus[-1][0], [t for _, t in kus]))
    return out


def _draw(rng, chunk: int, pop: int, size: int, block: int):
    """Indexy `chunk x size` z populácie `pop` — cyklický blokový bootstrap.

    Oproti `montecarlo._draw` sa tu líši dĺžka vzorky od veľkosti populácie: ťahá sa
    **krátky úsek z dlhej histórie**, a práve to je celý zmysel testu.
    """
    import numpy as np

    if block <= 1:
        return rng.integers(0, pop, size=(chunk, size))
    blocks = -(-size // block)
    starts = rng.integers(0, pop, size=(chunk, blocks, 1))
    idx = (starts + np.arange(block)) % pop
    return idx.reshape(chunk, blocks * block)[:, :size]


def _sample(trades: Sequence[dict[str, Any]], size: int, iterations: int,
            block: int, seed: int):
    """Rozdelenie break-evenu úsekov dĺžky `size` z celej histórie (blokový bootstrap)."""
    import numpy as np

    gross, volume = per_trade(list(trades))
    n = len(gross)
    rng = np.random.default_rng(seed)
    blok = block_size(block, size)
    kusy = []
    for chunk in _chunks(iterations, size):
        # Indexy sa ťahajú z celej histórie, nie z okna — presne to je tá nulová
        # hypotéza: „edge sa v čase nemení, takže na poradí nezáleží“.
        idx = _draw(rng, chunk, n, size, blok)
        g = gross[idx].sum(axis=1)
        v = volume[idx].sum(axis=1)
        kusy.append(np.where(v > 0, g / np.where(v > 0, v, 1.0) * 100.0, np.nan))
    vzorka = np.concatenate(kusy)
    return vzorka[~np.isnan(vzorka)]


def analyze(trades: Sequence[dict[str, Any]], *, parts: int = PARTS, by: str = "time",
            iterations: int = ITERATIONS, block: int = BLOCK, seed: int = 12345,
            conf: float = CONF) -> Decay:
    """Rozdelí históriu na obdobia a porovná posledné s tým, čo dokáže vyrobiť náhoda.

    `by="time"` delí kalendár na rovnaké úseky (default — úpadok je kalendárny jav),
    `by="count"` na rovnako početné (keď sú obchody riedke a úsek by ostal prázdny).
    """
    import numpy as np

    out = Decay()
    s_casom = sorted(((c, t) for t in trades if (c := _dt(t.get("open_date")))),
                     key=lambda x: x[0])
    out.trades = len(s_casom)
    if len(s_casom) < 2:
        out.verdict = "MALO DAT"
        out.note = "obchody nemajú dátumy, alebo ich je príliš málo na rozdelenie v čase"
        return out

    cele = [t for _, t in s_casom]
    out.whole_break_even = _break_even(cele)

    useky = _split_time(s_casom, parts) if by != "count" else _split_count(s_casom, parts)
    for a, b, kus in useky:
        mesiacov = max((b - a).days / 30.44, 0.01)
        out.periods.append(Period(
            label=f"{a:%Y-%m} - {b:%Y-%m}", start=a.isoformat(), end=b.isoformat(),
            trades=len(kus), break_even_pct=_break_even(kus), winrate=_winrate(kus),
            per_month=round(len(kus) / mesiacov, 2)))

    posledne = out.periods[-1]
    if out.trades < MIN_TRADES or posledne.trades < MIN_PART_TRADES:
        out.verdict = "MALO DAT"
        out.note = (f"celkom {out.trades} obchodov, v poslednom období {posledne.trades} — "
                    f"na rozlíšenie úpadku od bežného rozptylu treba aspoň {MIN_TRADES} "
                    f"a {MIN_PART_TRADES}. Pridaj okná alebo trhy.")
        return out

    vzorka = _sample(cele, posledne.trades, iterations, block, seed)
    if not len(vzorka):
        out.verdict = "MALO DAT"
        out.note = "z obchodov sa nedal spočítať objem, takže break-even vzoriek nevyšiel"
        return out

    lo_q, hi_q = (100.0 - conf) / 2.0, 100.0 - (100.0 - conf) / 2.0
    out.lo, out.hi = float(np.percentile(vzorka, lo_q)), float(np.percentile(vzorka, hi_q))
    out.median, out.sd = float(np.median(vzorka)), float(np.std(vzorka))

    # Percentil má zmysel pre každé obdobie, ale testom je len to posledné — ostatné sú
    # opis. Každé sa porovnáva s rozdelením VLASTNEJ veľkosti, inak by kratšie obdobie
    # vychádzalo systematicky extrémnejšie len preto, že je kratšie.
    for i, p in enumerate(out.periods):
        if p.break_even_pct is None or p.trades < 3:
            continue
        v = vzorka if p is posledne else _sample(cele, p.trades, max(400, iterations // 4),
                                                 block, seed + i)
        if len(v):
            percentil = round(float((v < p.break_even_pct).mean() * 100), 1)
            out.periods[i] = Period(**{**p.to_dict(), "percentile": percentil})

    hodnoty = [p.break_even_pct for p in out.periods if p.break_even_pct is not None]
    if len(hodnoty) >= 3:
        x = np.arange(len(hodnoty), dtype=float)
        out.slope = round(float(np.polyfit(x, np.asarray(hodnoty), 1)[0]), 6)

    out.verdict, out.note = _verdict(out, conf)
    return out


def _verdict(d: Decay, conf: float) -> tuple[str, str]:
    p = d.last
    assert p is not None and p.percentile is not None and d.lo is not None and d.hi is not None
    pocet = len(d.periods)

    # Klesajúci rad je silnejší dôkaz než jedno slabé obdobie: aby vyšiel náhodou, musia
    # sa zoradiť všetky obdobia, nie len posledné.
    hodnoty = [q.break_even_pct for q in d.periods if q.break_even_pct is not None]
    klesa = len(hodnoty) >= 3 and all(a > b for a, b in zip(hodnoty, hodnoty[1:]))
    # Pokles počtu signálov je úpadok tiež, aj keď break-even drží.
    frekvencie = [q.per_month for q in d.periods if q.per_month]
    riedne = (len(frekvencie) >= 2 and frekvencie[0] > 0
              and frekvencie[-1] < frekvencie[0] * 0.5)

    if p.percentile < (100.0 - conf) / 2.0:
        znacka = "SLABNE"
        veta = (f"SLABNE: posledné obdobie ({p.label}) má break-even {p.break_even_pct:+.4f} %, "
                f"pod dolnou hranicou {d.lo:+.4f} % — úsek tejto dĺžky by taký zlý vyšiel len "
                f"v {p.percentile:.0f} % prípadov, keby sa edge nemenil. Skôr než to vypneš: "
                f"pozri `tester.regime`, či to nie je len režimom trhu.")
    elif p.percentile > 100.0 - (100.0 - conf) / 2.0:
        znacka = "ZLEPSUJE SA"
        veta = (f"ZLEPSUJE SA: posledné obdobie ({p.label}) je nad hornou hranicou "
                f"{d.hi:+.4f} %. Pozor na opačnú chybu — dôvod zvyšovať riziko to nie je, "
                f"rovnako dobre to môže byť priaznivý režim.")
    elif klesa:
        znacka = "POZOR NA TREND"
        veta = (f"POZOR NA TREND: každé z {pocet} období je horšie než predchádzajúce "
                f"(sklon {d.slope:+.4f} na obdobie). Posledné je ešte v medziach "
                f"({p.percentile:.0f}. percentil), takže test úpadok nepotvrdzuje — ale rad "
                f"sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.")
    else:
        znacka = "DRZI"
        veta = (f"DRZI: posledné obdobie ({p.label}) je na {p.percentile:.0f}. percentile, "
                f"teda v medziach {d.lo:+.4f} až {d.hi:+.4f} %, ktoré tá istá stratégia vyrobí "
                f"sama od seba. Úpadok v dátach vidieť nie je.")
    if riedne:
        veta += (f" Signálov pritom ubudlo: z {frekvencie[0]:g} na {frekvencie[-1]:g} obchodov "
                 f"za mesiac. To je úpadok tiež, len v break-evene ho vidieť nie je.")
    return znacka, veta


def report(d: Decay, label: str = "") -> str:
    """Textový výpis pre CLI."""
    riadky = [("=== Slabne edge? " + label).rstrip() + " ==="]
    if d.whole_break_even is not None:
        riadky.append(f"celok: {d.trades} obchodov, break-even {d.whole_break_even:+.4f} %")
    if d.lo is not None:
        riadky.append(f"usek velkosti posledneho obdobia vyjde medzi {d.lo:+.4f} a "
                      f"{d.hi:+.4f} % (median {d.median:+.4f}, sigma {d.sd:.4f})")
    riadky.append("")
    riadky.append(f"{'obdobie':<20}{'obch.':>7}{'/mes.':>8}{'WR %':>8}"
                  f"{'break-even':>13}{'percentil':>11}")
    for p in d.periods:
        be = "-" if p.break_even_pct is None else f"{p.break_even_pct:+.4f}"
        pc = "-" if p.percentile is None else f"{p.percentile:.0f}"
        wr = "-" if p.winrate is None else f"{p.winrate:.1f}"
        riadky.append(f"{p.label:<20}{p.trades:>7}{(p.per_month or 0):>8.2f}{wr:>8}"
                      f"{be:>13}{pc:>11}")
    riadky.append("")
    riadky.append(d.note or d.verdict)
    return "\n".join(riadky)
