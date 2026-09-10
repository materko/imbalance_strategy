"""Meranie, ktoré sa napíše samo — z behov v histórii do `docs/merania/`.

### Načo to je
`tester.checkup` udržiava **jeden dokument pri stratégii**: aká tá stratégia je dnes.
Prepisuje sa celý, takže sa v ňom nedá nalistovať, čo sa meralo minulý mesiac a čo z toho
vyšlo. Merania sú to druhé — **datovaný snímok konkrétnej otázky** na konkrétnych behoch,
ktorý ostáva, aj keď sa stratégia medzitým zmení. Preto majú v repozitári vlastný adresár
a preto ich CLAUDE.md vyžaduje s číslami po oknách.

Tento modul je ten snímok: vezme behy, ktoré mu dáš, pustí nad nimi **tú istú batériu ako
`checkup`** (`checkup.measure` — okná, charakter, skupiny obchodov, náhoda, slabnúci edge,
Monte Carlo) a pridá dve veci, ktoré k jednej stratégii nepatria, ale k meraniu áno:
**maticu trhov** a **cenu rizika**. Merať sa musí rovnako, inak sa dva dokumenty nedajú
porovnať — preto je merací engine jeden a dokumenty dva.

### Čo to NIE JE
**Nespúšťa backtesty.** Píše sa len to, čo v histórii už je. Keď na niektorú otázku behy
nestačia, dokument to povie nahlas aj s príkazom, ktorým sa to doplní — namiesto toho, aby
sekcia potichu chýbala alebo sa vyplnila číslom z jedného okna.

**Nerobí záver za človeka.** Zhrnutie je tabuľka verdiktov jednotlivých testov; čo z nich
plynie dokopy, patrí do vety, ktorú dopíše ten, kto meranie robil. Preto je na začiatku
dokumentu prázdne miesto `## Záver` — a nie vygenerovaná veta, ktorá by vyzerala ako
zistenie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from tradebot.core.paths import MERANIA_DIR

from .hyperopt import REFERENCE_WINDOWS

__all__ = ["Section", "Paper", "build", "write", "filename", "render"]

#: Menej než toľko obchodov a do dokumentu ide „málo dát“, nie číslo. Rovnaká hranica
#: ako v `checkup` a v Monte Carle.
MIN_TRADES = 30


@dataclass
class Section:
    """Jedna sekcia dokumentu. `gap` znamená, že na ňu behy nestačili."""

    title: str
    body: str
    #: krátky verdikt do zhrnutia (prázdny = do tabuľky nejde)
    verdict: str = ""
    gap: str = ""


@dataclass
class Paper:
    title: str
    strategy: str
    pairs: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    windows: list[str] = field(default_factory=list)
    runs: list[dict[str, Any]] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    command: str = ""
    #: `checkup.verdicts()` — tie isté vety, aké má stratégia vo svojej ANALYTIKA.md
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


def _num(value: Any, digits: int = 4, plus: bool = True) -> str:
    if value is None:
        return "—"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{f:+.{digits}f}" if plus else f"{f:.{digits}f}"


def _skratka(text: str, limit: int = 60) -> str:
    """Verdikt do zhrnutia. Reže sa na hranici slova — useknuté slovo vyzerá ako chyba."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    orez = text[:limit].rsplit(" ", 1)[0]
    return (orez or text[:limit]).rstrip(",;:") + "…"


def _tabulka(hlavicka: Sequence[str], riadky: Sequence[Sequence[str]]) -> str:
    """Markdown tabuľka. Zarovnanie nerieši — čitateľ vidí render, nie zdroj."""
    out = ["| " + " | ".join(hlavicka) + " |",
           "|" + "|".join(["---"] * len(hlavicka)) + "|"]
    out += ["| " + " | ".join(str(b) for b in r) + " |" for r in riadky]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# sekcie z batérie (`checkup.measure`) — nič sa tu už nemeria, len píše
# --------------------------------------------------------------------------- #


def _po_oknach(records: Sequence[dict[str, Any]]) -> Section:
    """Čísla po referenčných oknách a znamienko v každom z nich.

    Berie sa zo záznamov behov, nie z batérie: `checkup` počíta s tým, že okná bežali
    práve raz a v poradí, kým sem môže prísť ľubovoľný výber behov — vrátane dvoch
    v jednom okne.
    """
    podla_okna: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        okno = (rec.get("settings") or {}).get("timerange")
        if okno:
            podla_okna.setdefault(okno, []).append(rec)

    znama = [w for w in REFERENCE_WINDOWS if w in podla_okna]
    ostatne = sorted(k for k in podla_okna if k not in REFERENCE_WINDOWS)
    poradie = znama + ostatne
    if not poradie:
        return Section("Po oknách", "", gap="behy nemajú uložené okno (`timerange`)")

    riadky, kladne, spolu = [], 0, 0
    for okno in poradie:
        pre = podla_okna[okno]
        # Viac behov v jednom okne = alternatívy tej istej veci; berie sa ten s najviac
        # obchodmi, aby sa dve konfigurácie nemiešali do jedného riadku.
        rec = max(pre, key=lambda r: (r.get("result") or {}).get("trades") or 0)
        v = rec.get("result") or {}
        be = v.get("break_even_pct")
        if be is not None:
            spolu += 1
            kladne += be > 0
        riadky.append([okno, v.get("trades", "—"), _num(v.get("winrate"), 1, plus=False),
                       _num(v.get("pnl_pct"), 3), _num(be),
                       _num(v.get("max_drawdown_pct"), 2, plus=False),
                       f"`{rec['id']}`" + (f" (+{len(pre) - 1})" if len(pre) > 1 else "")])

    chybaju = [w for w in REFERENCE_WINDOWS if w not in podla_okna]
    telo = [_tabulka(["okno", "obchodov", "WR %", "PnL %", "break-even %", "max DD %", "beh"],
                     riadky), ""]
    telo.append(f"**Kladné v {kladne} z {spolu} okien.** PnL v % závisí od sizingu a "
                f"peňaženky, break-even nie — preto je rozhodujúci on.")
    if chybaju:
        telo += ["", f"Chýbajú referenčné okná: {', '.join('`' + w + '`' for w in chybaju)}. "
                     f"Bez nich je záver o stabilite slabší."]
    verdikt = f"kladné v {kladne} z {spolu} okien" if spolu else "nedá sa určiť"
    return Section("Po oknách", "\n".join(telo), verdict=verdikt)


def _charakter(report: dict[str, Any]) -> Section:
    """Aký typ stratégie to je — a čo je pri tom type normálne."""
    ch = report.get("character") or {}
    if not ch.get("title"):
        return Section("Čo je to za stratégiu", "",
                       gap="charakter sa nedal zaradiť (málo obchodov alebo chýbajú sviečky)")

    cisla = [["winrate", _num(ch.get("winrate"), 1, plus=False) + " %"],
             ["payoff (zisk / strata)", _num(ch.get("payoff"), 2, plus=False)],
             ["očakávanie na obchod", _num(ch.get("expectancy_pct"), 4) + " %"],
             ["medián držania", f"{ch.get('median_bars') or '—'} barov"],
             ["obchodov za deň", _num(ch.get("trades_per_day"), 2, plus=False)],
             ["pohyb pred vstupom", _num(ch.get("pre_entry_atr"), 2, plus=False) + " ATR"],
             ["teplo pred ziskom (MAE/MFE)", _num(ch.get("heat_ratio"), 2, plus=False)]]
    telo = [f"**{ch['title']}** (istota: {ch.get('confidence') or '—'})", ""]
    telo += [f"- {d}" for d in (ch.get("evidence") or [])]
    telo += ["", _tabulka(["miera", "hodnota"], cisla), "",
             f"**Čo je pri tomto type normálne.** {ch.get('normal', '')}", "",
             f"**Na čo pozor.** {ch.get('watch', '')}", "",
             f"**Čo ladiť.** {ch.get('tune', '')}"]
    return Section("Čo je to za stratégiu", "\n".join(telo), verdict=ch["title"])


def _interval(report: dict[str, Any]) -> Section:
    """Interval okolo nameraného break-evenu — je to edge, alebo to bola vzorka?"""
    if report.get("trades", 0) < MIN_TRADES:
        return Section("Interval okolo výsledku", "",
                       gap=f"menej než {MIN_TRADES} obchodov; interval by bol taký široký, "
                           f"že by nič nehovoril")
    be = (report.get("montecarlo") or {}).get("break_even") or {}
    if not be:
        return Section("Interval okolo výsledku", "", gap="Monte Carlo nevrátilo break-even")

    fee = report.get("fee_pct")
    telo = [f"Namerané **{_num(be.get('observed'))} %**; preskladaním vlastných obchodov "
            f"(blokový bootstrap) vyjde medzi **{_num(be.get('lo'))}** a "
            f"**{_num(be.get('hi'))} %**, medián {_num(be.get('median'))} %."]
    if be.get("p_above_fee") is not None and fee:
        odkial = report.get("fee_note") or ""
        telo += ["", f"Nad nákladom {_num(fee, 5, plus=False)} % na stranu"
                     + (f" ({odkial})" if odkial else "")
                     + f" skončí **{be['p_above_fee'] * 100:.0f} %** preskladaní. Keď je "
                       f"toto číslo blízko sto, výsledok neunesie len jedna šťastná séria "
                       f"obchodov."]
    elif not fee:
        telo += ["", "Náklad na tomto trhu nepoznáme, takže break-even sa tu proti ničomu "
                     "neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`)."]
    return Section("Interval okolo výsledku", "\n".join(telo),
                   verdict=f"{_num(be.get('lo'))} až {_num(be.get('hi'))} %")


def _nahoda(report: dict[str, Any]) -> Section:
    """Je ten edge odlíšiteľný od hodu mincou — a nie je celý len o tom, KEDY obchoduje?"""
    nully = report.get("null") or {}
    prvy = next((v for v in nully.values() if v.get("sigma") is not None), None)
    if prvy is None:
        # Bez sigmy je tabuľka rad pomlčiek — a prázdna tabuľka v dokumente vyzerá ako
        # zmerané nič, hoci sa nemeralo. Radšej medzera nahlas.
        poznamka = next((v.get("note") for v in nully.values() if v.get("note")), "")
        return Section("Odlíšiteľné od náhody?", "",
                       gap=poznamka or "náhodné vstupy sa losujú zo sviečok jedného páru; "
                                       "pre tento výber behov sa to nedalo spočítať")

    riadky = [[f"`{meno}`", _num(v.get("observed")),
               f"{_num(v.get('mean'))} ± {_num(v.get('sd'), 4, plus=False)}",
               f"{_num(v.get('sigma'), 2)} σ", _num(v.get("percentile"), 1, plus=False)]
              for meno, v in nully.items()]
    telo = ["Tá istá stratégia, ktorá obchoduje rovnako často, rovnakým smerom a s rovnakým "
            "stopom aj take profitom — len si nevyberá, **kedy** vstúpiť.", "",
            _tabulka(["náhoda", "stratégia", "náhoda", "rozdiel", "percentil"], riadky), "",
            prvy.get("verdict") or ""]
    return Section("Odlíšiteľné od náhody?", "\n".join(telo),
                   verdict=f"{_num(prvy.get('sigma'), 1)} σ")


def _slabne(report: dict[str, Any]) -> Section:
    d = report.get("decay") or {}
    obdobia = d.get("periods") or []
    if not obdobia:
        return Section("Slabne edge?", "", gap="obchody nemajú dátumy")

    riadky = [[p["label"], p["trades"], _num(p.get("per_month"), 1, plus=False),
               _num(p.get("winrate"), 1, plus=False), _num(p.get("break_even_pct")),
               "—" if p.get("percentile") is None else _num(p["percentile"], 0, plus=False)]
              for p in obdobia]
    telo = []
    if d.get("lo") is not None:
        telo += [f"Úsek takej dĺžky, akú má posledné obdobie, vyjde tej istej stratégii medzi "
                 f"**{_num(d['lo'])}** a **{_num(d['hi'])} %** už len preskladaním vlastných "
                 f"obchodov. Preto sa posledné obdobie neporovnáva s celkom: je kratšie, "
                 f"teda aj prirodzene rozkolísanejšie.", ""]
    telo += [_tabulka(["obdobie", "obchodov", "/mes.", "WR %", "break-even %", "percentil"],
                      riadky), "", d.get("note") or d.get("verdict") or ""]
    if d.get("verdict") != "MALO DAT":
        telo += ["", "Percentil je test len pre **posledné** obdobie, lebo to bolo vybraté "
                     "vopred; percentily ostatných období sú opis."]
    return Section("Slabne edge?", "\n".join(telo), verdict=d.get("verdict") or "")


def _analytika(report: dict[str, Any], mixed_pairs: bool) -> Section:
    r = report.get("analytics") or {}
    if not r.get("splits"):
        return Section("Ktorá skupina obchodov kazí výsledok", "",
                       gap="na rozdelenie na skupiny je málo obchodov")

    telo = [r.get("headline") or "", ""]
    if mixed_pairs:
        telo += ["> Zliate sú obchody z viacerých párov. Vzdialenosť stopu ani prahy "
                 "v cenových bodoch medzi nimi porovnateľné nie sú.", ""]
    for s in r["splits"][:3]:
        riadky = [[b["label"], b["trades"], _num(b["share_pct"], 1, plus=False),
                   _num(b["winrate"], 1, plus=False), _num(b["break_even_pct"]),
                   _num(b["without_pct"]), _num(b["impact"])] for b in s["buckets"]]
        telo += [f"**{s['title']}** — {s['note']}", "",
                 _tabulka(["skupina", "obch.", "podiel %", "WR %", "break-even %",
                           "bez nej", "zmena"], riadky), ""]
    telo.append("Delí sa len podľa vlastností, ktoré sú známe **pri vstupe** — inak by to "
                "nebol filter, ale pohľad dozadu.")
    return Section("Ktorá skupina obchodov kazí výsledok", "\n".join(telo),
                   verdict=_skratka(r.get("headline") or ""))


# --------------------------------------------------------------------------- #
# sekcie, ktoré batéria nemá: k jednej stratégii nepatria, k meraniu áno
# --------------------------------------------------------------------------- #


def _matica(store) -> Section:
    """Drží tá myšlienka aj mimo trhu, na ktorom sa ladila?

    Matica sa nespúšťa — hľadá sa tá, ktorá už v histórii je. Behy sú označené značkou
    `settings.matrix.id`, takže ich stačí pozbierať.
    """
    from . import matrix as mx

    skupiny: dict[str, list[dict[str, Any]]] = {}
    for rec in store.all():
        znacka = (rec.get("settings") or {}).get("matrix") or {}
        if znacka.get("id") and rec.get("status") == "done":
            skupiny.setdefault(znacka["id"], []).append(rec)
    if not skupiny:
        return Section("Drží to aj na iných trhoch?", "",
                       gap="v histórii nie je žiadna matica trhov "
                           "(`cli matrix --pairs all --timeframes 3m`)")

    # Najväčšia matica je najsilnejší dôkaz; pri zhode rozhodne novšia.
    matrix_id = max(skupiny, key=lambda k: (len(skupiny[k]), k))
    rows = skupiny[matrix_id]
    goal = rows[0]["settings"]["matrix"].get("goal") or "break_even"
    poradie = mx.rank(rows, goal)
    verdikt = mx.verdict(rows)
    telo = [f"Matica `{matrix_id}` — {len(rows)} behov, okno "
            f"`{rows[0]['settings'].get('timerange')}`.", "",
            "```", mx.table(mx.matrix(poradie)), "```", "", verdikt, "",
            "Prahy v absolútnych bodoch sa prepočítali na ATR referenčného trhu — bez toho "
            "by tabuľka nehovorila „na tomto trhu to nefunguje“, ale „profil je tam "
            "nezmysel“."]
    return Section("Drží to aj na iných trhoch?", "\n".join(telo),
                   verdict=verdikt.split(":")[0])


def _portfolio(records: Sequence[dict[str, Any]], store, strategy: str,
               risk_pct: float) -> Section:
    from . import analytics as an, portfolio as pf

    per: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        t = store.trades(rec["id"])
        if not t:
            continue
        nast = rec["settings"]
        per[f"{nast.get('pair')} {nast.get('timeframe')} {nast.get('timerange')}"] = \
            an.enrich([dict(x) for x in t], store.chart(rec["id"]), strategy)
    if len(per) < 2:
        return Section("Cena rizika", "", gap="na portfólio treba aspoň dva behy")

    r = pf.analyze(per, records=list(records), risk_pct=risk_pct)
    riadky = [[_num(x["risk_pct"], 1, plus=False) + " %", _num(x["return_pct"], 1),
               _num(x.get("cagr_pct"), 1), _num(x["max_drawdown_pct"], 1, plus=False),
               "áno" if x.get("ruin") else "nie"]
              for x in (r.get("risks") or [])]
    telo = []
    if riadky:
        telo += [_tabulka(["riziko na obchod", "zhodnotenie %", "ročne (CAGR) %",
                           "max DD %", "účet na nule"], riadky), ""]

    roky = r.get("by_year") or []
    if roky:
        telo += [_tabulka(["rok", "obchodov", "zhodnotenie %"],
                          [[x["year"], x.get("trades", "—"), _num(x["return_pct"], 1)]
                           for x in roky]), "",
                 "Nesie to jeden dobrý rok, alebo je to rozložené?", ""]

    k = r.get("correlations") or {}
    if k.get("compared"):
        telo += [f"Korelácie mesačných výnosov: priemer **{_num(k.get('mean'), 2)}**, "
                 f"z {k['compared']} dvojíc je {k.get('high', 0)} nad hranicou vysokej "
                 f"korelácie. Portfólio má zmysel len vtedy, keď sa členovia nechovajú "
                 f"rovnako — inak je to jeden beh s väčšou pozíciou a drawdown sa "
                 f"neznižuje, len znásobuje.", ""]

    if r.get("duplicates"):
        telo += ["> Dvojice behov, ktoré pokrývajú ten istý trh v tom istom čase — "
                 "sú to alternatívy jednej veci, nie členovia portfólia:", ""]
        telo += [f"> - {d['a']} × {d['b']} — {d['what']}" for d in r["duplicates"][:5]]
        telo.append("")

    telo.append(r.get("verdict") or "")
    telo += ["", "Veľkosť pozície sa prepočítala z rizika (`riziko = zostatok × risk %`), "
                 "nepreberá sa z behu — inak by sa sčítavali peňaženky, nie stratégie. "
                 "Súbežné pozície sa nekrátia, takže je to horná hranica toho, čo by šlo."]
    return Section("Cena rizika", "\n".join(telo),
                   verdict=_skratka((r.get("verdict") or "").split(":")[0]))


# --------------------------------------------------------------------------- #
# poskladanie dokumentu
# --------------------------------------------------------------------------- #

#: Čo dokument nehovorí — platí to pre každé meranie z historických dát, takže to nie je
#: vygenerované, ale napísané raz a natvrdo. Keby to chýbalo, čísla by vyzerali istejšie,
#: než sú.
LIMITY = (
    "**Je to história, nie budúcnosť.** Všetko dole je popis toho, čo sa stalo. "
    "Ani jeden z testov nehovorí, že to tak bude ďalej.",
    "**Preoptimalizovanie sa z týchto čísel nezistí.** Obchody preladenej konfigurácie "
    "naozaj ziskové boli; chyba býva vo výbere najlepšej z dvesto epoch. Proti tomu "
    "chránia len dáta, ktoré optimalizátor nevidel — u nás päť referenčných okien.",
    "**Fill model je backtestový.** Beží sa s 1m detailom, takže sa vie, či prišiel skôr "
    "stop alebo take profit, ale sklz, čiastočné plnenie ani hĺbka trhu v tom nie sú.",
    "**Poplatok je jedno číslo.** Break-even hovorí, koľko smie burza brať; financovanie "
    "pozícií cez noc ani zmena sadzby v čase v ňom nie sú.",
)


def build(records: Sequence[dict[str, Any]], store, *, strategy: str = "ibs",
          title: str = "", risk_pct: float = 1.0, null_iterations: int = 400,
          command: str = "") -> Paper:
    """Poskladá dokument z behov, ktoré už v histórii sú. Nové backtesty nespúšťa.

    Merá sa `checkup.measure` — tá istá batéria, akú má stratégia vo svojej analytike.
    Keby sa tu meralo vlastným poradím, dva dokumenty o tej istej stratégii by sa nedali
    porovnať a to je presne to, čo majú riešiť.
    """
    from . import analytics as an, checkup as ck, montecarlo as mc

    zaznamy = [r for r in records if r.get("status") == "done"
               and ((r.get("result") or {}).get("trades") or 0) > 0]
    if not zaznamy:
        raise ValueError("žiadne dobehnuté behy s obchodmi")

    obchody: list[dict[str, Any]] = []
    for rec in zaznamy:
        t = store.trades(rec["id"])
        if t:
            obchody += an.enrich([dict(x) for x in t], store.chart(rec["id"]), strategy,
                                 pair=rec["settings"].get("pair") or "",
                                 timeframe=rec["settings"].get("timeframe") or "3m")
    if not obchody:
        raise ValueError("vybrané behy nemajú uložené obchody")

    pary = sorted({r["settings"].get("pair") for r in zaznamy if r["settings"].get("pair")})
    tfs = sorted({r["settings"].get("timeframe") for r in zaznamy if r["settings"].get("timeframe")})
    okna = sorted({r["settings"].get("timerange") for r in zaznamy if r["settings"].get("timerange")})
    # Sviečky sú párové, takže charakter a náhoda idú len na jednom trhu; pri zliatych
    # pároch sa tie sekcie ohlásia ako medzera, nie ako číslo z nesprávneho trhu.
    jeden_par = pary[0] if len(pary) == 1 else ""
    tf = tfs[0] if tfs else "3m"
    fee = float(zaznamy[0]["settings"].get("fee") or 0) * 100
    fee_note = zaznamy[0]["settings"].get("fee_note") or ""

    report = ck.measure(zaznamy, obchody, strategy=strategy, pair=jeden_par, timeframe=tf,
                        fee_pct=fee, fee_note=fee_note,
                        profile=zaznamy[0]["settings"].get("profile") or "",
                        engine=zaznamy[0]["settings"].get("engine") or "freqtrade",
                        risk_ref=mc.sizing_of(zaznamy[-1]), iterations=null_iterations)

    paper = Paper(title=title or f"{strategy.upper()} na {', '.join(pary) or 'histórii'}",
                  strategy=strategy, pairs=pary, timeframes=tfs, windows=okna,
                  runs=zaznamy, command=command,
                  strengths=list(report.get("strengths") or []),
                  weaknesses=list(report.get("weaknesses") or []))
    paper.sections = [
        _charakter(report),
        _po_oknach(zaznamy),
        _interval(report),
        _nahoda(report),
        _slabne(report),
        _analytika(report, len(pary) > 1),
        _matica(store),
        _portfolio(zaznamy, store, strategy, risk_pct),
    ]
    return paper


def render(paper: Paper) -> str:
    """Dokument v tvare, aký používa `docs/merania/`."""
    dnes = date.today().isoformat()
    hotove = [s for s in paper.sections if not s.gap]
    chybaju = [s for s in paper.sections if s.gap]

    out = [f"# {paper.title} — {dnes}", ""]
    out += [f"Zostavené z **{len(paper.runs)} behov** v histórii; nové backtesty sa "
            f"nespúšťali. Stratégia `{paper.strategy}`, trhy "
            f"{', '.join('`' + p + '`' for p in paper.pairs) or '—'}, timeframe "
            f"{', '.join('`' + t + '`' for t in paper.timeframes) or '—'}.", ""]
    if paper.command:
        out += ["```bash", paper.command, "```", ""]

    out += ["## Záver", "",
            "_Sem patrí jedna veta: čo z čísel dole plynie. Nechávam ju prázdnu zámerne —"
            " zhrnutie testov nižšie je zoznam verdiktov, nie záver._", "",
            "## Zhrnutie testov", ""]
    out.append(_tabulka(["test", "verdikt"],
                        [[s.title, s.verdict or "—"] for s in hotove if s.verdict]))
    out.append("")

    # Tie isté vety, aké má stratégia vo svojej ANALYTIKA.md — merací engine je jeden,
    # tak nech aj posudok znie rovnako.
    if paper.strengths or paper.weaknesses:
        if paper.strengths:
            out += ["**V čom je dobrá**", ""] + [f"- {v}" for v in paper.strengths] + [""]
        if paper.weaknesses:
            out += ["**Kde má chyby**", ""] + [f"- {v}" for v in paper.weaknesses] + [""]

    for s in hotove:
        out += [f"## {s.title}", "", s.body, ""]

    if chybaju:
        out += ["## Na čo behy nestačili", "",
                "Toto sa nespočítalo — radšej to nech chýba nahlas, než aby sekcia "
                "obsahovala číslo z jedného okna:", ""]
        out += [f"- **{s.title}** — {s.gap}" for s in chybaju]
        out.append("")

    out += ["## Čo tento dokument nehovorí", ""]
    out += [f"- {v}" for v in LIMITY]
    out += ["", "## Behy, z ktorých je to spočítané", ""]
    out.append(_tabulka(["beh", "trh", "TF", "okno", "obchodov", "poznámka"],
                        [[f"`{r['id']}`", r["settings"].get("pair") or "—",
                          r["settings"].get("timeframe") or "—",
                          r["settings"].get("timerange") or "—",
                          (r.get("result") or {}).get("trades", "—"),
                          (r.get("note") or "").replace("|", "/")[:60]]
                         for r in paper.runs]))
    out.append("")
    return "\n".join(out)


def filename(paper: Paper, name: str = "") -> Path:
    """Cesta v `docs/merania/` v tvare `TEMA_trh_datum.md`."""
    if name:
        return MERANIA_DIR / (name if name.endswith(".md") else name + ".md")
    trh = paper.pairs[0] if len(paper.pairs) == 1 else "viac_trhov"
    trh = trh.replace("/", "").replace(":", "").lower()
    return MERANIA_DIR / f"MERANIE_{paper.strategy}_{trh}_{date.today().isoformat()}.md"


def write(paper: Paper, name: str = "") -> Path:
    cesta = filename(paper, name)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(render(paper), encoding="utf-8")
    return cesta
