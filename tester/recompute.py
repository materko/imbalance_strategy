"""Prepočet peňazí uložených behov — súhrn z `trades.json` a hodnoty bodu inštrumentu.

    python -m tester.recompute                  # len výpis: čo by sa zmenilo (dry-run)
    python -m tester.recompute --pair MNQ/USD   # len behy na jednom páre
    python -m tester.recompute --write          # naozaj prepíše run.json a trades.json
    python -m tester.webapp.cli recompute …     # to isté cez CLI

### Načo to je
Do opravy A1 (audit 2026-09-17) sa na trhoch s hodnotou bodu ≠ 1 (MNQ 2, zlato 100,
ropa 1000, forex 100 000…) peniaze rozchádzali:

* **emulátor MultiCharts** mal zisk obchodu správne, ale objem v súhrne bez hodnoty bodu
  → `break_even_pct` a `volume_abs` ×hodnota bodu (GBPJPY hlásil 336,9 %);
* **Freqtrade** hodnotu bodu nepoznal vôbec (CFD bežali ako spot) → zisk, poplatky
  a drawdown ÷hodnota bodu. Kusy v `amount` pritom boli kusy enginu, takže peniaze sa
  dajú z cien dopočítať. Shorty, ktoré spot zahodil, sa však doplniť nedajú — taký beh
  treba **zopakovať**, prepočet ho len označí.

Prepočet ide cez jedinú definíciu peňazí (`tradebot.core.money`), tú istú, ktorou počíta
nový beh, takže prepočítaný starý beh a nový beh sa nerozídu. Chýbajúca `point_value`
v zázname obchodu nie je 1, doplní sa z inštrumentu páru behu; neznámy pár sa preskočí.

`recompute_run()` je čistá funkcia nad záznamom a obchodmi — dá sa zavolať aj z iného
nástroja nad históriou (napr. pri upratovaní behov) bez tohto CLI.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from tradebot.core.money import point_value_for_pair, row_money, row_point_value, summary_money

__all__ = ["Recomputed", "recompute_run", "scan", "main", "SUMMARY_KEYS"]

#: Kľúče súhrnu, ktoré sú čisto z peňazí obchodov a prepočet ich smie prepísať.
SUMMARY_KEYS = ("wins", "losses", "draws", "winrate", "pnl_abs", "pnl_pct", "profit_factor",
                "max_drawdown_abs", "max_drawdown_pct", "final_balance", "gross_abs",
                "volume_abs", "break_even_pct", "exits", "streaks")

#: Kľúče, ktoré sa ukazujú ako príklad pred/po.
SHOWN = ("break_even_pct", "pnl_abs", "max_drawdown_abs", "max_drawdown_pct", "volume_abs")

#: Rozdiel pod týmto prahom je zaokrúhlenie (Freqtrade počíta poplatky presnejšie), nie zmena.
_TOL_ABS = 0.011


@dataclass
class Recomputed:
    """Výsledok prepočtu jedného behu."""

    run_id: str
    pair: str
    engine: str
    point_value: float | None
    #: `kľúč -> (pred, po)` pre súhrn, len skutočné zmeny
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    #: koľko obchodov dostalo iný `profit_abs` (alebo doplnenú `point_value`)
    trades_changed: int = 0
    summary: dict[str, Any] | None = None
    trades: list[dict[str, Any]] | None = None
    series_equity: list[list[Any]] | None = None
    #: prečo sa beh nedá opraviť celý (napr. Freqtrade spot zahodil shorty)
    warning: str = ""
    skipped: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.changes or self.trades_changed)


def _engine(record: dict[str, Any]) -> str:
    nast = record.get("settings") or {}
    eng = nast.get("engine") or (record.get("result") or {}).get("engine") or "freqtrade"
    return "multicharts" if str(eng).startswith("multicharts") else str(eng)


def _differs(a: Any, b: Any, tol: float = _TOL_ABS) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) > max(tol, 1e-6 * abs(float(b)))
    if isinstance(a, dict) and isinstance(b, dict):
        # `exits`: emulátor zaokrúhľoval súčet po každom obchode, takže PnL skupiny smie
        # ujsť o pol centa na obchod
        n = a.get("n") if isinstance(a.get("n"), int) else 0
        return set(a) != set(b) or any(_differs(a[k], b[k], tol + 0.006 * n) for k in a)
    return a != b


def recompute_run(record: dict[str, Any], trades: list[dict[str, Any]]) -> Recomputed:
    """Prepočíta peniaze jedného behu. Vstupy nemení — vráti nové kópie."""
    nast = record.get("settings") or {}
    pair = str(nast.get("pair") or "")
    out = Recomputed(run_id=str(record.get("id") or ""), pair=pair, engine=_engine(record),
                     point_value=point_value_for_pair(pair))
    stary = record.get("result") or {}
    if record.get("status") != "done" or not stary.get("trades") or not trades:
        out.skipped = "bez obchodov"
        return out
    if out.point_value is None:
        out.skipped = f"neznámy inštrument {pair!r}"
        return out
    pv_inst = out.point_value
    wallet = float(stary.get("starting_balance") or nast.get("wallet") or 10_000.0)

    nove: list[dict[str, Any]] = []
    for t in trades:
        row = dict(t)
        if "point_value" not in row and pv_inst != 1.0:
            row["point_value"] = pv_inst
            out.trades_changed += 1
            if "gross_abs" in row:
                # záznam emulátora: zisk obchodu už hodnotu bodu mal (a z nezaokrúhlených
                # cien) — chýbala len v súhrne, obchod sa nemení
                nove.append(row)
                continue
            m = row_money(row)
            net = m.net + float(row.get("funding_fees") or 0.0)
            lev = max(float(row.get("leverage") or 1.0), 1.0)
            stake = m.notional_open / lev
            row["profit_abs"] = round(net, 4)
            row["stake_amount"] = round(stake, 4)
            row["profit_ratio"] = round(net / stake, 6) if stake else 0.0
            row["gross_abs"] = round(m.gross, 4)
            row["fees_abs"] = round(m.fees, 4)
        elif "gross_abs" not in row and row_point_value(row) != 1.0:
            m = row_money(row)
            row["gross_abs"], row["fees_abs"] = round(m.gross, 4), round(m.fees, 4)
        nove.append(row)
    nove.sort(key=lambda r: str(r.get("close_date") or ""))

    money = summary_money(nove, wallet)
    novy = dict(stary)
    for k in SUMMARY_KEYS:
        if k not in money:
            continue
        if k not in stary or _differs(stary.get(k), money[k]):
            out.changes[k] = (stary.get(k), money[k])
            novy[k] = money[k]
    out.summary = novy
    out.trades = nove
    if out.trades_changed or "pnl_abs" in out.changes:
        from tradebot.adapters.multicharts.emulator import equity_series

        out.series_equity = equity_series(nove, wallet)
    if out.engine == "freqtrade" and pv_inst != 1.0 and out.trades_changed:
        out.warning = ("Freqtrade beh spred hodnoty bodu: CFD bežal ako spot, shorty a páka "
                       "chýbajú — peniaze sú prepočítané, beh treba zopakovať")
    return out


def _runs(root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    for d in sorted(root.iterdir()) if root.exists() else ():
        p = d / "run.json"
        if d.name.startswith(".") or not p.exists():
            continue
        try:
            yield d, json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


def scan(root: Path | None = None, *, pair: str | None = None,
         write: bool = False) -> list[Recomputed]:
    """Prepočet všetkých behov v `root` (default `tester/runs`). `write` = zapísať zmeny."""
    from tradebot.core.paths import RUNS_DIR

    from .webapp.store import _write_json

    root = Path(root) if root is not None else RUNS_DIR
    out = []
    for d, rec in _runs(root):
        if pair and (rec.get("settings") or {}).get("pair") != pair:
            continue
        tp = d / "trades.json"
        try:
            trades = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else []
        except (OSError, json.JSONDecodeError):
            trades = []
        r = recompute_run(rec, trades)
        out.append(r)
        if write and r.changed and r.summary is not None:
            rec = dict(rec)
            rec["result"] = r.summary
            if r.series_equity is not None and isinstance(rec.get("series"), dict):
                rec["series"] = {**rec["series"], "equity": r.series_equity}
            _write_json(d / "run.json", rec)
            if r.trades_changed:
                _write_json(tp, r.trades)
    return out


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    return str(v)


def report(results: list[Recomputed], *, examples: int = 1, write: bool = False) -> str:
    """Výpis po inštrumentoch: koľko behov, koľko by sa zmenilo, príklad pred/po."""
    by: dict[tuple[str, str], list[Recomputed]] = {}
    for r in results:
        by.setdefault((r.pair, r.engine), []).append(r)
    riadky = [("zapísané" if write else "DRY-RUN (nič sa nezapísalo; --write zapíše)"), ""]
    riadky.append(f"{'pár':<18} {'engine':<12} {'bod':>9} {'behov':>6} {'zmena':>6} {'preskoč.':>8}")
    for (pair, eng), rs in sorted(by.items(), key=lambda x: (-sum(r.changed for r in x[1]), x[0])):
        pv = rs[0].point_value
        riadky.append(f"{pair:<18} {eng:<12} {_fmt(pv) if pv is not None else '?':>9} {len(rs):>6} "
                      f"{sum(r.changed for r in rs):>6} {sum(bool(r.skipped) for r in rs):>8}")
    zmenene = [r for r in results if r.changed]
    riadky += ["", f"spolu {len(results)} behov, zmenilo by sa {len(zmenene)}"
               f" (z toho {sum(bool(r.trades_changed) for r in zmenene)} aj obchody)"]
    kluce: dict[str, int] = {}
    for r in zmenene:
        for k in r.changes:
            kluce[k] = kluce.get(k, 0) + 1
    if kluce:
        riadky.append("zmenené polia súhrnu: " + ", ".join(
            f"{k} {n}" for k, n in sorted(kluce.items(), key=lambda x: -x[1])))
    ukazane: dict[tuple[str, str], int] = {}
    for r in zmenene:
        kluc = (r.pair, r.engine)
        if ukazane.get(kluc, 0) >= examples:
            continue
        ukazane[kluc] = ukazane.get(kluc, 0) + 1
        riadky.append(f"\n  {r.run_id}  {r.pair} {r.engine}  (bod {_fmt(r.point_value)}, "
                      f"obchodov prepočítaných {r.trades_changed})")
        for k in SHOWN:
            if k in r.changes:
                pred, po = r.changes[k]
                riadky.append(f"    {k:<18} {_fmt(pred):>18} -> {_fmt(po)}")
        if r.warning:
            riadky.append(f"    POZOR: {r.warning}")
    return "\n".join(riadky)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.recompute", description=__doc__.split("\n\n")[0])
    ap.add_argument("--pair", help="len behy na tomto páre (napr. MNQ/USD)")
    ap.add_argument("--root", help="adresár behov (default tester/runs)")
    ap.add_argument("--examples", type=int, default=1, help="príkladov pred/po na pár a engine")
    ap.add_argument("--write", action="store_true", help="naozaj prepísať run.json a trades.json")
    ap.add_argument("--json", action="store_true", help="strojový výpis zmien")
    args = ap.parse_args(argv)
    results = scan(Path(args.root) if args.root else None, pair=args.pair, write=args.write)
    if args.json:
        print(json.dumps([{"run_id": r.run_id, "pair": r.pair, "engine": r.engine,
                           "point_value": r.point_value, "trades_changed": r.trades_changed,
                           "changes": r.changes, "warning": r.warning, "skipped": r.skipped}
                          for r in results if r.changed], ensure_ascii=False, indent=2, default=str))
    else:
        print(report(results, examples=args.examples, write=args.write))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
