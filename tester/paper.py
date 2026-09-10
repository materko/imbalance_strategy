"""Meranie, ktoré sa napíše samo — z behov v histórii do `docs/merania/`.

### Načo to je
Analýz máme sedem a každá odpovedá na inú otázku: charakter stratégie, po oknách, proti
náhode, či edge slabne, ktorá skupina obchodov ho kazí, či drží aj na iných trhoch a čo
stojí riziko. Kým sú roztrúsené po termináli, nikto z nich záver neposkladá — a o týždeň
si už nikto nespomenie, z ktorých behov to bolo.

Toto je ten posledný krok: vezme behy z histórie, pustí nad nimi všetko, čo vieme, a
zapíše datovaný dokument do `docs/merania/` presne v tvare, aký repozitár používa —
čísla **po oknách**, kľúčová metrika **break-even poplatok**, a zoznam behov na konci,
aby sa to dalo zopakovať.

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

__all__ = ["Section", "Paper", "build", "write", "filename"]

#: Menej než toľko obchodov a do dokumentu ide „málo dát“, nie číslo.
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
# sekcie
# --------------------------------------------------------------------------- #


def _po_oknach(records: Sequence[dict[str, Any]]) -> Section:
    """Čísla po referenčných oknách a znamienko v každom z nich.

    Toto je jediná sekcia, ktorá nezlieva obchody: konvencia repozitára je hodnotiť
    **znamienko po rokoch**, nie súčet, lebo jeden dobrý rok utiahne štyri zlé.
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
                       _num(v.get("pnl_pct"), 3), _num(be), _num(v.get("max_drawdown_pct"), 2, plus=False),
                       f"`{rec['id']}`" + (f" (+{len(pre) - 1})" if len(pre) > 1 else "")])

    chybaju = [w for w in REFERENCE_WINDOWS if w not in podla_okna]
    telo = [_tabulka(["okno", "obchodov", "WR %", "PnL %", "break-even %", "max DD %", "beh"], riadky)]
    telo.append("")
    telo.append(f"**Kladné v {kladne} z {spolu} okien.** PnL v % závisí od sizingu a "
                f"peňaženky, break-even nie — preto je rozhodujúci on.")
    if chybaju:
        telo.append("")
        telo.append(f"Chýbajú referenčné okná: {', '.join('`' + w + '`' for w in chybaju)}. "
                    f"Bez nich je záver o stabilite slabší.")
    verdikt = f"kladné v {kladne} z {spolu} okien" if spolu else "nedá sa určiť"
    return Section("Po oknách", "\n".join(telo), verdict=verdikt)


def _charakter(obchody: list[dict[str, Any]], pair: str, timeframe: str) -> Section:
    """Aký typ stratégie to je — a čo je pri tom type normálne.

    Číta sa z `to_dict()`, nie z atribútov: rady „čo je normálne / na čo pozor / čo ladiť“
    nesie archetyp, do ktorého sa meranie zaradilo, nie samotné meranie.
    """
    from . import character as chr_mod

    ch = chr_mod.measure(obchody, pair=pair, timeframe=timeframe).to_dict()
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


def _nahoda(obchody: list[dict[str, Any]], pair: str, timeframe: str,
            iterations: int) -> Section:
    from . import nulltest as nt

    if not pair:
        return Section("Odlíšiteľné od náhody?", "",
                       gap="behy sú z viacerých trhov; náhodné vstupy sa losujú zo "
                           "sviečok jedného páru (`cli nulltest --runs …` na jednom trhu)")
    riadky, prvy = [], None
    for null in nt.NULLS:
        try:
            v = nt.compare(obchody, pair=pair, timeframe=timeframe,
                           iterations=iterations, null=null)
        except (ValueError, FileNotFoundError) as exc:
            return Section("Odlíšiteľné od náhody?", "", gap=f"nedalo sa spočítať: {exc}")
        # Bez sigmy je tabuľka rad pomlčiek — a prázdna tabuľka v dokumente vyzerá ako
        # zmerané nič, hoci sa nemeralo. Radšej medzera nahlas.
        if v.sigma is None:
            return Section("Odlíšiteľné od náhody?", "",
                           gap=v.note or "porovnanie s náhodou sa nedalo spočítať")
        prvy = prvy or v
        riadky.append([f"`{null}`", _num(v.observed), f"{_num(v.mean)} ± {_num(v.sd, 4, plus=False)}",
                       f"{_num(v.sigma, 2)} σ", _num(v.percentile, 1, plus=False)])

    telo = ["Tá istá stratégia, ktorá obchoduje rovnako často, rovnakým smerom a s rovnakým "
            "stopom aj take profitom — len si nevyberá, **kedy** vstúpiť.", "",
            _tabulka(["náhoda", "stratégia", "náhoda", "rozdiel", "percentil"], riadky), "",
            prvy.verdict if prvy else ""]
    return Section("Odlíšiteľné od náhody?", "\n".join(telo),
                   verdict=f"{_num(prvy.sigma, 1)} σ" if prvy and prvy.sigma is not None else "málo dát")


def _slabne(obchody: list[dict[str, Any]]) -> Section:
    from . import decay as dc

    v = dc.analyze(obchody)
    if not v.periods:
        return Section("Slabne edge?", "", gap="obchody nemajú dátumy")
    riadky = [[p.label, p.trades, _num(p.per_month, 1, plus=False),
               _num(p.winrate, 1, plus=False), _num(p.break_even_pct),
               "—" if p.percentile is None else _num(p.percentile, 0, plus=False)]
              for p in v.periods]
    telo = []
    if v.lo is not None:
        telo += [f"Úsek takej dĺžky, akú má posledné obdobie, vyjde tej istej stratégii medzi "
                 f"**{_num(v.lo)}** a **{_num(v.hi)} %** už len preskladaním vlastných "
                 f"obchodov. Preto sa posledné obdobie neporovnáva s celkom: je kratšie, "
                 f"teda aj prirodzene rozkolísanejšie.", ""]
    telo += [_tabulka(["obdobie", "obchodov", "/mes.", "WR %", "break-even %", "percentil"], riadky),
             "", v.note or v.verdict]
    if v.verdict != "MALO DAT":
        telo += ["", "Percentil je test len pre **posledné** obdobie, lebo to bolo vybraté "
                     "vopred; percentily ostatných období sú opis."]
    return Section("Slabne edge?", "\n".join(telo), verdict=v.verdict)


def _analytika(obchody: list[dict[str, Any]], strategy: str, mixed_pairs: bool) -> Section:
    from . import analytics as an

    r = an.analyze(obchody, strategy=strategy)
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
                   verdict=(r.get("headline") or "")[:60])


def _matica(records: Sequence[dict[str, Any]], store) -> Section:
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
    goal = (rows[0]["settings"]["matrix"].get("goal") or "break_even")
    poradie = mx.rank(rows, goal)
    telo = [f"Matica `{matrix_id}` — {len(rows)} behov, okno "
            f"`{rows[0]['settings'].get('timerange')}`.", "",
            "```", mx.table(mx.matrix(poradie)), "```", "",
            mx.verdict(rows), "",
            "Prahy v absolútnych bodoch sa prepočítali na ATR referenčného trhu — bez toho "
            "by tabuľka nehovorila „na tomto trhu to nefunguje“, ale „profil je tam "
            "nezmysel“."]
    return Section("Drží to aj na iných trhoch?", "\n".join(telo),
                   verdict=mx.verdict(rows).split(":")[0])


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
                   verdict=(r.get("verdict") or "").split(":")[0][:60])


def _interval(obchody: list[dict[str, Any]]) -> Section:
    """Interval okolo nameraného break-evenu — je to edge, alebo to bola vzorka?"""
    from . import montecarlo as mc

    if len(obchody) < MIN_TRADES:
        return Section("Interval okolo výsledku", "",
                       gap=f"menej než {MIN_TRADES} obchodov; interval by bol taký široký, "
                           f"že by nič nehovoril")
    r = mc.analyze(list(obchody), iterations=2000)
    be = (r.get("break_even") or {})
    if not be:
        return Section("Interval okolo výsledku", "", gap="Monte Carlo nevrátilo break-even")
    telo = [f"Namerané **{_num(be.get('observed'))} %**; preskladaním vlastných obchodov "
            f"(blokový bootstrap) vyjde medzi **{_num(be.get('lo'))}** a "
            f"**{_num(be.get('hi'))} %**, medián {_num(be.get('median'))} %.", "",
            "Keď dolná hranica leží nad poplatkom burzy, výsledok neunesie len jedna "
            "šťastná séria obchodov."]
    return Section("Interval okolo výsledku", "\n".join(telo),
                   verdict=f"{_num(be.get('lo'))} až {_num(be.get('hi'))} %")


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
    """Poskladá dokument z behov, ktoré už v histórii sú. Nové backtesty nespúšťa."""
    from . import analytics as an

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
    jeden_par = pary[0] if len(pary) == 1 else ""
    tf = tfs[0] if tfs else "3m"

    paper = Paper(title=title or f"{strategy.upper()} na {', '.join(pary) or 'histórii'}",
                  strategy=strategy, pairs=pary, timeframes=tfs, windows=okna,
                  runs=zaznamy, command=command)
    paper.sections = [
        _charakter(obchody, jeden_par, tf),
        _po_oknach(zaznamy),
        _interval(obchody),
        _nahoda(obchody, jeden_par, tf, null_iterations),
        _slabne(obchody),
        _analytika(obchody, strategy, len(pary) > 1),
        _matica(zaznamy, store),
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
    trh = (paper.pairs[0] if len(paper.pairs) == 1 else "viac_trhov")
    trh = trh.replace("/", "").replace(":", "").lower()
    return MERANIA_DIR / f"MERANIE_{paper.strategy}_{trh}_{date.today().isoformat()}.md"


def write(paper: Paper, name: str = "") -> Path:
    cesta = filename(paper, name)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(render(paper), encoding="utf-8")
    return cesta
