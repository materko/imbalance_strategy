"""Základná analytika stratégie: v čom je dobrá, kde má chyby — jedna batéria, jeden dokument.

### Na akú otázku odpovedá
„Aká je tá stratégia?" Nie „koľko zarobil tento beh" — to povie backtest. Odpoveď na
otázku o stratégii vyžaduje vždy tie isté merania v tom istom poradí, lebo inak sa dve
stratégie (ani tá istá o mesiac neskôr) nedajú porovnať. Tento modul je to poradie:

1. **Päť referenčných okien** — drží to znamienko po rokoch, alebo nesie súčet jeden rok?
2. **Charakter** ([character.py](character.py)) — prerazenie, trend, protitrend, scalp?
   Od toho závisí, čo je pri nej normálne a čo je chyba.
3. **Skupiny obchodov** ([analytics.py](analytics.py)) — ktorá časť obchodov výsledok kazí
   a či sa to dá odfiltrovať, alebo je to nastavenie parametra.
4. **Test proti náhode** ([nulltest.py](nulltest.py)) — je ten edge odlíšiteľný od hodu
   mincou, a nie je celý len v tom, *kedy* obchoduje?
5. **Slabne edge?** ([decay.py](decay.py)) — drží to aj dnes, alebo sa zarobilo v prvých
   rokoch a odvtedy stratégia stojí?
6. **Monte Carlo** ([montecarlo.py](montecarlo.py)) — aký široký je interval okolo
   nameraného čísla a čo to robí s účtom.

Nič z toho nie je nové; nové je, že to je **jedna vec s jedným výstupom**, ktorý sa dá
priložiť k stratégii a o mesiac zopakovať. Preto sa výsledok zapisuje ako
`tradebot/strategies/<key>/docs/ANALYTIKA.md` — pri stratégii, nie v spoločnom adresári
meraní: meranie patrí dátumu, toto patrí stratégii.

### Prečo „silné stránky" a „chyby" a nie jedno skóre
Jedno číslo by muselo tvrdiť, že drawdown, počet obchodov a odlíšiteľnosť od náhody sa
dajú spočítať na jednu hromadu. Nedajú — stratégia s malým drawdownom a bez edge je iný
prípad než stratégia s edge a drawdownom 40 %, hoci „skóre" by mali podobné. Preto je
výstup dva zoznamy viet, každá s číslom, z ktorého vznikla: `verdicts()` je pravidlá nad
zmeranými hodnotami, rovnako ako zaradenie charakteru — má byť vidieť **prečo**.

### Čo tento modul nerobí
Nespúšťa backtesty (to je `cli checkup`, ktorý mu behy podá) a nič nehľadá: nie je to
ani hyperopt, ani mriežka. Je to fotka stratégie, aká je dnes — a keď sa niečo z nej
nepáči, ďalší krok je sweep, hyperopt alebo matica trhov, nie prepisovanie tejto fotky.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from tradebot.strategies import get_spec

from .hyperopt import REFERENCE_WINDOWS

__all__ = [
    "REFERENCE_WINDOWS", "DOC_NAME", "MIN_TRADES",
    "POSUDOK_OTAZKY", "POSUDOK_PLACEHOLDER", "POSUDOK_START", "POSUDOK_END",
    "doc_path", "window_rows", "measure", "verdicts", "fingerprint", "extract_posudok",
    "markdown", "table",
]

#: Meno dokumentu pri stratégii. Jedno pre všetky, aby sa dal nájsť bez hľadania.
DOC_NAME = "ANALYTIKA.md"

#: Pod týmto počtom obchodov (spolu, cez všetky okná) je celá batéria anekdota.
#: Rovnaká hranica ako v Monte Carle — pod ňou je interval taký široký, že nič nehovorí.
MIN_TRADES = 30

#: Max drawdown, nad ktorým sa to už nedá vydržať s bežným účtom (% z vrcholu).
DD_LIMIT = 25.0


def doc_path(strategy: str) -> Path:
    """Kam patrí analytika stratégie — `tradebot/strategies/<key>/docs/ANALYTIKA.md`."""
    spec = get_spec(strategy)
    return spec.profile_dir.parent / "docs" / DOC_NAME


# --------------------------------------------------------------------------- #
# okná
# --------------------------------------------------------------------------- #


def window_rows(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Behy referenčných okien ako riadky tabuľky — v poradí, v akom bežali."""
    rows = []
    for rec in records:
        settings = rec.get("settings") or {}
        result = rec.get("result") or {}
        rows.append({
            "timerange": settings.get("timerange") or "?",
            "run_id": rec.get("id") or "?",
            "status": rec.get("status") or "?",
            "trades": result.get("trades"),
            "pnl_pct": result.get("pnl_pct"),
            "break_even_pct": result.get("break_even_pct"),
            "max_dd_pct": result.get("max_drawdown_pct"),
            "winrate": result.get("winrate"),
            "profit_factor": result.get("profit_factor"),
            "warning": result.get("warning"),
            "error": rec.get("error"),
        })
    return rows


def _positive(rows: Sequence[dict[str, Any]]) -> tuple[int, int]:
    """(koľko okien skončilo v pluse, koľko okien vôbec dobehlo)."""
    hotove = [r for r in rows if r["status"] == "done" and r["pnl_pct"] is not None]
    return sum(1 for r in hotove if r["pnl_pct"] > 0), len(hotove)


# --------------------------------------------------------------------------- #
# batéria
# --------------------------------------------------------------------------- #


def measure(records: Sequence[dict[str, Any]], trades: Sequence[dict[str, Any]], *,
            strategy: str, pair: str, timeframe: str, fee_pct: float = 0.05,
            profile: str = "", engine: str = "freqtrade", account: float = 10_000.0,
            risk_ref: float | None = None, iterations: int = 1000,
            mc_iterations: int = 10_000, seed: int = 12345) -> dict[str, Any]:
    """Celá batéria nad hotovými behmi. `trades` sú obchody zo všetkých okien spolu.

    Obchody musia prísť **obohatené** (`analytics.enrich` s kresbami behu) — vzdialenosť
    stopu a plánovaný RR sú v kresbách, nie v `trades.json`, a bez nich sú to dve
    vlastnosti, ktoré by v analytike ticho chýbali.
    """
    from . import analytics as an, character as ch, decay as dc, montecarlo as mc, nulltest as nt

    spec = get_spec(strategy)
    rows = window_rows(records)
    kladne, hotove = _positive(rows)

    report: dict[str, Any] = {
        "strategy": strategy,
        "title": spec.title,
        "pair": pair,
        "timeframe": timeframe,
        "engine": engine,
        "profile": profile,
        "fee_pct": fee_pct,
        "account": account,
        "windows": rows,
        "years_positive": kladne,
        "years_done": hotove,
        "trades": len(trades),
        "break_even_pct": an.break_even_pct(list(trades)) if trades else None,
        "character": None,
        "analytics": None,
        "null": {},
        "decay": None,
        "montecarlo": None,
    }
    if not trades:
        report["strengths"], report["weaknesses"] = [], [
            "Žiadne obchody: batéria nemá z čoho merať. Pozri log behov (`cli show <id>`) — "
            "typicky je malá peňaženka na profil s pevným sizingom, alebo okno bez dát."]
        return report

    report["character"] = ch.measure(list(trades), pair=pair, timeframe=timeframe).to_dict()
    report["analytics"] = an.analyze(list(trades), strategy=strategy)
    for null in nt.NULLS:
        report["null"][null] = nt.compare(list(trades), pair=pair, timeframe=timeframe,
                                          iterations=iterations, null=null, seed=seed).to_dict()
    # Obchody z piatich okien idú po sebe, takže delenie kalendára na obdobia dáva zmysel.
    report["decay"] = dc.analyze(list(trades), seed=seed).to_dict()
    report["montecarlo"] = mc.analyze(list(trades), fee_pct=fee_pct, iterations=mc_iterations,
                                      seed=0, account=account, risk_ref=risk_ref,
                                      risk=risk_ref)

    silne, slabe = verdicts(report)
    report["strengths"], report["weaknesses"] = silne, slabe
    return report


def verdicts(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Dva zoznamy viet: v čom je dobrá a kde má chyby. Pravidlá nad zmeranými číslami.

    Každá veta nesie číslo, z ktorého vznikla — bez neho by to bol názor. Čo sa nedalo
    zmerať, sa nehodnotí: chýbajúca hodnota nie je ani plus, ani mínus.
    """
    silne: list[str] = []
    slabe: list[str] = []
    fee = float(report.get("fee_pct") or 0.0)
    rows = report["windows"]
    kladne, hotove = report["years_positive"], report["years_done"]

    # -- okná: znamienko po rokoch je dôležitejšie než súčet ------------------- #
    if hotove:
        stratove = [r["timerange"] for r in rows
                    if r["status"] == "done" and (r["pnl_pct"] or 0) <= 0]
        veta = f"zisková v {kladne} z {hotove} referenčných okien"
        if not stratove:
            silne.append(veta)
        else:
            slabe.append(f"{veta} ({', '.join(stratove)} v strate)")
    zle = [r for r in rows if r["status"] != "done"]
    if zle:
        slabe.append(f"{len(zle)} z {len(rows)} okien vôbec nedobehlo "
                     f"({', '.join(r['timerange'] for r in zle)}) — bez nich je obraz neúplný")

    # -- vzorka ---------------------------------------------------------------- #
    n = report["trades"]
    if n < MIN_TRADES:
        slabe.append(f"len {n} obchodov spolu: pod {MIN_TRADES} je každý interval taký široký, "
                     "že závery z neho sú anekdota")
    elif n >= 200:
        silne.append(f"{n} obchodov spolu — na štatistiku dosť")

    # -- edge oproti poplatku -------------------------------------------------- #
    be = report.get("break_even_pct")
    if be is not None and fee > 0:
        if be > fee:
            silne.append(f"break-even {be:.4f} % je nad poplatkom {fee:.4f} % "
                         f"(rezerva {be - fee:+.4f} bodu)")
        else:
            slabe.append(f"break-even {be:.4f} % je pod poplatkom {fee:.4f} % — "
                         "pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek")

    mcr = report.get("montecarlo") or {}
    if mcr:
        p = mcr["break_even"]["p_above_fee"]
        if p >= 0.95:
            silne.append(f"edge nad poplatkom v {100 * p:.0f} % bootstrapových vzoriek")
        elif fee > 0:
            slabe.append(f"edge nad poplatkom len v {100 * p:.0f} % vzoriek — v zvyšku by "
                         "burza zobrala viac, než stratégia zarobí")
        dd = mcr["account"]["drawdown_pct"]
        if dd["p95"] >= DD_LIMIT:
            slabe.append(f"95. percentil max drawdownu {dd['p95']:.1f} % (namerané "
                         f"{dd['median']:.1f} % medián) — na účet to treba mať")
        elif dd["p95"] > 0:
            silne.append(f"drawdown drží: 95. percentil {dd['p95']:.1f} %")
        if mcr["account"]["p_ruin"] > 0.01:
            slabe.append(f"pravdepodobnosť ruiny účtu {100 * mcr['account']['p_ruin']:.1f} % "
                         "pri riziku, s akým beh bežal")

    # -- náhoda ---------------------------------------------------------------- #
    nulls = report.get("null") or {}
    anytime, session = nulls.get("anytime") or {}, nulls.get("session") or {}
    sig_a, sig_s = anytime.get("sigma"), session.get("sigma")
    if sig_a is not None:
        if sig_a >= 2.0:
            silne.append(f"odlíšiteľná od náhody ({sig_a:+.1f} sigma proti náhodnému vstupu)")
        elif sig_a <= 0:
            slabe.append(f"nie je lepšia než náhodný vstup za tých istých pravidiel "
                         f"({sig_a:+.1f} sigma) — výber vstupu nepridáva nič")
        else:
            slabe.append(f"proti náhode len {sig_a:+.1f} sigma: náznak, nie dôkaz")
    if sig_a is not None and sig_s is not None and sig_a - sig_s > 1.0:
        slabe.append(f"proti náhode v tých istých hodinách je rozdiel podstatne menší "
                     f"({sig_s:+.1f} vs {sig_a:+.1f} sigma) — veľká časť edge je v tom, "
                     "KEDY obchoduje, nie v tom, čo si vyberá")

    # -- slabne edge? ---------------------------------------------------------- #
    # Verdikt aj vetu s číslami vyrába `tester.decay`; tu sa len rozhoduje, na ktorú
    # stranu patria. „MALO DAT" nie je ani plus, ani mínus — to už povedal počet obchodov.
    dec = report.get("decay") or {}
    posledne = (dec.get("periods") or [{}])[-1]
    # „Drží" je silná stránka len vtedy, keď je čo držať: stabilne záporný edge drží tiež.
    ma_edge = be is not None and (fee <= 0 or be > fee)
    if dec.get("verdict") == "DRZI" and ma_edge:
        silne.append(f"edge drží aj v poslednom období ({posledne.get('label', '?')} na "
                     f"{(posledne.get('percentile') or 0):.0f}. percentile toho, čo stratégia "
                     "vyrobí sama od seba)")
    elif dec.get("verdict") in ("SLABNE", "POZOR NA TREND"):
        slabe.append(dec.get("note") or dec["verdict"])
    elif dec.get("verdict") == "ZLEPSUJE SA" and ma_edge:
        silne.append(f"posledné obdobie ({posledne.get('label', '?')}) je nad horným "
                     "intervalom vlastnej minulosti — dôvod zvyšovať riziko to ale nie je, "
                     "rovnako dobre to môže byť priaznivý režim")

    # -- charakter ------------------------------------------------------------- #
    char = report.get("character") or {}
    if char.get("title"):
        veta = f"charakter: {char['title'].lower()} (istota {char.get('confidence')})"
        if char.get("confidence") == "dobrá":
            silne.append(veta + " — vie sa teda, čo je pri nej normálne a čo ladiť")
        else:
            slabe.append(veta + " — zaradenie je neisté, závery o tom, čo je pri nej "
                                "normálne, treba brať opatrne")
    exits = char.get("exits") or {}
    for dovod, podiel in exits.items():
        if dovod in ("session_end", "force_exit") and podiel >= 20:
            slabe.append(f"{podiel:g} % obchodov končí na čase ({dovod}), nie na pláne — "
                         "to je nastavenie okna seansy, nie vlastnosť vstupu")

    # -- skupiny obchodov ------------------------------------------------------ #
    an_report = report.get("analytics") or {}
    splits = an_report.get("splits") or []
    if splits:
        najhorsi = splits[0]
        dopad = najhorsi.get("best_impact")
        skupina = (najhorsi.get("buckets") or [{}])[0]
        if dopad is not None and dopad >= 0.01:
            slabe.append(
                f"najhoršia skupina '{skupina.get('label')}' vlastnosti "
                f"'{najhorsi.get('title')}': {skupina.get('trades')} obchodov "
                f"({skupina.get('share_pct')} %), bez nej by break-even bol o {dopad:+.4f} lepší"
                + (f" (riadi `{najhorsi.get('param')}`)" if najhorsi.get("param") else ""))
        else:
            silne.append("žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — "
                         "niet čo filtrovať, ladiť sa dá len parametrami")
    return silne, slabe


# --------------------------------------------------------------------------- #
# posudok od AI
# --------------------------------------------------------------------------- #

#: Značky, medzi ktorými žije posudok. Všetko ostatné v dokumente je generované, takže
#: pri prepočte sa prepíše — posudok je jediná časť, ktorú generátor prenesie ďalej.
POSUDOK_START = "<!-- POSUDOK cisla="
POSUDOK_END = "<!-- POSUDOK KONIEC -->"

#: Text, ktorý generátor vloží namiesto chýbajúceho posudku. Pri ďalšom prepočte sa
#: nesmie prevziať ako posudok — inak by dokument tvrdil, že posudok má.
POSUDOK_PLACEHOLDER = "_(zatiaľ nenapísaný)_"

#: Na čo má posudok odpovedať. Zámerne to nie sú otázky na čísla (tie sú v dokumente
#: vyššie), ale na to, čo z čísel nevyplýva samo: kam stratégia patrí, čo jej chýba
#: a či sa jej vôbec oplatí venovať ďalší čas.
POSUDOK_OTAZKY: tuple[str, ...] = (
    "**Na čo sa to hodí a na čo nie** — trh, timeframe, režim, veľkosť účtu; kde by to "
    "isté číslo znamenalo niečo iné.",
    "**Má to potenciál?** Čo z čísel hovorí, že za tým je skutočný jav, a čo hovorí, "
    "že je to vlastnosť vzorky.",
    "**Čo treba dorobiť** v samotnej stratégii — filtre, výstupy, sizing, sviatky "
    "a seansy, chýbajúce parametre.",
    "**Čo otestovať ďalej** — konkrétne príkazy (`cli sweep`, `cli matrix`, "
    "`cli hyperopt`, druhý engine) a čo by ich výsledok rozhodol.",
    "**Je to použiteľné, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte "
    "uvidíme\" je odpoveď len vtedy, keď je za ňou konkrétny test.",
    "**Čo by som pridal** — nápad, ktorý v stratégii nie je a z týchto čísel dáva zmysel.",
)


def fingerprint(report: dict[str, Any]) -> str:
    """Odtlačok čísel, ku ktorým posudok patrí — aby bolo vidieť, keď sa rozišli.

    Posudok je text o konkrétnej vzorke. Keď sa prepočíta na iných dátach, starý text
    v dokumente ostane (je to práca navyše ho písať znova), ale musí byť **označený**,
    inak by o mesiac nikto nevedel, či hovorí o týchto číslach alebo o dávnych.
    """
    import hashlib

    kusky = [report.get("strategy", ""), report.get("pair", ""), report.get("timeframe", ""),
             str(report.get("trades")), str(report.get("break_even_pct"))]
    for r in report.get("windows") or ():
        kusky += [r.get("timerange", ""), str(r.get("trades")), str(r.get("pnl_pct"))]
    return hashlib.sha1("|".join(kusky).encode("utf-8")).hexdigest()[:8]


def extract_posudok(text: str) -> tuple[str, str]:
    """(text posudku, odtlačok čísel, ku ktorým bol napísaný) z existujúceho dokumentu."""
    zaciatok = text.find(POSUDOK_START)
    koniec = text.find(POSUDOK_END)
    if zaciatok < 0 or koniec < 0 or koniec < zaciatok:
        return "", ""
    hlavicka = text[zaciatok:text.find("-->", zaciatok) + 3]
    odtlacok = hlavicka[len(POSUDOK_START):].split()[0].strip(" -->") if hlavicka else ""
    telo = text[text.find("-->", zaciatok) + 3:koniec].strip()
    if telo == POSUDOK_PLACEHOLDER:
        return "", ""     # výzva napísať posudok nie je posudok
    return telo, odtlacok


def _posudok_block(report: dict[str, Any], posudok: str, stamp: str) -> list[str]:
    """Sekcia posudku — buď prenesený text, alebo zadanie pre AI, ktorá ho napíše."""
    teraz = fingerprint(report)
    out = ["", "## Posudok (AI)", ""]
    if posudok.strip() and stamp == teraz:
        out += [POSUDOK_START + teraz + " -->", "", posudok, "", POSUDOK_END]
        return out
    if posudok.strip():
        out += [f"> **Posudok je starší než čísla** (písal sa k vzorke `{stamp or '?'}`, "
                f"tu je `{teraz}`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.",
                ""]
        out += [POSUDOK_START + (stamp or "?") + " -->", "", posudok, "", POSUDOK_END]
        return out
    out += ["Chýba. Napíše ho AI: prečíta čísla vyššie a odpovie na týchto šesť otázok. "
            "Text patrí **medzi značky** nižšie, aby ho ďalší `cli checkup` preniesol ďalej.",
            ""]
    out += [f"{i}. {q}" for i, q in enumerate(POSUDOK_OTAZKY, 1)]
    out += [POSUDOK_START + teraz + " -->", "", POSUDOK_PLACEHOLDER, "", POSUDOK_END]
    return out

# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def _num(value: Any, digits: int = 2, plus: bool = False) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:{'+' if plus else ''}.{digits}f}"
    return str(value)


def _windows_table(rows: Sequence[dict[str, Any]]) -> list[list[str]]:
    """Riadky tabuľky okien ako zoznam buniek — spoločné pre konzolu aj markdown."""
    out = []
    for r in rows:
        if r["status"] != "done":
            out.append([r["timerange"], r["status"], "-", "-", "-", "-", r["run_id"]])
            continue
        out.append([r["timerange"], str(r["trades"] if r["trades"] is not None else "-"),
                    _num(r["pnl_pct"], 2, plus=True), _num(r["break_even_pct"], 4),
                    _num(r["max_dd_pct"], 1), _num(r["winrate"], 1), r["run_id"]])
    return out


_HEAD = ("okno", "obchodov", "PnL %", "break-even %", "max DD %", "WR %", "beh")

#: Koľko skupín jednej vlastnosti sa vojde do dokumentu, kým prestane byť čitateľný.
#: Skupiny sú zoradené od najhoršej, takže zaujímavé sú okraje — stred sa dá vynechať
#: (celé rozdelenie je vždy v behu, `cli show`, a na karte Analytika vo webapp).
MAX_BUCKETS = 8


def _buckets(split: dict[str, Any]) -> list[dict[str, Any] | None]:
    """Skupiny do tabuľky: buď všetky, alebo najhoršie a najlepšie a `None` namiesto stredu."""
    buckets = split["buckets"]
    if len(buckets) <= MAX_BUCKETS:
        return list(buckets)
    kraj = MAX_BUCKETS // 2
    return list(buckets[:kraj]) + [None] + list(buckets[-kraj:])


def table(report: dict[str, Any]) -> str:
    """Batéria pre konzolu. Hlavičky sú ASCII, vety verdiktu idú tak, ako sú."""
    lines = [f"=== zakladna analytika: {report['title']} ({report['strategy']}) ===",
             f"{report['pair']} {report['timeframe']}, engine {report['engine']}, "
             f"poplatok {report['fee_pct']:.4f} % na stranu"
             + (f", profil {report['profile']}" if report.get("profile") else "")]
    lines.append("")
    lines.append(f"{_HEAD[0]:<22}{_HEAD[1]:>9}{_HEAD[2]:>9}{_HEAD[3]:>14}{_HEAD[4]:>10}{_HEAD[5]:>7}")
    for cells in _windows_table(report["windows"]):
        lines.append(f"{cells[0]:<22}{cells[1]:>9}{cells[2]:>9}{cells[3]:>14}"
                     f"{cells[4]:>10}{cells[5]:>7}")
    lines.append("")
    lines.append(f"ziskova v {report['years_positive']} z {report['years_done']} okien, "
                 f"obchodov spolu {report['trades']}, break-even {_num(report.get('break_even_pct'), 4)} %")
    dec = report.get("decay") or {}
    if dec.get("verdict"):
        lines.append(f"slabne edge? {dec['verdict']}")

    lines += ["", "V COM JE DOBRA"]
    lines += [f"  + {v}" for v in report.get("strengths") or ["(nic, co by vycnievalo)"]]
    lines += ["", "KDE MA CHYBY"]
    lines += [f"  - {v}" for v in report.get("weaknesses") or ["(nic, co by vycnievalo)"]]
    return "\n".join(lines)


def markdown(report: dict[str, Any], *, command: str = "", generated: datetime | None = None,
             posudok: str = "", posudok_stamp: str = "") -> str:
    """Dokument, ktorý sa zapíše k stratégii. Píše sa celý znova — je to fotka, nie denník.

    Jediná výnimka je **posudok**: text, ktorý k číslam napísala AI. Ten sa prenáša
    z predošlej verzie dokumentu (`extract_posudok`), lebo je to jediná časť, ktorú
    generátor vyrobiť nevie — a keď sa čísla medzitým zmenili, označí sa za starý.
    """
    kedy = (generated or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    char = report.get("character") or {}
    mcr = report.get("montecarlo") or {}
    nulls = report.get("null") or {}

    out = [f"# Základná analytika — {report['title']} (`{report['strategy']}`)", "",
           f"Zmerané {kedy} na `{report['pair']}` {report['timeframe']}, engine "
           f"`{report['engine']}`, poplatok {report['fee_pct']:.4f} % na stranu"
           + (f", profil `{report['profile']}`" if report.get("profile") else "") + ".",
           "",
           "Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa "
           "stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).",
           ""]
    if command:
        out += ["```bash", command, "```", ""]

    out += ["## V čom je dobrá", ""]
    out += [f"- {v}" for v in report.get("strengths") or ["_nič, čo by vyčnievalo_"]]
    out += ["", "## Kde má chyby", ""]
    out += [f"- {v}" for v in report.get("weaknesses") or ["_nič, čo by vyčnievalo_"]]

    out += ["", "## Päť referenčných okien", "",
            "Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.",
            "",
            "| " + " | ".join(_HEAD) + " |",
            "|" + "---|" * len(_HEAD)]
    for cells in _windows_table(report["windows"]):
        out.append("| " + " | ".join(f"`{c}`" if i == len(cells) - 1 else str(c)
                                     for i, c in enumerate(cells)) + " |")
    out += ["", f"Zisková v **{report['years_positive']} z {report['years_done']}** okien, "
                f"obchodov spolu {report['trades']}, break-even celkom "
                f"{_num(report.get('break_even_pct'), 4)} %."]

    if char.get("title"):
        out += ["", "## Charakter", "",
                f"**{char['title']}** (istota {char.get('confidence')})", ""]
        out += [f"- {d}" for d in char.get("evidence") or []]
        out += ["", f"- **Čo je normálne:** {char.get('normal', '')}",
                f"- **Na čo pozor:** {char.get('watch', '')}",
                f"- **Čo ladiť:** {char.get('tune', '')}"]
        if char.get("exits"):
            out += ["", "Výstupy: " + ", ".join(f"`{k}` {v:g} %" for k, v in char["exits"].items())]
        out += ["", "Čo z čísel vyplýva pre tento typ: "
                    "[docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md)."]

    an_report = report.get("analytics") or {}
    if an_report.get("headline") or an_report.get("splits"):
        out += ["", "## Ktorá skupina obchodov kazí výsledok", "",
                an_report.get("headline", ""), ""]
        for s in (an_report.get("splits") or [])[:3]:
            hlavicka = f"**{s['title']}**" + (f" (riadi `{s['param']}`)" if s.get("param") else "")
            out += ["", hlavicka, "",
                    "| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |",
                    "|---|---|---|---|---|---|---|"]
            for b in _buckets(s):
                if b is None:      # vynechaný stred tabuľky
                    out.append("| … | | | | | | |")
                    continue
                out.append(f"| {b['label']} | {b['trades']} | {b['share_pct']:.1f} % | "
                           f"{_num(b['winrate'], 1)} | {_num(b['break_even_pct'], 4)} | "
                           f"{_num(b['without_pct'], 4)} | {_num(b['impact'], 4, plus=True)} |")
        if an_report.get("tunable"):
            out += ["", "Parametre, ktorými sa dá s tým niečo spraviť: "
                    + ", ".join(f"`{p}`" for p in an_report["tunable"]) + "."]

    if nulls:
        out += ["", "## Je ten edge odlíšiteľný od náhody", "",
                "Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, "
                "s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, "
                "nie nad nulou.", "",
                "| náhoda | break-even stratégie | break-even náhody | sigma | percentil |",
                "|---|---|---|---|---|"]
        for kluc, r in nulls.items():
            if r.get("sigma") is None or r.get("observed") is None:
                out.append(f"| {kluc} | – | – | – | nedalo sa spočítať |")
                continue
            out.append(f"| {kluc} ({r.get('null_note', '')}) | {_num(r['observed'], 4)} % | "
                       f"{_num(r['mean'], 4)} % ± {_num(r['sd'], 4)} | "
                       f"{_num(r['sigma'], 2, plus=True)} | {_num(r['percentile'], 1)} |")
        prvy = next(iter(nulls.values()), {})
        if prvy.get("verdict"):
            out += ["", prvy["verdict"]]

    dec = report.get("decay") or {}
    if dec.get("periods"):
        out += ["", "## Slabne edge?", "",
                "Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu "
                "(kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov "
                "tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.",
                "",
                "| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |",
                "|---|---|---|---|---|---|"]
        for per in dec["periods"]:
            out.append(f"| {per['label']} | {per['trades']} | {_num(per['per_month'], 1)} | "
                       f"{_num(per['winrate'], 1)} | {_num(per['break_even_pct'], 4)} | "
                       f"{_num(per['percentile'], 0)} |")
        if dec.get("lo") is not None:
            out += ["", f"Hranice pre úsek veľkosti posledného obdobia: {dec['lo']:+.4f} až "
                        f"{dec['hi']:+.4f} % (medián {_num(dec.get('median'), 4)})."]
        # `note` začína tým istým verdiktom; v dokumente by stálo dvakrát za sebou.
        znacka = dec.get("verdict", "?")
        poznamka = (dec.get("note") or "").removeprefix(znacka + ":").strip()
        out += ["", f"**{znacka}** — {poznamka}"]

    if mcr:
        be, acc = mcr["break_even"], mcr["account"]
        opakovani = f"{mcr['iterations']:,}".replace(",", " ")
        dd = acc["drawdown_pct"]
        out += ["", "## Interval okolo výsledku a čo to robí s účtom", "",
                f"Bootstrap po blokoch {mcr['block']} obchodov, {opakovani} opakovaní.", "",
                f"- break-even: namerané **{be['observed']:.4f} %**, medián {be['median']:.4f} %, "
                f"{mcr['ci']:.0f} % interval {be['lo']:.4f}–{be['hi']:.4f} %",
                f"- P(edge > poplatok) = **{100 * be['p_above_fee']:.1f} %**",
                f"- max drawdown: medián {dd['median']:.1f} %, 95. percentil {dd['p95']:.1f} %, "
                f"najhorší {dd['max']:.1f} %",
                f"- najdlhšia séria strát: medián {acc['losing_streak']['median']:.0f}, "
                f"95. percentil {acc['losing_streak']['p95']:.0f} obchodov",
                f"- pravdepodobnosť ruiny účtu: {100 * acc['p_ruin']:.1f} %"]
        if acc.get("advice"):
            a = acc["advice"]
            riziko = f"{a['risk']:,.0f}".replace(",", " ")
            ucet = f"{acc['start']:,.0f}".replace(",", " ")
            out.append(f"- aby 95 % ciest zostalo nad −{a['limit']:.0f} %, riskuj najviac "
                       f"**{riziko}** na obchod pri účte {ucet}")
        out += ["", "Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. "
                    "Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel."]

    out += ["", "## Čo tu nie je", "",
            "- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, "
            "povie matica: `cli matrix --pairs all --timeframes 3m`.",
            "- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill "
            "model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).",
            "- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je "
            "`cli sweep` a `cli hyperopt`."]
    out += _posudok_block(report, posudok, posudok_stamp)
    out.append("")
    return "\n".join(out)
