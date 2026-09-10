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
from typing import Any

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
