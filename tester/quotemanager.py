"""Sviečky pre QuoteManager (MultiCharts) — ASCII CSV zo skladu sviečok.

    python -m tester.quotemanager                 # čo treba a ešte nie je
    python -m tester.quotemanager --all           # aj krypto, nielen Dukascopy symboly
    python -m tester.quotemanager --symbol NAS100 --force
    python -m tester.quotemanager --status

### Načo to je
MultiCharts si sviečky nesťahuje — nakŕmi sa cez QuoteManager z ASCII súboru. Doteraz taký
súbor vznikal len pri importe surového Dukascopy exportu (`tester.dukas_import`), takže
pre pár, ktorý cez ten import neprešiel (krypto z burzy), sa nedal vyrobiť vôbec.

Teraz sa robí z **toho istého skladu 1m sviečok**, aký číta Freqtrade aj emulátor
(`data/tester/<zdroj>/<trh>/…`, zložený z `data_archive/`). Vďaka tomu je v QuoteManageri
presne to, na čom bežali backtesty — nie druhá kópia z inej cesty.

### Formát
`Date,Time,Open,High,Low,Close,Volume`, čas **zatvorenia** baru (MultiCharts konvencia:
+1 minúta oproti času otvorenia, ktorý je v sklade) a objem ako celé číslo.

Objem: QuoteManager berie len celé čísla, Dukascopy CFD majú loty s desatinami, preto sa
zapisuje `round(vol × --volume-scale)` (predvolene 100). Pri krypte je objem skutočný,
takže škálovanie len posúva rád — na `useVolumeFilter` to nemá vplyv, na jeho prahy áno.

### Čo NEvzniká
Nič sa nedopočítava: QuoteManager dostane 1m a vyššie TF si MultiCharts skladá sám.
Výstup je odvodený, gitignorovaný a kedykoľvek sa dá vyrobiť znova.
"""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

from tradebot.core.env import getenv
from tradebot.core.paths import QUOTEMANAGER_DATA
from tradebot.core.types import INSTRUMENTS, InstrumentSpec

from . import engines

__all__ = ["HEADER", "MINUTE", "num", "format_row", "csv_path", "write_csv",
           "scope", "targets", "missing", "export", "ensure", "main"]

#: Hlavička, akú čaká ASCII import v QuoteManageri.
HEADER = "Date,Time,Open,High,Low,Close,Volume"

MINUTE = timedelta(minutes=1)

#: Predvolený formát dátumu (ISO) a násobok objemu — rovnaké ako v `dukas_import`.
DATE_FORMAT = "%Y-%m-%d"
VOLUME_SCALE = 100.0

#: Ktoré symboly exportovať bez ďalších prepínačov. `multicharts` = len tie, ktoré v
#: MultiCharts naozaj bežia (Dukascopy CFD); `all` aj krypto; `off` nič.
SCOPES = ("multicharts", "all", "off")


def num(x: float) -> str:
    """Číslo bez exponentu a bez zbytočných núl: 24271.599 -> '24271.599', 0.0 -> '0'."""
    return f"{x:.12g}"


def format_row(t, o: float, h: float, l: float, c: float, volume: int,  # noqa: E741
               date_format: str = DATE_FORMAT) -> str:
    """Jeden riadok ASCII súboru. `t` je čas baru **tak, ako má byť v súbore**."""
    return (f"{t.strftime(date_format)},{t.strftime('%H:%M:%S')},"
            f"{num(o)},{num(h)},{num(l)},{num(c)},{volume}")


def csv_path(inst: InstrumentSpec) -> Path:
    """`data/quotemanager/<zdroj>/<PÁR>-1m.csv` — vedľa ostatných exportov toho zdroja."""
    return QUOTEMANAGER_DATA / inst.data_source / f"{inst.data_stem}-1m.csv"


def write_csv(df, dst: Path, *, stamp: str = "close", date_format: str = DATE_FORMAT,
              volume_scale: float = VOLUME_SCALE) -> int:
    """1m sviečky (`date`, o/h/l/c/v) → ASCII súbor pre QuoteManager. Vráti počet riadkov."""
    if stamp not in ("close", "open"):
        raise ValueError(f"stamp musí byť 'close' alebo 'open', nie {stamp!r}")
    shift = MINUTE if stamp == "close" else timedelta(0)
    dst.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(dst, "w", encoding="utf-8", newline="\n") as out:
        out.write(HEADER + "\n")
        for r in df.itertuples(index=False):
            out.write(format_row(
                r.date.to_pydatetime() + shift,
                float(r.open), float(r.high), float(r.low), float(r.close),
                int(round(float(r.volume) * volume_scale)), date_format,
            ) + "\n")
            rows += 1
    return rows


def targets(want: str = "multicharts") -> dict[str, InstrumentSpec]:
    """Inštrumenty, pre ktoré má export zmysel — a sú pre ne 1m sviečky."""
    if want not in SCOPES:
        raise ValueError(f"neznamy rozsah {want!r}; znamy: {', '.join(SCOPES)}")
    if want == "off":
        return {}
    out = {}
    for key, inst in INSTRUMENTS.items():
        if want == "multicharts" and inst.venue != "multicharts":
            continue
        if engines.one_minute_file(inst).exists():
            out[key] = inst
    return out


def scope() -> str:
    """Rozsah z `TRADEBOT_QUOTEMANAGER` (`multicharts` | `all` | `off`)."""
    want = (getenv("QUOTEMANAGER", "multicharts") or "multicharts").strip().lower()
    return want if want in SCOPES else "multicharts"


def missing(want: str = "multicharts") -> list[Path]:
    return [csv_path(inst) for inst in targets(want).values() if not csv_path(inst).exists()]


def export(inst: InstrumentSpec, *, dst: Path | None = None, force: bool = False,
           verbose: bool = True, **kw) -> Path | None:
    """Vyrobí ASCII súbor pre jeden inštrument zo skladu 1m sviečok."""
    import pandas as pd

    src = engines.one_minute_file(inst)
    out = Path(dst) if dst else csv_path(inst)
    if not src.exists():
        if verbose:
            print(f"  {inst.symbol}: chybaju 1m sviecky ({src.name}) - preskakujem")
        return None
    if out.exists() and not force:
        return None
    rows = write_csv(pd.read_feather(src), out, **kw)
    if verbose:
        # `--out` môže ukazovať kamkoľvek, preto relatívne len keď to dáva zmysel
        try:
            label = out.relative_to(QUOTEMANAGER_DATA).as_posix()
        except ValueError:
            label = str(out)
        print(f"  {label}  {rows:>8} barov  {out.stat().st_size / 1e6:.1f} MB")
    return out


def ensure(want: str | None = None, *, force: bool = False, verbose: bool = True,
           **kw) -> list[Path]:
    """Doplní chýbajúce ASCII súbory. Rozsah z `TRADEBOT_QUOTEMANAGER`, inak Dukascopy."""
    made = []
    for inst in targets(want or scope()).values():
        out = export(inst, force=force, verbose=verbose, **kw)
        if out is not None:
            made.append(out)
    return made


def status(want: str = "all") -> int:
    print(f"export pre QuoteManager: {QUOTEMANAGER_DATA}")
    found = targets(want)
    if not found:
        print("  ziadne 1m sviecky - najprv `python -m tester.data_archive merge`")
        return 0
    for key, inst in found.items():
        out = csv_path(inst)
        stav = f"{out.stat().st_size / 1e6:.1f} MB" if out.exists() else "CHYBA"
        print(f"  {inst.symbol:<16} {inst.venue:<12} {out.name:<28} {stav}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m tester.quotemanager",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--symbol", help="len tento symbol (NAS100, BTC/USDT:USDT, kľúč inštrumentu)")
    ap.add_argument("--all", action="store_true", help="aj krypto, nielen Dukascopy symboly")
    ap.add_argument("--status", action="store_true", help="čo je vyrobené a čo chýba")
    ap.add_argument("--force", action="store_true", help="prepíš aj existujúce súbory")
    ap.add_argument("--out", type=Path, help="výstupný súbor (len s --symbol)")
    ap.add_argument("--stamp", choices=("close", "open"), default="close",
                    help="čas baru: close = +1 min (konvencia MultiCharts), open = ako v sklade")
    ap.add_argument("--date-format", default=DATE_FORMAT, help="strftime formát dátumu")
    ap.add_argument("--volume-scale", type=float, default=VOLUME_SCALE,
                    help="objem = round(vol × N); QuoteManager chce celé číslo")
    args = ap.parse_args(argv)

    if args.status:
        return status()

    opts = {"stamp": args.stamp, "date_format": args.date_format,
            "volume_scale": args.volume_scale}
    if args.symbol:
        want = args.symbol.strip().lower()
        found = [inst for key, inst in INSTRUMENTS.items()
                 if want in (key.lower(), inst.symbol.lower(), inst.data_stem.lower(),
                             inst.symbol.partition("/")[0].lower())]
        if not found:
            print(f"symbol {args.symbol!r} nepoznam; zoznam da `--status`")
            return 1
        made = [p for p in (export(found[0], dst=args.out, force=args.force, **opts),) if p]
    else:
        made = ensure("all" if args.all else None, force=args.force, **opts)

    print(f"hotovo: {len(made)} suborov" if made else "vsetko uz vyrobene je")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
