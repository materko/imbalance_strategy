"""Je víťaz hyperoptu plató, alebo osamelá špička? Okolie víťaza ako test robustnosti.

### Na akú otázku odpovedá
Hyperopt vráti jednu konfiguráciu: ``rrRatio 4,7``, ``slLookback 40``. To číslo ale
nehovorí nič o tom, či je to **stred niečoho**, alebo náhodná diera v šume. Rozdiel je
zásadný:

- **plató** — susedné hodnoty dávajú podobný výsledok. Optimalizátor našiel oblasť, kde
  stratégia funguje, a presná hodnota nie je kritická. Takú konfiguráciu možno používať.
- **špička** — susedia spadnú. Optimum drží len na tej jednej hodnote, teda je to tvar
  **toho okna**, nie stratégie. V ostrej prevádzke z toho nebude nič.

Rozdiel sa nedá vyčítať z čísla, len zmerať: víťazovi sa preberú susedia (o krok a o dva
kroky hore aj dole na každom ladenom parametri) a každý sa pustí ako obyčajný backtest na
tom istom okne.

### Ako sa rozhoduje, či susedia „držia"
Nie percentom — to by bola vymyslená hranica. Meradlom je **vlastný interval spoľahlivosti
víťaza** z Monte Carla (`tester.montecarlo`): keď sused padne dovnútra intervalu, ktorý
by víťaz dosiahol už len preskladaním vlastných obchodov, nie je od neho odlíšiteľný —
a to je presne definícia plató.

Z toho plynie aj poctivé priznanie, ktoré výpis robí sám: pri dvadsiatich obchodoch je ten
interval taký široký, že doň spadne skoro všetko. Vtedy test nehovorí „je to plató", ale
„na rozlíšenie je málo dát".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from . import sweep as sweep_mod

__all__ = [
    "STEPS", "Neighbour", "neighbours", "assess", "table",
]

#: O koľko krokov od víťaza sa skúša. Dva kroky stačia: keby optimum držalo len na
#: jednom kroku, je to špička už pri prvom susedovi.
STEPS = (-2, -1, 1, 2)

#: Keď plán krok nemá, berie sa toľkátina rozsahu.
FALLBACK_STEPS = 20


@dataclass(frozen=True)
class Neighbour:
    """Jedna susedná konfigurácia — mení sa vždy len jeden parameter."""

    param: str
    value: Any
    step: int

    @property
    def label(self) -> str:
        znak = "+" if self.step > 0 else ""
        return f"{self.param} {znak}{self.step}"


def _round_like(value: float, vzor: Any) -> Any:
    """Celočíselné pole musí zostať celé — inak ho config odmietne."""
    if isinstance(vzor, bool):
        return bool(value)
    if isinstance(vzor, int):
        return int(round(value))
    return round(float(value), 6)


def neighbours(knobs: dict[str, str], winner: dict[str, Any],
               steps: Sequence[int] = STEPS) -> list[Neighbour]:
    """Susedia víťaza — o `steps` krokov na každom ladenom parametri, po jednom.

    Mení sa vždy len jeden parameter: keby sa hýbali všetky naraz, nevedelo by sa, ktorý
    z nich výsledok drží. Hodnoty mimo rozsahu z plánu vypadnú — config by ich aj tak
    neprijal.
    """
    out: list[Neighbour] = []
    for name, spec in knobs.items():
        if name not in winner:
            continue
        try:
            rozsah = sweep_mod.to_knob(spec)
        except ValueError:
            continue
        stred = winner[name]
        if "choices" in rozsah:
            # Prepínač alebo enum: susedia sú ostatné možnosti, kroky nedávajú zmysel.
            for hodnota in rozsah["choices"]:
                if hodnota != stred:
                    out.append(Neighbour(name, hodnota, 1))
            continue
        if not isinstance(stred, (int, float)) or isinstance(stred, bool):
            continue
        low, high = float(rozsah["low"]), float(rozsah["high"])
        krok = float(rozsah.get("step") or (high - low) / FALLBACK_STEPS)
        if krok <= 0:
            continue
        videne = {stred}
        for k in steps:
            hodnota = _round_like(float(stred) + k * krok, stred)
            if hodnota in videne or not (low <= float(hodnota) <= high):
                continue
            videne.add(hodnota)
            out.append(Neighbour(name, hodnota, k))
    return out


# --------------------------------------------------------------------------- #
# vyhodnotenie
# --------------------------------------------------------------------------- #


@dataclass
class Assessment:
    """Výsledok testu okolia."""

    winner: float | None = None
    ci_lo: float | None = None
    ci_hi: float | None = None
    trades: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    by_param: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: rozpätie susedov (max - min) a jeho pomer k šírke intervalu víťaza
    spread: float | None = None
    spread_ratio: float | None = None
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _be(rec: dict[str, Any]) -> float | None:
    hodnota = (rec.get("result") or {}).get("break_even_pct")
    return None if hodnota is None else float(hodnota)


def assess(winner_record: dict[str, Any], neighbour_records: Sequence[dict[str, Any]],
           ci: tuple[float | None, float | None] = (None, None),
           min_trades: int = 10) -> Assessment:
    """Porovná susedov s víťazom a jeho intervalom spoľahlivosti."""
    out = Assessment(winner=_be(winner_record), ci_lo=ci[0], ci_hi=ci[1],
                     trades=int((winner_record.get("result") or {}).get("trades") or 0))
    if out.winner is None:
        out.verdict = "Vitaz nema break-even, okolie sa porovnat neda."
        return out

    for rec in neighbour_records:
        tag = (rec.get("settings") or {}).get("plateau") or {}
        be = _be(rec)
        obchodov = int((rec.get("result") or {}).get("trades") or 0)
        drzi = (be is not None and out.ci_lo is not None and be >= out.ci_lo)
        out.rows.append({
            "param": tag.get("param"), "value": tag.get("value"), "step": tag.get("step"),
            "id": rec.get("id"), "status": rec.get("status"),
            "break_even_pct": be, "trades": obchodov,
            "holds": bool(drzi),
            "thin": obchodov < min_trades,
        })

    for riadok in out.rows:
        meno = riadok["param"] or "?"
        polozka = out.by_param.setdefault(meno, {"held": 0, "total": 0, "worst": None})
        if riadok["break_even_pct"] is None:
            continue
        polozka["total"] += 1
        polozka["held"] += int(riadok["holds"])
        if polozka["worst"] is None or riadok["break_even_pct"] < polozka["worst"]:
            polozka["worst"] = riadok["break_even_pct"]

    hodnoty = [r["break_even_pct"] for r in out.rows if r["break_even_pct"] is not None]
    if hodnoty:
        out.spread = round(max(hodnoty + [out.winner]) - min(hodnoty + [out.winner]), 6)
        if out.ci_lo is not None and out.ci_hi is not None and out.ci_hi > out.ci_lo:
            out.spread_ratio = round(out.spread / (out.ci_hi - out.ci_lo), 3)
    out.verdict = _verdict(out, min_trades)
    return out


def _verdict(a: Assessment, min_trades: int) -> str:
    """Jedna veta o tom, či je optimum plocha alebo hrot.

    Rozhoduje **rozptyl susedov voči intervalu spoľahlivosti víťaza**, nie šírka intervalu
    sama. Prvá verzia porovnávala šírku intervalu s hodnotou výsledku a hlásila „málo dát"
    aj vtedy, keď susedia ležali v rozpätí 0,014 pri intervale 0,107 — teda keď bola plocha
    preukázateľne rovná. Bootstrap interval break-even je pri malých kladných hodnotách
    takmer vždy širší než samotná hodnota, takže také pravidlo nepovie nikdy nič.

    Zmysel má opak: keď sa susedia od seba takmer nelíšia, parameter v tom rozsahu
    nerozhoduje — a presne to je plató.
    """
    hodnotene = [r for r in a.rows if r["break_even_pct"] is not None]
    if len(hodnotene) < 2:
        return "Dobehli menej nez dvaja susedia - bez nich sa robustnost hodnotit neda."
    if a.trades < min_trades:
        return (f"MALO DAT: vitaz ma {a.trades} obchodov, co je na rozlisenie plata od spicky "
                "malo. Pusti to na dlhsom okne.")
    if a.ci_lo is None:
        return "Interval spolahlivosti vitaza sa nedal spocitat, susedia su len na pozretie."

    pod = [r for r in hodnotene if r["break_even_pct"] < a.ci_lo]
    n = len(hodnotene)
    tesne = a.spread_ratio is not None and a.spread_ratio <= 0.35

    if not pod and tesne:
        return (f"PLATO: vsetkych {n} susedov drzi a lisia sa medzi sebou o {a.spread:.4f} %, "
                f"co je {a.spread_ratio:.0%} sirky intervalu vitaza. Parameter v tomto rozsahu "
                "nerozhoduje, takze presna cifra nie je kriticka - to je dobre znamenie.")
    if len(pod) >= n * 0.5:
        mena = ", ".join(sorted({r["param"] for r in pod if r["param"]}))
        return (f"SPICKA: {len(pod)} z {n} susedov je pod intervalom vitaza ({mena}). Optimum "
                "drzi len na tej jednej hodnote, co je tvar TOHO okna, nie strategie. "
                "Tieto parametre nepouzivaj.")
    if pod:
        mena = ", ".join(sorted({r["param"] for r in pod if r["param"]}))
        return (f"NEJASNE: {len(pod)} z {n} susedov je pod intervalom vitaza ({mena}), ostatni "
                "drzia. Parametre nie su rovnako citlive - pozri, ktory z nich to je.")
    return (f"SIROKE OKOLIE: vsetkych {n} susedov drzi, ale lisia sa medzi sebou o "
            f"{a.spread:.4f} % ({a.spread_ratio:.0%} sirky intervalu). Nie je to spicka, "
            "ale ani rovna plocha - vysledok na presnej hodnote trochu zalezi.")


# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def table(a: Assessment) -> str:
    """Okolie ako text — ASCII, konzola na Windows beží v cp1250."""
    if a.winner is None:
        return a.verdict
    lines = [f"vitaz: break-even {a.winner:.4f} %, {a.trades} obchodov"]
    if a.ci_lo is not None:
        lines.append(f"interval vitaza (Monte Carlo): {a.ci_lo:.4f} az {a.ci_hi:.4f} %")
    if a.spread is not None:
        pomer = f" ({a.spread_ratio:.0%} sirky intervalu)" if a.spread_ratio is not None else ""
        lines.append(f"rozptyl okolia: {a.spread:.4f} %{pomer}")
    lines += ["", f"{'sused':<26}{'hodnota':>10}{'obchodov':>10}{'break-even':>12}{'drzi':>7}"]
    for r in sorted(a.rows, key=lambda x: (x["param"] or "", x["step"] or 0)):
        be = r["break_even_pct"]
        lines.append(
            f"{(r['param'] or '?') + ' ' + ('+' if (r['step'] or 0) > 0 else '') + str(r['step']):<26}"
            f"{str(r['value']):>10}{r['trades']:>10}"
            f"{(f'{be:.4f}' if be is not None else '-'):>12}"
            f"{('ano' if r['holds'] else 'NIE'):>7}"
            + ("  <- malo obchodov" if r["thin"] else ""))
    lines += ["", a.verdict]
    return "\n".join(lines)
