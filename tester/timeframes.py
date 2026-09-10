"""Timeframy, ktoré má mať Tester na disku — a ich odvodenie z 1m sviečok.

    python -m tester.timeframes             # doplní, čo chýba
    python -m tester.timeframes --status    # čo je na disku a čo by pribudlo
    python -m tester.timeframes --force     # prepíše aj to, čo existuje

### Načo to je
Freqtrade si vyšší TF z 1m **nedopočíta**: keď preň nemá súbor na disku, backtest skončí
na „No history … found". Burza pritom niektoré timeframy nedáva vôbec (2m, 4m) a
Dukascopy export nedáva žiadny okrem 1m. Zoznam v `timeframes.json` preto hovorí, čo má
byť k dispozícii, a tento modul to z 1m poskladá.

Skladá sa tým istým pravidlom, aké používa graf webapp, offline simulátor aj emulátor
MultiCharts (`tradebot.core.candles.resample_ohlcv`) — keby sa pravidlo rozišlo,
porovnanie výsledkov medzi platformami by prestalo niečo znamenať.

### Čo sa neprepisuje a necommituje
Oficiálne stiahnuté TF z burzy (3m, 5m, 15m…) ostanú tak, ako prišli — nikdy sa
neprepisujú. Vyrobené súbory sa zapíšu do `data/tester/.derived.json` a
`data_archive split` ich preskočí — v gite majú byť len dáta z burzy a z exportov,
nie to, čo sa kedykoľvek dopočíta z 1m.

### Zastaraný odvodený súbor
Doplniť len to, čo **chýba**, nestačí: keď sa 1m zdroj prerobí (`tester.synthetic build
--force`, nový `dukas_import`, `data_archive merge` s novšími dátami), už odvodené vyššie
TF ostanú na disku staré a nič si toho nevšimne. Backtest potom beží na 5m sérii, ktorá
nemá nič spoločné s 1m detailom, ktorým sa plnia ordre — a výsledok vyzerá úplne normálne.
Presne to sa stalo synthetickému trhu 2026-09-10 (3m a 5m odvodené o tri minúty skôr, než
sa 1m pregeneroval) a chytilo sa to až na obchodoch so stratou 40× väčšou, než bol plán.

Preto sa odvodený súbor prerobí aj vtedy, keď je **starší než jeho 1m zdroj**. Platí to
len pre súbory, ktoré sú v `.derived.json`, teda pre tie, ktoré sme vyrobili sami:
stiahnutý timeframe v tom zozname nie je a prepísať sa preto nemôže.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.core.candles import timeframe_minutes as minutes
from tradebot.core.derived import MANIFEST, derived, forget, remember
from tradebot.core.paths import TESTER_DATA

__all__ = ["CONFIG", "SOURCE_TF", "wanted", "minutes", "sources", "targets",
           "missing", "ensure", "derived", "forget", "remember", "main"]

#: Konfigurácia — jediné miesto, kde sa zoznam timeframov mení.
CONFIG = Path(__file__).with_name("timeframes.json")

#: Z čoho sa skladá. Nikdy sa neodvodzuje, vždy je to stiahnuté alebo importované.
SOURCE_TF = "1m"

#: Keď config chýba alebo je pokazený (klon bez neho, preklep v JSON).
FALLBACK: tuple[str, ...] = ("2m", "3m", "4m", "5m", "15m", "30m", "1h", "4h", "1d", "1w")

#: Zoznam vyrobených súborov, aby ich `data_archive split` nepridal do gitu. Vedie ho
#: jadro (`tradebot.core.derived`), lebo doň píše aj Freqtrade adaptér, keď si timeframe
#: dopočíta počas behu.

def wanted(config: Path | None = None) -> tuple[str, ...]:
    """Timeframy zo `timeframes.json`, bez zdrojového 1m."""
    path = Path(config or CONFIG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tfs = [str(tf) for tf in data["derive"]]
    except (OSError, ValueError, KeyError, TypeError):
        tfs = list(FALLBACK)
    return tuple(tf for tf in tfs if tf != SOURCE_TF)


def sources(root: Path | None = None) -> list[Path]:
    """Všetky 1m súbory v sklade sviečok — z každého sa dá odvodiť zvyšok.

    Vyberá sa podľa mena, nie podľa adresára: `-1h-funding_rate.feather` a `-1h-mark.feather`
    sú tiež vo `futures/`, ale sviečky to nie sú a skladať sa z nich nedá.
    """
    base = Path(root or TESTER_DATA)
    if not base.exists():
        return []
    found = list(base.rglob(f"*-{SOURCE_TF}.feather")) + list(base.rglob(f"*-{SOURCE_TF}-futures.feather"))
    return sorted(found)


def _target(src: Path, timeframe: str) -> Path:
    """`BTC_USDT_USDT-1m-futures.feather` + `4h` → `BTC_USDT_USDT-4h-futures.feather`."""
    name = src.name[: -len(".feather")]
    suffix = "-futures" if name.endswith("-futures") else ""
    stem = name[: -len(f"-{SOURCE_TF}{suffix}")]
    return src.parent / f"{stem}-{timeframe}{suffix}.feather"


def targets(root: Path | None = None, config: Path | None = None) -> dict[Path, list[Path]]:
    """1m súbor → súbory, ktoré z neho podľa configu majú vzniknúť."""
    return {src: [_target(src, tf) for tf in wanted(config)] for src in sources(root)}


def missing(root: Path | None = None, config: Path | None = None) -> list[Path]:
    """Ktoré z nich na disku ešte nie sú."""
    return [out for outs in targets(root, config).values() for out in outs if not out.exists()]


def _zastarany(out: Path, src: Path, nase: set[str]) -> bool:
    """Je `out` náš odvodený súbor, ktorý je starší než jeho 1m zdroj?

    Bez tejto otázky by sa prerobený 1m zdroj do vyšších TF nikdy nepremietol a beh by
    ticho miešal dve rôzne série — viď hlavičku modulu.
    """
    if str(out) not in nase:
        return False
    try:
        return out.stat().st_mtime < src.stat().st_mtime
    except OSError:  # pragma: no cover - súbor zmizol medzi dvoma volaniami
        return False


def ensure(root: Path | None = None, config: Path | None = None, force: bool = False,
           verbose: bool = True, manifest: Path | None = None) -> list[Path]:
    """Doplní chýbajúce timeframy z 1m. Vráti, čo vzniklo."""
    import pandas as pd  # noqa: F401  (drží sa lenivo, aby import modulu nebol drahý)

    from tradebot.core.candles import resample_ohlcv

    base = Path(root or TESTER_DATA)
    manifest_path = Path(manifest) if manifest else (base / MANIFEST.name)
    # Len to, čo sme sami vyrobili, sa smie prepísať — stiahnutý TF z burzy tu nie je.
    nase = {str(p) for p in derived(manifest_path)}
    made: list[Path] = []
    for src, outs in targets(base, config).items():
        todo = [(out, tf) for out, tf in zip(outs, wanted(config))
                if force or not out.exists() or _zastarany(out, src, nase)]
        if not todo:
            continue
        df = pd.read_feather(src)
        for out, tf in todo:
            part = resample_ohlcv(df, minutes(tf))
            part.to_feather(out)
            made.append(out)
            if verbose:
                print(f"  {out.relative_to(base).as_posix()}  {len(part):>8} barov  "
                      f"{out.stat().st_size / 1e6:.1f} MB")
    if made:
        remember(made, manifest_path)
    return made


def status(root: Path | None = None, config: Path | None = None) -> int:
    base = Path(root or TESTER_DATA)
    tfs = wanted(config)
    print(f"config: {CONFIG}")
    print(f"  odvodzuje sa z {SOURCE_TF}: {', '.join(tfs)}\n")
    src_list = sources(base)
    if not src_list:
        print(f"ziadne {SOURCE_TF} sviecky v {base} - najprv `python -m tester.data_archive merge`")
        return 0
    made = set(derived(base / MANIFEST.name))
    for src in src_list:
        print(f"{src.relative_to(base).as_posix()}")
        for tf in tfs:
            out = _target(src, tf)
            if not out.exists():
                stav = "CHYBA"
            elif out in made:
                stav = "odvodene"
            else:
                stav = "z burzy"
            print(f"  {tf:>4}  {stav}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m tester.timeframes",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--status", action="store_true", help="len vypíš, čo je a čo chýba")
    ap.add_argument("--force", action="store_true", help="prepíš aj existujúce odvodené súbory")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.status:
        return status()

    made = ensure(force=args.force, verbose=not args.quiet)
    if not args.quiet:
        print(f"hotovo: {len(made)} suborov" if made else "vsetky timeframy uz na disku su")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
