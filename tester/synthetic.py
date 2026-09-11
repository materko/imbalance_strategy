"""Syntetický trh — pevný, opakovateľný, bez akejkoľvek štruktúry.

### Na akú otázku odpovedá
`tester.nulltest` losuje **vstupy** na skutočnom trhu a pýta sa, či je výber lepší než
náhoda. Toto je opačná otázka: stratégia ostane nezmenená a náhodný je **trh**. Keď na
trhu, v ktorom žiadna štruktúra nie je, stratégia stále „nájde edge“, tá výhoda nevznikla
na trhu — vznikla v našom backteste. Je to teda hlavne **detektor chýb enginu**: pohľad
dopredu, fill model, ktorý rozhoduje sporné bary v náš prospech, sizing, ktorý zvýhodňuje
výhry. Také chyby nič iné v repozitári nezachytí, lebo na skutočných dátach vyzerajú ako
zisk.

### Ako sa robí
Nie je to náhodná prechádzka s vymyslenou volatilitou — tá by sa dala odmietnuť tým, že
„nevyzerá ako trh“. Berú sa **skutočné 1m bary zdrojového trhu** a:

1. z každého baru sa zapamätá jeho vnútorný tvar (kde je open, high a low voči close),
2. spočítajú sa výnosy medzi barmi,
3. výnosy sa **premiešajú po blokoch** (`block` barov spolu) a z nich sa poskladá nová
   cenová cesta; každému baru sa vráti jeho pôvodný tvar.

Rozdelenie výnosov, tvary barov aj typická volatilita teda ostávajú presne tie isté ako na
zdrojovom trhu. Čo zmizne, je **poradie** — teda trendy, úrovne, návraty, všetko, na čom
môže stáť skutočná výhoda. Blok drží krátke zhluky volatility pokope, aby trh nevyzeral
neprirodzene hladko.

### Prečo je pevný
Trh sa vygeneruje **raz** a ostáva. Keby sa robil pri každom teste nanovo, dva výsledky by
sa nedali porovnať a nedalo by sa povedať „minule to tu urobilo 12 obchodov, dnes 40“.
Preto je recept (zdroj, okno, metóda, blok, seed) uložený v registri a dáta sa
pregenerujú len na výslovný príkaz. Seed robí generovanie deterministickým, takže z receptu
vznikne bit po bite ten istý súbor — a `sha256` v registri to overí.

### Ako to čítať
Na syntetickom trhu má vyjsť **nula**: break-even okolo nuly, žiadna súvislá krivka.
Keď vyjde zreteľne kladný, je to nález — ale nález o **nás**, nie o stratégii. Naopak
záporný výsledok nič nedokazuje: poplatky a spread berú aj na náhodnom trhu.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from tradebot.core.types import INSTRUMENTS, SYNTHETIC_REGISTRY, InstrumentSpec, synthetic_specs

__all__ = ["Recipe", "recipes", "build", "verify", "SYNTHETIC_REGISTRY"]

#: Koľko barov drží blok pokope. Hodina na 1m: dosť na to, aby zhluky volatility prežili,
#: málo na to, aby v dátach ostal trend dlhší než hodina.
DEFAULT_BLOCK = 60

#: Seed. Je súčasťou receptu, takže z toho istého receptu vznikne ten istý trh.
DEFAULT_SEED = 20260910


@dataclass(frozen=True)
class Recipe:
    """Recept na syntetický trh. Uložený v registri, aby sa dal zopakovať."""

    key: str
    symbol: str
    source_pair: str
    timerange: str
    block: int = DEFAULT_BLOCK
    seed: int = DEFAULT_SEED
    method: str = "block_shuffle"
    #: kontrolný súčet vygenerovaného 1m súboru — overí, že dáta sedia s receptom
    sha256: str = ""
    created: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def recipes(path: Path | None = None) -> dict[str, Recipe]:
    """Recepty z registra. Kľúče začínajúce `_` sú komentáre."""
    src = Path(path or SYNTHETIC_REGISTRY)
    if not src.exists():
        return {}
    raw = json.loads(src.read_text(encoding="utf-8"))
    out = {}
    for key, row in raw.items():
        if key.startswith("_"):
            continue
        polia = {k: v for k, v in row.items() if k in Recipe.__dataclass_fields__}
        polia.pop("key", None)
        out[key] = Recipe(key=key, **polia)
    return out


def _write_recipe(recipe: Recipe, like: str, path: Path | None = None) -> None:
    """Zapíše recept do registra. Ostatné recepty ostanú, ako boli."""
    src = Path(path or SYNTHETIC_REGISTRY)
    raw = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
    raw.setdefault("_comment", [
        "Recepty na synteticke trhy (tester/synthetic.py). Je to RECEPT, nie data:",
        "zdroj, okno, metoda, blok a seed, z ktorych sa trh da vygenerovat znova bit po",
        "bite. Sviecky sa necommituju - su velke a daju sa kedykolvek vyrobit.",
        "`like` je klucom instrumentu, od ktoreho sa preberu vlastnosti trhu (tick,",
        "hodnota bodu, mena, naklad). `sha256` je kontrolny sucet 1m suboru.",
        "Pregenerovat sa da len vyslovne: `python -m tester.synthetic build <kluc> --force`.",
        "Prepisanie znamena, ze skorsie behy na tomto trhu uz nie su porovnatelne.",
    ])
    raw[recipe.key] = {**recipe.to_dict(), "like": like}
    raw[recipe.key].pop("key", None)
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for kus in iter(lambda: f.read(1 << 20), b""):
            h.update(kus)
    return h.hexdigest()


def data_file(key: str) -> Path:
    """Kam patria 1m sviečky syntetického trhu."""
    from . import engines

    inst = INSTRUMENTS.get(key)
    if inst is None:
        raise KeyError(f"syntetický trh {key!r} nie je v registri")
    return engines.one_minute_file(inst)


def shuffle_bars(df, *, block: int = DEFAULT_BLOCK, seed: int = DEFAULT_SEED):
    """Premieša bary po blokoch a poskladá z nich novú cenovú cestu.

    Zachová sa: rozdelenie výnosov, tvar každého baru (kde bol open, high a low voči
    close), objem aj časová os. Zmizne poradie — teda všetko, na čom môže stáť výhoda.
    """
    import numpy as np
    import pandas as pd

    if len(df) < block * 4:
        raise ValueError(f"na premiešanie treba aspoň {block * 4} barov, je ich {len(df)}")

    close = df["close"].to_numpy(dtype=float)
    # Tvar baru sa drží ako pomer k close, nie ako rozdiel — na inej cenovej úrovni má
    # potom bar rovnakú relatívnu veľkosť, nie rovnakú v dolároch.
    tvar = np.stack([df["open"].to_numpy(dtype=float) / close,
                     df["high"].to_numpy(dtype=float) / close,
                     df["low"].to_numpy(dtype=float) / close], axis=1)
    objem = df["volume"].to_numpy(dtype=float)

    # Výnosov je o jeden menej než barov a premiešava sa **presne táto množina** — žiadny
    # sa nezahodí ani nepridá. Vďaka tomu má nový trh nielen to isté rozdelenie výnosov,
    # ale aj ten istý celkový drift: súčet sa premiešaním nemení, takže trh končí na tej
    # istej cene ako zdroj. Stratégia s dlhým biasom tak nie je trestaná.
    vynos = np.log(close[1:] / close[:-1])

    n = len(vynos)
    rng = np.random.default_rng(seed)
    zaciatky = np.arange(0, n, block)
    poradie = rng.permutation(len(zaciatky))
    index = np.concatenate([np.arange(z, min(z + block, n)) for z in zaciatky[poradie]])

    novy_close = np.empty(len(close))
    novy_close[0] = float(close[0])
    novy_close[1:] = float(close[0]) * np.exp(np.cumsum(vynos[index]))
    # Bar 0 si necháva svoj tvar, ostatné idú s výnosom, ku ktorému patrili (index+1).
    novy_tvar = np.vstack([tvar[:1], tvar[index + 1]])
    novy_objem = np.concatenate([objem[:1], objem[index + 1]])

    out = pd.DataFrame({
        "date": df["date"].to_numpy(),          # časová os ostáva pôvodná
        "open": novy_close * novy_tvar[:, 0],
        "high": novy_close * novy_tvar[:, 1],
        "low": novy_close * novy_tvar[:, 2],
        "close": novy_close,
        "volume": novy_objem,
    })
    # Premiešanie môže tvar baru posunúť tak, že high nie je najvyššie — bar, ktorý
    # nespĺňa low <= open,close <= high, by rozbil každý fill model.
    out["high"] = out[["open", "high", "low", "close"]].max(axis=1)
    out["low"] = out[["open", "high", "low", "close"]].min(axis=1)
    return out


def _source_frame(pair: str, timerange: str):
    """1m sviečky zdrojového trhu orezané na okno receptu."""
    import pandas as pd

    from .webapp.chart import pair_file

    path = pair_file(pair, "1m")
    if not path.exists():
        raise FileNotFoundError(f"chýbajú 1m sviečky pre {pair} ({path})")
    df = pd.read_feather(path)
    if timerange:
        a, b = timerange.split("-")
        od = pd.Timestamp(datetime.strptime(a, "%Y%m%d").replace(tzinfo=timezone.utc))
        do = pd.Timestamp(datetime.strptime(b, "%Y%m%d").replace(tzinfo=timezone.utc))
        df = df[(df["date"] >= od) & (df["date"] < do)]
    return df.reset_index(drop=True)


def build(key: str, *, symbol: str = "", source_pair: str = "BTC/USDT:USDT",
          timerange: str = "20211001-20260904", like: str = "btcusdt_binance",
          block: int = DEFAULT_BLOCK, seed: int = DEFAULT_SEED, force: bool = False,
          registry: Path | None = None) -> Recipe:
    """Vygeneruje syntetický trh a zapíše recept. Existujúci prepíše len s `force`.

    Prepísanie nie je nevinné: skoršie behy na tomto trhu prestanú byť porovnateľné
    s novými, hoci sa pár volá rovnako. Preto to chce výslovný súhlas.
    """
    from . import engines

    stare = recipes(registry)
    if key in stare and not force:
        raise ValueError(
            f"trh {key!r} už existuje (seed {stare[key].seed}, {stare[key].created[:10]}). "
            f"Pregenerovanie znamená, že skoršie behy na ňom už nie sú porovnateľné — "
            f"ak to naozaj chceš, pridaj --force.")

    df = _source_frame(source_pair, timerange)
    novy = shuffle_bars(df, block=block, seed=seed)

    recept = Recipe(key=key, symbol=symbol or f"{key.upper()}/USDT:USDT",
                    source_pair=source_pair, timerange=timerange, block=block, seed=seed,
                    created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    note=f"premiešané 1m bary {source_pair} po blokoch {block}")
    # Recept musí byť v registri skôr, než sa hľadá cesta k dátam: inštrument vzniká
    # z registra.
    _write_recipe(recept, like, registry)
    INSTRUMENTS.update(synthetic_specs(registry))

    inst = INSTRUMENTS[key]
    path = engines.one_minute_file(inst)
    path.parent.mkdir(parents=True, exist_ok=True)
    novy.to_feather(path)

    recept = Recipe(**{**recept.to_dict(), "sha256": _sha256(path)})
    _write_recipe(recept, like, registry)
    return recept


def verify(key: str, registry: Path | None = None) -> tuple[bool, str]:
    """Sedia dáta s receptom? `(True, správa)` keď áno.

    Bez tohto by sa nedalo rozlíšiť „ten istý trh ako minule“ od „niekto ho medzitým
    pregeneroval“ — a to je celý zmysel pevného trhu.
    """
    recept = recipes(registry).get(key)
    if recept is None:
        return False, f"trh {key!r} v registri nie je"
    try:
        path = data_file(key)
    except KeyError as exc:
        return False, str(exc)
    if not path.exists():
        return False, (f"recept je, ale sviečky nie — vygeneruj ich: "
                       f"python -m tester.synthetic build {key}")
    if not recept.sha256:
        return True, "recept nemá kontrolný súčet, takže sa dá overiť len jeho existencia"
    teraz = _sha256(path)
    if teraz != recept.sha256:
        return False, (f"sviečky nesedia s receptom (sha256 {teraz[:12]}… "
                       f"vs {recept.sha256[:12]}…) — niekto ich pregeneroval alebo prepísal, "
                       f"takže staršie behy na tomto trhu s novými porovnateľné nie sú")
    return True, f"sviečky sedia s receptom (sha256 {teraz[:12]}…)"


def main(argv: list[str] | None = None) -> int:
    """`python -m tester.synthetic build|list|verify`."""
    import argparse

    ap = argparse.ArgumentParser(prog="python -m tester.synthetic",
                                 description=__doc__.split("###")[0].strip())
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="vygeneruje syntetický trh (existujúci len s --force)")
    p.add_argument("key", nargs="?", default="synth", help="kľúč trhu (default synth)")
    p.add_argument("--symbol", default="", help="ako sa pár volá (default <KEY>/USDT:USDT)")
    p.add_argument("--source", default="BTC/USDT:USDT", help="z ktorého trhu sa berú bary")
    p.add_argument("--like", default="btcusdt_binance",
                   help="inštrument, od ktorého sa preberú vlastnosti trhu")
    p.add_argument("--timerange", default="20211001-20260904")
    p.add_argument("--block", type=int, default=DEFAULT_BLOCK)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--force", action="store_true",
                   help="prepísať existujúci trh (skoršie behy prestanú byť porovnateľné)")

    sub.add_parser("list", help="recepty v registri a či dáta sedia")
    p = sub.add_parser("verify", help="sedia sviečky s receptom?")
    p.add_argument("key", nargs="?", default="synth")

    args = ap.parse_args(argv)
    if args.cmd == "list":
        vsetky = recipes()
        if not vsetky:
            print("register je prazdny: python -m tester.synthetic build synth")
            return 1
        for k, r in vsetky.items():
            ok, sprava = verify(k)
            print(f"{k:<12}{r.symbol:<22}{r.source_pair:<16}{r.timerange:<20}"
                  f"blok {r.block:<4}seed {r.seed}")
            print(f"{'':<12}{'OK' if ok else 'CHYBA'}: {sprava}")
        return 0

    if args.cmd == "verify":
        ok, sprava = verify(args.key)
        print(("OK: " if ok else "CHYBA: ") + sprava)
        return 0 if ok else 1

    try:
        r = build(args.key, symbol=args.symbol, source_pair=args.source,
                  timerange=args.timerange, like=args.like, block=args.block,
                  seed=args.seed, force=args.force)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        raise SystemExit(str(exc))
    print(f"hotovo: {r.symbol} ({r.key})")
    print(f"  zdroj {r.source_pair}, okno {r.timerange}, blok {r.block}, seed {r.seed}")
    print(f"  sviecky: {data_file(r.key)}")
    print(f"  sha256:  {r.sha256}")
    print("\nTrh je pevny - pregeneruje sa len s --force. V ponuke parov sa objavi po "
          "restarte webapp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------- #
# vyhodnotenie: to isté zadanie na skutočnom a na premiešanom trhu
# --------------------------------------------------------------------------- #

#: Menej než toľko okien so syntetickým behom a porovnanie nič nehovorí.
MIN_WINDOWS = 3


def synthetic_symbols() -> set[str]:
    """Symboly syntetických trhov — tie, ktorých sviečky vyrobil tento modul."""
    return {i.symbol for i in INSTRUMENTS.values() if i.data_source == "synthetic"}


def twin_for(pair: str, registry: Path | None = None) -> tuple[str, InstrumentSpec] | None:
    """Syntetické dvojča páru: trh premiešaný z jeho barov (recept so `source_pair`).
    Pri viacerých ten s najširším oknom. `None` = ešte nevyrobené."""
    kandidati = [(k, r) for k, r in recipes(registry).items() if r.source_pair == pair and k in INSTRUMENTS]
    if not kandidati:
        return None
    kandidati.sort(key=lambda kr: (kr[1].timerange.split("-")[0], kr[1].timerange.split("-")[-1]))
    key = kandidati[0][0]
    return key, INSTRUMENTS[key]


def twin_key(pair: str) -> str:
    """`NAS100/USD` → `synth_nas100_usd`; BTC má z histórie kľúč `synth`."""
    return "synth_" + pair.replace("/", "_").replace(":", "_").lower()


def ensure_twin(pair: str, *, registry: Path | None = None) -> tuple[str, InstrumentSpec]:
    """Dvojča páru; keď nie je, vyrobí ho z celého rozsahu dát páru (recept + 1m sviečky).

    Analytika ho potrebuje pri každom páre - tester nemá vedieť, že má najprv niečo
    „vybuildovať". Trh je potom pevný ako každý iný recept.
    """
    import pandas as pd

    from .webapp.runner import instrument_for_pair

    hotove = twin_for(pair, registry)
    if hotove is not None:
        return hotove
    like = instrument_for_pair(pair)
    df = _source_frame(pair, "")
    if df.empty:
        raise FileNotFoundError(f"pár {pair} nemá 1m sviečky, z ktorých by sa dal premiešať")
    a = df["date"].iloc[0].strftime("%Y%m%d")
    b = (df["date"].iloc[-1] + pd.Timedelta(days=1)).strftime("%Y%m%d")
    base, _, quote = pair.partition("/")
    symbol = f"SYNTH-{base}/{quote}" if quote else f"SYNTH-{base}/USD"
    key = twin_key(pair)
    build(key, symbol=symbol, source_pair=pair, timerange=f"{a}-{b}", like=like, registry=registry)
    return key, INSTRUMENTS[key]


def _row(rec: dict[str, Any], store) -> dict[str, Any]:
    from .webapp.runner import entry_signals

    v = rec.get("result") or {}
    try:
        signaly = entry_signals((store.log(rec["id"]) or "").splitlines())
    except Exception:                                   # noqa: BLE001 - log je nepovinný
        signaly = None
    obchodov = v.get("trades") or 0
    return {"run_id": rec["id"], "trades": obchodov, "break_even_pct": v.get("break_even_pct"),
            "signals": signaly,
            "fill_pct": round(100 * obchodov / signaly, 1) if signaly else None}


def _best(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Z viacerých behov jedného okna ten s najviac obchodmi — nie ich zmes."""
    return max(records, key=lambda r: (r.get("result") or {}).get("trades") or 0)


def assess(records: Sequence[dict[str, Any]], store, *, strategy: str = "ibs") -> dict[str, Any]:
    """Porovná vybrané behy s behmi tej istej konfigurácie na syntetickom trhu.

    Nič nespúšťa — hľadá v histórii. Keď syntetické behy nie sú, povie to aj s príkazom,
    ktorým vzniknú; vymýšľať si čísla by bolo horšie než priznať, že chýbajú.
    """
    import statistics

    from .webapp.store import strategy_of

    skutocne = [r for r in records if r.get("status") == "done"
                and ((r.get("result") or {}).get("trades") or 0) > 0]
    if not skutocne:
        return {"severity": "chyba dat", "rows": [], "verdict": "žiadne dobehnuté behy"}

    from .analytics import normalized_params

    prve = skutocne[0].get("settings") or {}
    profil = prve.get("profile") or ""
    par, tf = prve.get("pair") or "", prve.get("timeframe") or ""
    okna = {(r.get("settings") or {}).get("timerange") for r in skutocne}
    okna.discard(None)
    # Dvojča páru (premiešané z jeho barov); keď ho pár nemá, hocijaký syntetický trh.
    dvojca = twin_for(par)
    symboly = {dvojca[1].symbol} if dvojca else synthetic_symbols()
    prikaz = (f"python -m tester.webapp.cli run --profile {profil or '<profil>'} "
              f"--pair {sorted(symboly)[0] if symboly else 'SYNTH/USDT:USDT'} "
              f"--timerange <okno> --note \"synteticky trh\"")

    out: dict[str, Any] = {"profile": profil, "rows": [], "missing": [],
                           "pairs": sorted(symboly), "command": prikaz}
    if not symboly:
        out["severity"] = "chyba dat"
        out["verdict"] = ("syntetický trh ešte nie je vyrobený — vznikne pri Spočítať "
                          "na karte Analytika (alebo `python -m tester.synthetic build`)")
        return out

    # Porovnáva sa len to, čo sa porovnať dá: tie isté parametre (doplnené Pine
    # defaultmi - nie meno profilu, to sa dá prepísať), ten istý TF a to isté okno.
    norm = normalized_params(skutocne[0])
    synt: dict[str, list[dict[str, Any]]] = {}
    for rec in store.all():
        nast = rec.get("settings") or {}
        if (rec.get("status") == "done" and nast.get("pair") in symboly
                and strategy_of(rec) == strategy and (nast.get("timeframe") or tf) == tf
                and normalized_params(rec) == norm):
            synt.setdefault(nast.get("timerange") or "", []).append(rec)

    for okno in sorted(okna):
        realny = _row(_best([r for r in skutocne
                             if (r.get("settings") or {}).get("timerange") == okno]), store)
        if okno not in synt:
            out["missing"].append(okno)
            out["rows"].append({"timerange": okno, "real": realny, "synth": None})
            continue
        out["rows"].append({"timerange": okno, "real": realny,
                            "synth": _row(_best(synt[okno]), store)})

    dvojice = [r for r in out["rows"] if r["synth"]]
    hotove = [r for r in dvojice if r["synth"]["break_even_pct"] is not None]
    out["windows"] = len(hotove)
    if len(hotove) < MIN_WINDOWS:
        out["severity"] = "chyba dat"
        out["verdict"] = (
            f"na porovnanie treba aspoň {MIN_WINDOWS} okná so behom na syntetickom trhu, "
            f"sú {len(hotove)}. Dobehni ich: {prikaz}")
        return out

    real_be = [r["real"]["break_even_pct"] for r in hotove
               if r["real"]["break_even_pct"] is not None]
    synt_be = [r["synth"]["break_even_pct"] for r in hotove]
    out["real_median"] = round(statistics.median(real_be), 4) if real_be else None
    out["synth_median"] = round(statistics.median(synt_be), 4)
    out["real_positive"] = sum(1 for x in real_be if x > 0)
    out["synth_positive"] = sum(1 for x in synt_be if x > 0)
    fill = lambda kluc: [r[kluc]["fill_pct"] for r in hotove if r[kluc]["fill_pct"] is not None]
    out["real_fill"] = round(statistics.median(fill("real")), 1) if fill("real") else None
    out["synth_fill"] = round(statistics.median(fill("synth")), 1) if fill("synth") else None
    out["severity"], out["verdict"] = _verdict(out)
    return out


def _verdict(out: dict[str, Any]) -> tuple[str, str]:
    """Čo z porovnania plynie. Kladné číslo na premiešanom trhu je nález o **nás**."""
    n = out["windows"]
    kladnych = out["synth_positive"]
    synt, realny = out["synth_median"], out.get("real_median")
    fill_r, fill_s = out.get("real_fill"), out.get("synth_fill")

    # Vyplnenie signálov je vedľajšia informácia, ale často zaujímavejšia než hlavná:
    # keď sa na premiešanom trhu vyplní podstatne menej vstupov, stratégia sa spolieha
    # na to, že sa cena k nejakej úrovni vráti — a to je skutočná štruktúra trhu.
    doplnok = ""
    if fill_r is not None and fill_s is not None and fill_r - fill_s >= 15:
        doplnok = (f" Vedľajšia vec, ktorá stojí za pozretie: na skutočnom trhu sa vyplní "
                   f"{fill_r:g} % signálov, na premiešanom {fill_s:g} %. Vstup teda čaká na "
                   f"návrat ceny k úrovni — a to premiešaním zmizne.")

    if kladnych >= n - 1 and synt > 0:
        return "chyba", (
            f"POZOR NA ENGINE: aj na trhu bez akejkoľvek štruktúry vyšiel break-even kladný "
            f"v {kladnych} z {n} okien (medián {synt:+.4f} %). Takú výhodu trh nemá z čoho "
            f"dať — hľadaj ju v backteste: pohľad dopredu, fill model, sizing." + doplnok)

    if realny is not None and realny > 0 and synt < realny / 2 and kladnych <= n / 2 + 0.5:
        return "ok", (
            f"ENGINE OK: na premiešanom trhu edge nie je — kladný v {kladnych} z {n} okien, "
            f"medián {synt:+.4f} % oproti {realny:+.4f} % na skutočnom trhu. To, čo stratégia "
            f"nameria, teda nevyrába backtest sám od seba." + doplnok)

    return "pozor", (
        f"NEJASNE: na premiešanom trhu je break-even kladný v {kladnych} z {n} okien "
        f"(medián {synt:+.4f} %"
        + (f" oproti {realny:+.4f} % na skutočnom" if realny is not None else "") + "). "
        f"Nie je to dosť na obvinenie enginu ani na jeho očistenie — dobehni viac okien "
        f"alebo viac obchodov." + doplnok)
