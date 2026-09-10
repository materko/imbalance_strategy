"""Prop výzva: dostaneš sa k výplate skôr, než účet zhorí?

### Na akú otázku odpovedá
`tester.portfolio` povie, koľko by stratégia zarobila na vlastnom účte. Na prop účte to
nestačí, lebo tam **účet zomiera podľa pravidla**, nie podľa toho, či ti došli peniaze:
denný limit straty, celkový drawdown, minimálny počet dní, cieľ zisku. Séria strát, ktorá
by na vlastnom účte znamenala zlý mesiac, tu znamená koniec — a zaplatený poplatok.

Otázka teda nie je „koľko sa dá zarobiť“, ale **s akou pravdepodobnosťou sa dostanem
k výplate skôr, než ma pravidlo vyhodí** — a koľko výziev na to spálim.

### Ako sa to počíta
Nie jedným behom, ale **stovkami pokusov**: výzva sa začne postupne na každom obchode
histórie a prehrá sa dopredu, kým nepadne cieľ alebo pravidlo. To zámerne nie je bootstrap
— denný limit straty je o tom, ako sa straty **zhlukujú v čase**, a preskladanie obchodov
práve to zhlukovanie rozbije. Pokusy sa prekrývajú, takže nie sú nezávislé; výsledok treba
čítať ako „keby som začal v náhodnom bode tejto histórie“, nie ako interval spoľahlivosti.

Veľkosť pozície sa prepočítava z rizika (`riziko = zostatok × risk %`), rovnako ako
v `tester.portfolio` — inak by čísla hovorili o peňaženke behu, nie o stratégii.

### Čo to NEVIE a robí to optimistickým
**Vidí len uzavreté obchody.** Prop firmy merajú denný limit aj celkový drawdown na
**equity vrátane otvorených pozícií**; tu sa kontroluje až pri zatvorení obchodu. Pozícia,
ktorá išla hlboko proti a nakoniec vyšla na TP, tu účet nezabije — v skutočnosti by
mohla. Skutočná pravdepodobnosť prejdenia je teda **nižšia** než tá tu.

**Súbežné pozície sa nekrátia.** Keď sa do jedného účtu zlejú obchody z viacerých
trhov, simulácia ich odohrá za sebou, hoci v skutočnosti bežali naraz — a desať trhov
môže prehrať v ten istý deň. Práve denný limit je pravidlo, ktoré na tom účty zabíja,
takže **zliatie trhov robí výsledok optimistickým**; koľko pozícií naozaj bežalo naraz,
výpis hlási (`max_concurrent`).

**Nepozná sklz ani víkendové medzery** nad rámec toho, čo je v obchodoch behu, a nerieši
pravidlá o konzistencii, novinkách či držaní cez noc, ktorými firmy výplaty zamietajú.

**Nie je to rada, akú propku si vziať.** Čísla v `PRESETS` sú bežné tvary pravidiel, nie
ponuka konkrétnej firmy — pred použitím ich prepíš podľa zmluvy, ktorú naozaj máš.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Sequence

from .portfolio import _dt, _sl_distance

__all__ = [
    "Rules", "PRESETS", "CUSTOM", "Attempt", "Result", "attempt", "simulate", "risk_table",
    "report", "RISKS", "max_concurrent", "rules_for", "compare",
]

#: Kľúč pre pravidlá poskladané z polí (nie z predlohy firmy).
CUSTOM = "custom"

#: Riziká na obchod, ktoré sa skúšajú v tabuľke (% zo zostatku).
RISKS: tuple[float, ...] = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)

#: Pod týmto počtom obchodov je každé číslo nižšie anekdota.
MIN_TRADES = 40


@dataclass(frozen=True)
class Rules:
    """Pravidlá výzvy.

    Čísla v `PRESETS` sú odpísané z verejných stránok firiem k dátumu v `source` a firmy
    ich menia často. **Pred použitím ich prepíš podľa zmluvy, ktorú naozaj máš** — každé
    pole sa dá prepísať z príkazového riadku.
    """

    name: str = "vlastné"
    account: float = 100_000.0
    #: cieľ zisku pre každú fázu (% z počiatočného zostatku). Dĺžka = počet fáz.
    targets: tuple[float, ...] = (8.0, 5.0)
    #: denný limit straty, % z počiatočného zostatku dňa. **0 = firma denný limit nemá.**
    max_daily_loss_pct: float = 5.0
    #: celkový limit straty, % — od čoho sa počíta, hovorí `trailing`
    max_loss_pct: float = 10.0
    #: `"nie"` = od počiatočného zostatku (FTMO 2-step), `"vrchol"` = od najvyššej equity
    #: kedykoľvek (intraday trailing), `"koniec_dna"` = od najvyššieho **koncodenného**
    #: zostatku (FTMO 1-step, Apex EOD, Tradeify). Rozdiel medzi poslednými dvoma je
    #: veľký: intraday trailing berie aj vrchol, ktorý si nezrealizoval.
    trailing: str = "nie"
    #: `True` = hranica prestane stúpať, keď dorovná počiatočný zostatok (Apex)
    trailing_freeze_at_start: bool = False
    #: koľko rôznych dní musí byť odobchodovaných, než sa fáza dá uzavrieť
    min_days: int = 4
    #: pravidlo konzistencie: najlepší deň smie byť najviac toľko % z celého zisku.
    #: 0 = firma ho nemá. Pre algotradera je to zradné — jeden veľký deň fázu nezavrie.
    max_day_share_pct: float = 0.0
    #: cena výzvy
    cost: float = 500.0
    #: podiel zo zisku, ktorý dostane obchodník (%)
    payout_pct: float = 80.0
    #: vracia sa cena výzvy pri prvej výplate?
    refund: bool = True
    #: horizont v kalendárnych dňoch (0 = kým sú obchody)
    horizon_days: int = 0
    #: odkiaľ sú čísla — ide do každého výpisu, nech je vidieť, čo treba overiť
    source: str = ""

    @property
    def phases(self) -> int:
        return len(self.targets)

    def __post_init__(self) -> None:
        if not self.targets:
            raise ValueError("Rules.targets musí mať aspoň jednu fázu")
        if self.trailing not in ("nie", "vrchol", "koniec_dna"):
            raise ValueError(f"Rules.trailing musí byť 'nie', 'vrchol' alebo "
                             f"'koniec_dna', nie {self.trailing!r}")


def _pct(dolare: float, ucet: float) -> float:
    """Pravidlo v dolároch na % z účtu — firmy futures ich udávajú v peniazoch."""
    return round(dolare / ucet * 100.0, 4)


#: Predlohy podľa verejných pravidiel troch firiem. Overené 2026-09-10; **firmy ich menia
#: často**, takže to je východisko, nie zmluva. Účet je vždy 100k, aby sa dali porovnať.
PRESETS: dict[str, Rules] = {
    "ftmo2": Rules(
        name="FTMO 2-Step, 100k",
        targets=(10.0, 5.0), max_daily_loss_pct=5.0, max_loss_pct=10.0,
        trailing="nie", min_days=4, cost=540.0, payout_pct=80.0, refund=True,
        source="ftmo.com/en/trading-objectives/, 2026-09-10 (2-Step: cieľ 10 %/5 %, "
               "denný 5 %, celkový 10 % statický, min 4 dni)"),
    "ftmo1": Rules(
        name="FTMO 1-Step, 100k",
        targets=(10.0,), max_daily_loss_pct=3.0, max_loss_pct=10.0,
        trailing="koniec_dna", min_days=0, max_day_share_pct=50.0,
        cost=540.0, payout_pct=80.0, refund=True,
        source="ftmo.com/en/trading-objectives/, 2026-09-10 (1-Step: cieľ 10 %, denný 3 %, "
               "celkový 10 % s koncodenným trailingom, najlepší deň max 50 % zisku)"),
    "apex100": Rules(
        name="Apex 100k evaluácia (intraday trailing)",
        targets=(_pct(6_000, 100_000),), max_daily_loss_pct=0.0,
        max_loss_pct=_pct(3_000, 100_000), trailing="vrchol",
        trailing_freeze_at_start=True, min_days=0,
        cost=137.0, payout_pct=100.0, refund=False,
        source="tradetanto.com/learn/apex-trader-funding-rules-what-you-need-to-know, "
               "2026-09-10 (100k: cieľ $6 000, trailing $3 000, bez denného limitu, bez "
               "minima dní; intraday varianta)"),
    "apex50": Rules(
        name="Apex 50k evaluácia (EOD trailing s denným limitom)",
        account=50_000.0, targets=(_pct(3_000, 50_000),),
        max_daily_loss_pct=_pct(1_000, 50_000), max_loss_pct=_pct(2_000, 50_000),
        trailing="koniec_dna", trailing_freeze_at_start=True, min_days=0,
        cost=87.0, payout_pct=100.0, refund=False,
        source="tradetanto.com/learn/apex-trader-funding-rules-what-you-need-to-know, "
               "2026-09-10 (50k: cieľ $3 000, drawdown $2 000, denný limit $1 000)"),
    "tradeify_growth": Rules(
        name="Tradeify Growth 100k",
        targets=(_pct(6_000, 100_000),), max_daily_loss_pct=0.0,
        max_loss_pct=_pct(3_500, 100_000), trailing="koniec_dna", min_days=1,
        cost=300.0, payout_pct=90.0, refund=False,
        source="tradetanto.com/learn/tradeify-rules-explained-what-every-trader-should-know, "
               "2026-09-10 (Growth 100k: cieľ $6 000, EOD trailing $3 500, denný limit "
               "$2 500 je len pauza na seansu, nie pád — preto je tu 0)"),
    "tradeify_select": Rules(
        name="Tradeify Select 100k",
        targets=(_pct(6_000, 100_000),), max_daily_loss_pct=0.0,
        max_loss_pct=_pct(3_000, 100_000), trailing="koniec_dna", min_days=3,
        max_day_share_pct=40.0, cost=300.0, payout_pct=90.0, refund=False,
        source="tradetanto.com/learn/tradeify-rules-explained-what-every-trader-should-know, "
               "2026-09-10 (Select 100k: cieľ $6 000, EOD trailing $3 000, bez denného "
               "limitu, min 3 dni, konzistencia 40 %)"),
}


@dataclass
class Attempt:
    """Jeden pokus o výzvu — od jedného vstupného bodu histórie po koniec."""

    outcome: str = ""          # "prešiel" | "spálený" | "nedobehol"
    reason: str = ""           # čo ho ukončilo
    phase: int = 1             # v ktorej fáze skončil
    days: int = 0              # kalendárne dni od prvého obchodu
    trades: int = 0
    profit: float = 0.0        # zisk v mene účtu pri prejdení (inak 0)
    max_dd_pct: float = 0.0

    @property
    def passed(self) -> bool:
        return self.outcome == "prešiel"

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "passed": self.passed}


def _pnl(t: dict[str, Any], zostatok: float, risk_pct: float) -> float | None:
    """Zisk obchodu po prepočte na riziko `risk_pct` zo `zostatok`. `None` = bez stopu."""
    sl = _sl_distance(t)
    if not sl or sl <= 0:
        return None
    mnozstvo = zostatok * risk_pct / 100.0 / sl
    smer = -1.0 if t.get("is_short") else 1.0
    zisk = (float(t["close_rate"]) - float(t["open_rate"])) * mnozstvo * smer
    # Poplatky behu uz obchod zaplatil, tak sa prepocitaju na novu velkost.
    objem = (float(t["open_rate"]) + float(t["close_rate"])) * mnozstvo
    poplatok = (float(t.get("fee_open") or 0) + float(t.get("fee_close") or 0)) * objem / 2
    return zisk - poplatok


def max_concurrent(trades: Sequence[dict[str, Any]]) -> int:
    """Najviac pozícií otvorených naraz. 1 = obchody idú pekne za sebou.

    Pre denný limit je to kľúčové číslo: päť naraz otvorených pozícií môže prehrať v ten
    istý deň, kým simulácia ich odohrá jednu po druhej a limit tak nikdy nenarazí.
    """
    udalosti: list[tuple[Any, int]] = []
    for t in trades:
        od, do = _dt(t.get("open_date")), _dt(t.get("close_date"))
        if od is None or do is None:
            continue
        udalosti += [(od, 1), (do, -1)]
    if not udalosti:
        return 0
    # Zatvorenie pred otvorenim pri rovnakom case: pozicia, ktora prave skoncila,
    # uz miesto nezabera.
    udalosti.sort(key=lambda x: (x[0], x[1]))
    teraz = najviac = 0
    for _, zmena in udalosti:
        teraz += zmena
        najviac = max(najviac, teraz)
    return najviac


def _sorted(trades: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Obchody podľa času **zatvorenia** — zostatok sa mení, keď obchod skončí."""
    return sorted((t for t in trades if _dt(t.get("close_date")) is not None),
                  key=lambda t: _dt(t["close_date"]))


def _floor(rules: Rules, vrchol: float, eod_vrchol: float) -> float:
    """Odkiaľ sa počíta celkový limit — a kde sa zastaví.

    Limit je vždy **pevná suma** (% z počiatočného zostatku), nie percento z vrcholu:
    tak to majú všetky tri firmy. Mení sa len to, od čoho sa tá suma odpočíta.
    """
    zaklad = {"nie": rules.account, "vrchol": vrchol, "koniec_dna": eod_vrchol}[rules.trailing]
    strop = rules.account + rules.account * rules.max_loss_pct / 100.0
    if rules.trailing_freeze_at_start:
        # Apex: hranica prestane stúpať, keď dorovná počiatočný zostatok.
        zaklad = min(zaklad, strop)
    return zaklad - rules.account * rules.max_loss_pct / 100.0


def attempt(trades: Sequence[dict[str, Any]], rules: Rules, *, risk_pct: float,
            start: int = 0) -> Attempt:
    """Jeden pokus: obchody od indexu `start` dopredu, kým nepadne cieľ alebo pravidlo.

    Obchody musia byť už zoradené (`_sorted`). Fázy idú za sebou a každá začína
    s čerstvým zostatkom — tak to firmy robia, a preto je dvojfázová výzva podstatne
    ťažšia než dvojnásobok jednofázovej.
    """
    out = Attempt()
    if start >= len(trades):
        return replace(out, outcome="nedobehol", reason="žiadne obchody")
    zaciatok = _dt(trades[start]["close_date"]).date()

    faza = 0
    zostatok = vrchol = eod_vrchol = rules.account
    den: date | None = None
    zaciatok_dna = rules.account
    dni: set[date] = set()
    zisk_dna: dict[date, float] = {}
    max_dd = 0.0

    def koniec(outcome: str, reason: str, kedy: date, zisk: float = 0.0) -> Attempt:
        return replace(out, outcome=outcome, reason=reason, phase=faza + 1,
                       days=(kedy - zaciatok).days, trades=out.trades, profit=round(zisk, 2),
                       max_dd_pct=round(max_dd * 100, 2))

    for t in trades[start:]:
        kedy = _dt(t["close_date"]).date()
        if rules.horizon_days and (kedy - zaciatok).days > rules.horizon_days:
            return koniec("nedobehol", "horizont", kedy)
        if kedy != den:
            if den is not None:
                eod_vrchol = max(eod_vrchol, zostatok)   # zostatok na konci predošlého dňa
            den, zaciatok_dna = kedy, zostatok

        zmena = _pnl(t, zostatok, risk_pct)
        if zmena is None:
            continue                      # obchod bez známeho stopu sa nedá preškálovať
        zostatok += zmena
        out.trades += 1
        dni.add(kedy)
        zisk_dna[kedy] = zisk_dna.get(kedy, 0.0) + zmena
        vrchol = max(vrchol, zostatok)
        if vrchol > 0:
            max_dd = max(max_dd, (vrchol - zostatok) / vrchol)

        # -- pravidlá, ktoré účet zabijú -------------------------------------- #
        if rules.max_daily_loss_pct > 0:
            dno_dna = zaciatok_dna - rules.account * rules.max_daily_loss_pct / 100.0
            if zostatok <= dno_dna:
                return koniec("spálený", "denný limit", kedy)
        if zostatok <= _floor(rules, vrchol, eod_vrchol):
            return koniec("spálený", "celkový limit", kedy)

        # -- cieľ -------------------------------------------------------------- #
        zisk = zostatok - rules.account
        if zisk < rules.account * rules.targets[faza] / 100.0 or len(dni) < rules.min_days:
            continue
        # Pravidlo konzistencie: jeden veľký deň fázu nezavrie. Pre algotradera je to
        # zradné — nedá sa naň reagovať inak než ďalej obchodovať a zisk „rozriediť“.
        if rules.max_day_share_pct > 0 and zisk > 0:
            najlepsi = max(zisk_dna.values(), default=0.0)
            if najlepsi > zisk * rules.max_day_share_pct / 100.0:
                continue
        if faza + 1 >= rules.phases:
            return koniec("prešiel", "cieľ", kedy, zisk)
        # Ďalšia fáza: čerstvý zostatok, čerstvé dni, ten istý sled obchodov.
        faza += 1
        zostatok = vrchol = eod_vrchol = rules.account
        dni, zisk_dna, den = set(), {}, None

    return koniec("nedobehol", "došli obchody", _dt(trades[-1]["close_date"]).date())


@dataclass
class Result:
    """Stovky pokusov zhrnuté do čísel, ktoré rozhodujú."""

    rules: Rules = field(default_factory=Rules)
    risk_pct: float = 1.0
    attempts: int = 0
    passed: int = 0
    burned: int = 0
    unfinished: int = 0
    p_pass: float = 0.0
    #: koľko výziev sa v priemere zaplatí na jednu výplatu
    per_payout: float | None = None
    median_days: float | None = None
    median_profit: float | None = None
    ev: float | None = None
    reasons: dict[str, int] = field(default_factory=dict)
    #: najviac pozícií otvorených naraz v podkladových obchodoch (1 = idú za sebou)
    max_concurrent: int = 1
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        out = {k: v for k, v in self.__dict__.items() if k != "rules"}
        out["rules"] = dict(self.rules.__dict__)
        return out


def simulate(trades: Sequence[dict[str, Any]], rules: Rules | None = None, *,
             risk_pct: float = 1.0, step: int = 1) -> Result:
    """Pokus začatý na každom `step`-tom obchode histórie.

    `step > 1` zriedi štartovacie body, keď je obchodov veľa — pokusy sa aj tak
    prekrývajú, takže hustejšie štarty pridávajú viac času než informácie.
    """
    import statistics

    rules = rules or Rules()
    zoradene = _sorted(trades)
    out = Result(rules=rules, risk_pct=risk_pct)
    if len(zoradene) < 2:
        out.verdict = "MALO DAT: bez obchodov s dátumom zatvorenia sa výzva simulovať nedá"
        return out

    out.max_concurrent = max_concurrent(zoradene)
    pokusy = [attempt(zoradene, rules, risk_pct=risk_pct, start=i)
              for i in range(0, len(zoradene), max(1, step))]
    out.attempts = len(pokusy)
    out.passed = sum(1 for a in pokusy if a.passed)
    out.burned = sum(1 for a in pokusy if a.outcome == "spálený")
    out.unfinished = sum(1 for a in pokusy if a.outcome == "nedobehol")
    for a in pokusy:
        out.reasons[a.reason] = out.reasons.get(a.reason, 0) + 1

    # Nedobehnuté pokusy sa do pravdepodobnosti počítajú ako neúspech: výzva, ktorá sa
    # do horizontu nedostala k cieľu, je zaplatená a bez výplaty rovnako ako spálená.
    out.p_pass = round(out.passed / out.attempts, 4) if out.attempts else 0.0
    if out.passed:
        out.per_payout = round(1 / out.p_pass, 1)
        out.median_days = statistics.median([a.days for a in pokusy if a.passed])
        out.median_profit = round(statistics.median([a.profit for a in pokusy if a.passed]), 2)
        vyplata = rules.payout_pct / 100.0 * out.median_profit + (rules.cost if rules.refund else 0.0)
        out.ev = round(out.p_pass * vyplata - rules.cost, 2)
    else:
        out.ev = round(-rules.cost, 2)

    out.verdict = _verdict(out, len(zoradene))
    return out


def _verdict(r: Result, trades: int) -> str:
    if trades < MIN_TRADES:
        return (f"MALO DAT: {trades} obchodov je na simuláciu výzvy málo — pokusy sa "
                f"prekrývajú natoľko, že to je jeden priebeh, nie stovky.")

    hlavny = max(r.reasons, key=r.reasons.get) if r.reasons else ""
    # Horizont ako najcastejsi dovod nie je o kvalite stratégie, ale o jej TEMPE: ciel
    # nestihne, lebo nemá dosť obchodov. To je iná chyba a iné riešenie než spálený účet.
    if hlavny == "horizont":
        podiel = r.reasons["horizont"] / r.attempts * 100
        return (f"PRILIS POMALA: {podiel:.0f} % pokusov sa do horizontu "
                f"{r.rules.horizon_days} dní k cieľu ani nedostane. Nie je to o riziku ani "
                f"o pravidlách — stratégia jednoducho neurobí dosť obchodov. Riešenie je "
                f"viac trhov naraz alebo výzva bez časového limitu, nie väčšie pozície.")
    if not r.passed:
        return (f"NEPREJDE: ani jeden z {r.attempts} pokusov sa nedostal k výplate "
                f"(najčastejšie končí na: {hlavny}). Pri riziku {r.risk_pct:g} % je to "
                f"zaplatený poplatok bez šance.")

    suvisle = ("" if r.max_concurrent <= 1 else
               f" Pozor: v podkladových obchodoch bežalo naraz až {r.max_concurrent} "
               f"pozícií, ale simulácia ich odohrá za sebou — denný limit je tým pádom "
               f"podstrelený a šanca nadhodnotená.")
    ev = r.ev or 0.0
    zaklad = (f"{r.p_pass * 100:.0f} % pokusov prejde (asi {r.per_payout:g} výziev na jednu "
              f"výplatu), medián {r.median_days:.0f} dní, EV na výzvu {ev:+.0f}")
    # Ciel, ktory padne za den-dva, nepadol vdaka strategii, ale vdaka jednemu obchodu.
    rychle = ("" if r.median_days is None or r.median_days > 2 else
              f" Medián {r.median_days:.0f} dní znamená, že cieľ padne na jednom-dvoch "
              f"obchodoch — taká výplata stojí na šťastí, nie na stratégii. Firmy na to "
              f"majú minimum dní a pravidlo konzistencie; táto predloha ich má "
              f"{r.rules.min_days} a "
              + (f"{r.rules.max_day_share_pct:g} %." if r.rules.max_day_share_pct else "žiadne."))
    tenke = ("" if r.passed >= 10 else
             f" Odhad stojí na {r.passed} úspešných pokusoch, takže je to rádový údaj, "
             f"nie číslo.")
    if ev > 0:
        return (f"KLADNA EV: {zaklad}. Simulácia vidí len uzavreté obchody, takže je "
                f"optimistická — skutočná šanca je nižšia.{tenke}{rychle}{suvisle}")
    return (f"ZAPORNA EV: {zaklad}. Poplatok za výzvu zje viac, než tá šanca prinesie — "
            f"skús iné riziko alebo miernejšie pravidlá.{tenke}{rychle}{suvisle}")


def risk_table(trades: Sequence[dict[str, Any]], rules: Rules | None = None, *,
               risks: Sequence[float] = RISKS, step: int = 1) -> list[Result]:
    """To isté pre viac rizík — „ako veľké pozície" je tu hlavná páka.

    Väčšie riziko dosiahne cieľ rýchlejšie **a** narazí na limit častejšie; kde je
    optimum, sa nedá odhadnúť, len zmerať.
    """
    return [simulate(trades, rules, risk_pct=r, step=step) for r in risks]


def report(results: Sequence[Result], label: str = "") -> str:
    """Textový výpis pre CLI. Bez diakritiky v číslach — konzola Windows ju nemusí zvládať."""
    if not results:
        return "ziadne vysledky"
    r0 = results[0]
    p = r0.rules
    penize = lambda v: f"{v:,.0f}".replace(",", " ")  # noqa: E731
    denny = f"{p.max_daily_loss_pct:g} %" if p.max_daily_loss_pct else "ziadny"
    trailing = {"nie": "staticky", "vrchol": "trailing z vrcholu",
                "koniec_dna": "trailing z konca dna"}[p.trailing]
    out = [("=== Prop vyzva: " + label).rstrip() + " ===",
           f"pravidla: {p.name} — ucet {penize(p.account)}, ciele "
           + " + ".join(f"{x:g} %" for x in p.targets)
           + f", denny limit {denny}, celkovy {p.max_loss_pct:g} % ({trailing}"
           + (", zastavi sa na pociatocnom zostatku" if p.trailing_freeze_at_start else "")
           + f"), min {p.min_days} dni"
           + (f", najlepsi den max {p.max_day_share_pct:g} % zisku" if p.max_day_share_pct else ""),
           f"cena {penize(p.cost)}, podiel {p.payout_pct:g} %"
           f"{', vratna pri vyplate' if p.refund else ''}"
           f", horizont {str(p.horizon_days) + ' dni' if p.horizon_days else 'bez limitu'}"]
    if p.source:
        out.append(f"zdroj cisel: {p.source}")
        out.append("POZOR: firmy pravidla menia casto - over si ich podla svojej zmluvy.")
    out.append("")
    out.append(f"{'riziko':>8}{'pokusov':>9}{'presiel':>9}{'spaleny':>9}{'nedobehol':>11}"
               f"{'P(vyplata)':>12}{'dni':>7}{'EV':>10}")
    for r in results:
        dni = "-" if r.median_days is None else f"{r.median_days:.0f}"
        ev = "-" if r.ev is None else f"{r.ev:+.0f}"
        out.append(f"{r.risk_pct:>7.2f}%{r.attempts:>9}{r.passed:>9}{r.burned:>9}"
                   f"{r.unfinished:>11}{r.p_pass * 100:>11.1f}%{dni:>7}{ev:>10}")

    najlepsi = max(results, key=lambda r: (r.ev if r.ev is not None else -1e18))
    out += ["", f"najlepsie riziko podla EV: {najlepsi.risk_pct:g} %"]
    if najlepsi.max_concurrent > 1:
        out.append(f"naraz otvorenych pozicii v podklade: az {najlepsi.max_concurrent} "
                   f"(simulacia ich odohra za sebou)")
    out.append("")
    if najlepsi.reasons:
        poradie = sorted(najlepsi.reasons.items(), key=lambda kv: -kv[1])
        out.append("preco pokusy koncia (pri tom riziku): "
                   + ", ".join(f"{k} {v}x" for k, v in poradie))
    out += ["", najlepsi.verdict]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# viac predlôh naraz
# --------------------------------------------------------------------------- #
#
# Otázka „unesie to propku?" má zmysel až ako porovnanie: tie isté obchody, pravidlá
# rôznych firiem vedľa seba. Preto sa vyberá zoznam predlôh, nie jedna — a k nim
# voliteľne `custom`, pravidlá poskladané z polí formulára.


def rules_for(keys: Sequence[str], overrides: dict[str, Any] | None = None) -> list[tuple[str, Rules]]:
    """Predlohy podľa kľúčov: `all` = všetky firmy, `custom` = pravidlá z polí.

    Prepisy z polí (`overrides`) sa uplatnia **len na `custom`**. Predlohy firiem sú
    nemenné — inak by jedna zaškrtnutá firma dostala čísla predvyplnené z inej a výpis
    by niesol jej meno s cudzími pravidlami. Prepisy bez `custom` v zozname sú chyba,
    nie tiché ignorovanie.
    """
    vybrane: list[str] = []
    for k in keys:
        for cast in str(k).split(","):
            cast = cast.strip()
            if not cast:
                continue
            if cast == "all":
                vybrane += [p for p in PRESETS if p not in vybrane]
            elif cast not in vybrane:
                vybrane.append(cast)
    if not vybrane:
        raise ValueError(f"vyber aspoň jednu predlohu; známe: {', '.join(PRESETS)}, {CUSTOM}, all")
    nezname = [k for k in vybrane if k != CUSTOM and k not in PRESETS]
    if nezname:
        raise ValueError(f"neznáme pravidlá {', '.join(nezname)}; známe: "
                         f"{', '.join(PRESETS)}, {CUSTOM}, all")

    zmeny = {k: v for k, v in (overrides or {}).items() if v is not None}
    if zmeny and CUSTOM not in vybrane:
        raise ValueError(f"prepisy pravidiel ({', '.join(sorted(zmeny))}) platia len na predlohu "
                         f"`{CUSTOM}` — pridaj ju do zoznamu, predlohy firiem sa nemenia")
    out: list[tuple[str, Rules]] = []
    for k in vybrane:
        if k == CUSTOM:
            out.append((k, replace(Rules(name="vlastné pravidlá"), **zmeny)))
        else:
            out.append((k, PRESETS[k]))
    return out


def compare(variants: Sequence[tuple[str, Sequence[Result]]]) -> str:
    """Porovnanie predlôh: pri každej najlepšie riziko podľa EV a čo z toho vyšlo."""
    if not variants:
        return "ziadne predlohy"
    out = ["=== Porovnanie predloh (najlepsie riziko podla EV) ===",
           f"{'predloha':<18}{'riziko':>8}{'P(vyplata)':>12}{'dni':>6}{'EV':>9}  verdikt"]
    for kluc, vysledky in variants:
        if not vysledky:
            out.append(f"{kluc:<18}{'-':>8}{'-':>12}{'-':>6}{'-':>9}  bez vysledku")
            continue
        naj = max(vysledky, key=lambda r: (r.ev if r.ev is not None else -1e18))
        dni = "-" if naj.median_days is None else f"{naj.median_days:.0f}"
        ev = "-" if naj.ev is None else f"{naj.ev:+.0f}"
        znacka = naj.verdict.split(":")[0] if naj.verdict else ""
        out.append(f"{kluc:<18}{naj.risk_pct:>7.2f}%{naj.p_pass * 100:>11.1f}%{dni:>6}{ev:>9}  {znacka}")
    return "\n".join(out)
