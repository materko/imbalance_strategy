"""Monte Carlo nad hotovým behom — aký široký je interval okolo nameraného čísla.

    python -m tester.montecarlo                     # posledný beh v histórii
    python -m tester.montecarlo <run_id>
    python -m tester.montecarlo <run_id> --fee 0.05 --iterations 20000
    python -m tester.montecarlo <run_id> --json

### Načo to je
Backtest dá jedno číslo: break-even poplatok 0,0176 %. Nepovie, či by na inej vzorke
nevyšlo 0,004 alebo 0,03. Pri stratégii, ktorej edge je zhruba veľkosť poplatku, je
práve táto šírka to podstatné — bodový odhad z 12 obchodov a z 800 obchodov vyzerá
v tabuľke rovnako, hoci hovorí niečo úplne iné.

### Ako
**Bootstrap** (ťahanie s opakovaním): z nameraných obchodov sa poskladá `--iterations`
nových sérií rovnakej dĺžky a z každej sa spočíta break-even poplatok a čistý PnL.
Rozptyl výsledkov je ten, ktorý čakať od tej istej stratégie na inej vzorke.

**Permutácia poradia** (bez opakovania): tie isté obchody v inom poradí. Súčet je
invariantný, mení sa len cesta — takto vzniká rozdelenie max. drawdownu. Nameraný
drawdown je jedna z tých ciest a spravidla nie tá najhoršia.

Obidve časti počítajú s hrubým ziskom a obchodovaným objemom (rovnako ako
`tester.fees`), takže výsledok **nezávisí od toho, s akým `--fee` bežal backtest** —
sadzba sa dosadí až tu.

### Čo to NErieši
**Preoptimalizovanie neodhalí.** Bootstrap in-sample obchodov z preladenej
konfigurácie vyzerá výborne — tie obchody naozaj ziskové boli, chyba bola vo výbere
najlepšieho z dvesto epoch. Proti tomu chránia jedine dáta, ktoré optimalizátor
nevidel; u nás päť referenčných okien, viď
[docs/merania/HYPEROPT_uzky_2026-09-04.md](../docs/merania/HYPEROPT_uzky_2026-09-04.md).

Ďalej predpokladá, že obchody sú **nezávislé a rovnako rozdelené**: nemodeluje
zhlukovanie volatility ani to, že straty chodia v sérii (na to by bol blokový
bootstrap). A berie PnL v absolútnej mene tak, ako vyšiel, teda **bez zloženého
úročenia** — risk-based sizing by na inej equity krivke otvoril iné veľkosti pozícií.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

#: Nad týmto počtom obchodov už interval niečo znamená. Pod ním je široký tak, že
#: jediný poctivý záver je „málo dát" — a presne to má výpis povedať nahlas.
MIN_TRADES = 30

#: Po koľkých opakovaniach naraz sa počíta. Matica je `chunk x n`; pri tisícoch
#: obchodov a desaťtisícoch opakovaní by celá naraz zabrala stovky MB.
_CHUNK_CELLS = 2_000_000


def _chunks(iterations: int, n: int) -> list[int]:
    step = max(1, _CHUNK_CELLS // max(n, 1))
    out = [step] * (iterations // step)
    if iterations % step:
        out.append(iterations % step)
    return out


def per_trade(trades: list[dict[str, Any]]):
    """(hrubý zisk, obchodovaný objem) na obchod, v mene účtu.

    Hrubý zisk je z cien, nie z `profit_abs`, takže v ňom nie sú poplatky behu.
    Objem je vstup + výstup, teda základ, z ktorého sa poplatok počíta — rovnaká
    definícia ako v `tester.fees` a v súhrne behu.
    """
    import numpy as np

    if not trades:
        raise ValueError("beh nemá obchody — nie je čo premiešavať")

    direction = np.array([-1.0 if t.get("is_short") else 1.0 for t in trades])
    open_rate = np.array([float(t["open_rate"]) for t in trades])
    close_rate = np.array([float(t["close_rate"]) for t in trades])
    amount = np.array([float(t["amount"]) for t in trades])

    gross = (close_rate - open_rate) * amount * direction
    volume = (open_rate + close_rate) * amount
    return gross, volume


def _drawdown(equity):
    """Max pokles od doterajšieho vrcholu; vrchol začína na nule (štartovací zostatok)."""
    import numpy as np

    eq = np.concatenate([np.zeros((equity.shape[0], 1)), equity], axis=1)
    return (np.maximum.accumulate(eq, axis=1) - eq).max(axis=1)


def _stats(sample, observed: float, lo_q: float, hi_q: float) -> dict[str, float]:
    import numpy as np

    return {
        "observed": float(observed),
        "median": float(np.median(sample)),
        "lo": float(np.percentile(sample, lo_q)),
        "hi": float(np.percentile(sample, hi_q)),
    }


def analyze(
    trades: list[dict[str, Any]],
    fee_pct: float = 0.0,
    iterations: int = 10_000,
    seed: int = 0,
    ci: float = 90.0,
) -> dict[str, Any]:
    """Rozdelenia break-even poplatku, čistého PnL a max drawdownu.

    `fee_pct` je poplatok v percentách **na jednu stranu** (Binance taker 0,05).
    `seed` je fixný, aby sa dal ten istý výpis zopakovať a citovať v meraní.
    """
    import numpy as np

    gross, volume = per_trade(trades)
    n = len(gross)
    rng = np.random.default_rng(seed)
    lo_q = (100.0 - ci) / 2.0
    hi_q = 100.0 - lo_q

    # -- bootstrap: iná vzorka tej istej stratégie --------------------------- #
    be_s, net_s = [], []
    for chunk in _chunks(iterations, n):
        idx = rng.integers(0, n, size=(chunk, n))
        g = gross[idx].sum(axis=1)
        v = volume[idx].sum(axis=1)
        be_s.append(np.where(v > 0, g / v * 100.0, np.nan))
        net_s.append(g - v * fee_pct / 100.0)
    be_s = np.concatenate(be_s)
    net_s = np.concatenate(net_s)

    # -- permutácia poradia: tie isté obchody, iná cesta --------------------- #
    net_trade = gross - volume * fee_pct / 100.0
    dd_s = []
    for chunk in _chunks(iterations, n):
        perm = rng.random((chunk, n)).argsort(axis=1)
        dd_s.append(_drawdown(np.cumsum(net_trade[perm], axis=1)))
    dd_s = np.concatenate(dd_s)

    gross_sum = float(gross.sum())
    volume_sum = float(volume.sum())
    observed_be = gross_sum / volume_sum * 100.0 if volume_sum else float("nan")
    observed_dd = float(_drawdown(np.cumsum(net_trade)[None, :])[0])

    return {
        "n": n,
        "iterations": iterations,
        "seed": seed,
        "ci": ci,
        "fee_pct": fee_pct,
        "gross": gross_sum,
        "volume": volume_sum,
        "break_even": {
            **_stats(be_s, observed_be, lo_q, hi_q),
            "p_above_fee": float((be_s > fee_pct).mean()),
        },
        # `p_positive` je tá istá udalosť ako `p_above_fee` (zisk > 0 práve vtedy, keď
        # hrubý zisk na objem prevýši sadzbu) — vo výpise sa preto uvádza raz.
        "net": {
            **_stats(net_s, float(net_trade.sum()), lo_q, hi_q),
            "p_positive": float((net_s > 0).mean()),
        },
        "drawdown": {
            **_stats(dd_s, observed_dd, lo_q, hi_q),
            "p95": float(np.percentile(dd_s, 95.0)),
            "worst": float(dd_s.max()),
        },
    }


def report(result: dict[str, Any], label: str = "", currency: str = "USDT") -> str:
    """Výpis pre konzolu. Bez diakritiky — Windows konzola beží v systémovej kódovej stránke."""
    fee = result["fee_pct"]
    be, net, dd = result["break_even"], result["net"], result["drawdown"]
    ci = result["ci"]
    out = [f"\n=== Monte Carlo{': ' + label if label else ''} ==="]
    out.append(f"  obchodov              {result['n']}")
    out.append(f"  opakovani             {result['iterations']:,} (seed {result['seed']})")
    out.append(f"  poplatok v prepocte   {fee:.4f} % na stranu")

    out.append(f"\n  BREAK-EVEN POPLATOK (% na stranu)")
    out.append(f"    namerany            {be['observed']:.4f}")
    out.append(f"    median              {be['median']:.4f}")
    out.append(f"    {ci:.0f} % interval       {be['lo']:.4f} - {be['hi']:.4f}")
    out.append(f"    P(edge > poplatok)  {100 * be['p_above_fee']:.1f} %  (= P(cisty zisk > 0))")

    out.append(f"\n  CISTY PnL pri {fee:.4f} % ({currency})")
    out.append(f"    namerany            {net['observed']:+,.0f}")
    out.append(f"    median              {net['median']:+,.0f}")
    out.append(f"    {ci:.0f} % interval       {net['lo']:+,.0f} - {net['hi']:+,.0f}")

    out.append(f"\n  MAX DRAWDOWN ({currency}) - permutacia poradia, tie iste obchody")
    out.append(f"    namerany            {dd['observed']:,.0f}")
    out.append(f"    median              {dd['median']:,.0f}")
    out.append(f"    95. percentil       {dd['p95']:,.0f}")
    out.append(f"    najhorsia cesta     {dd['worst']:,.0f}")

    if result["n"] < MIN_TRADES:
        out.append(
            f"\n  POZOR: {result['n']} obchodov je pod hranicou {MIN_TRADES}. Interval je taky"
            "\n  siroky, ze o strategii nehovori nic - je to anekdota, nie vysledok."
        )
    if be["p_above_fee"] < 0.95 and fee > 0:
        out.append(
            f"\n  Edge nad poplatkom nie je isty: v {100 * (1 - be['p_above_fee']):.0f} % vzoriek"
            "\n  by burza zobrala viac, nez strategia zarobi."
        )
    out.append(
        "\n  Bootstrap nemeria preoptimalizovanie - hovori len o rozptyle vzorky."
        "\n  Ci nastavenie prezije, ukazu az data, ktore optimalizator nevidel."
    )
    return "\n".join(out)


def _label(record: dict[str, Any]) -> tuple[str, str]:
    """(popis behu do hlavičky, mena účtu)."""
    s = record.get("settings") or {}
    r = record.get("result") or {}
    bits = [str(v) for v in (s.get("pair"), s.get("timeframe"), s.get("timerange"),
                             r.get("engine") or s.get("engine")) if v]
    note = record.get("note")
    label = f"{record.get('id', '?')}  {' '.join(bits)}"
    if note:
        label += f'  "{note}"'
    return label, str(r.get("stake_currency", "USDT"))


def main(argv: list[str] | None = None) -> int:
    from .webapp.store import RunStore

    ap = argparse.ArgumentParser(
        prog="python -m tester.montecarlo",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("run", nargs="?", help="run_id z histórie (default: posledný beh s obchodmi)")
    ap.add_argument("--fee", type=float, default=None,
                    help="poplatok v %% na stranu (default: ten, s ktorým beh bežal)")
    ap.add_argument("--iterations", type=int, default=10_000, help="počet opakovaní")
    ap.add_argument("--seed", type=int, default=0, help="seed generátora (rovnaký = rovnaký výpis)")
    ap.add_argument("--ci", type=float, default=90.0, help="šírka intervalu v %% (default 90)")
    ap.add_argument("--json", action="store_true", help="výsledok ako JSON namiesto výpisu")
    args = ap.parse_args(argv)

    store = RunStore()
    if args.run:
        record = store.get(args.run)
        if record is None:
            print(f"beh {args.run} v histórii nie je")
            return 1
    else:
        record = next(
            (r for r in store.all()
             if r.get("status") == "done" and (r.get("result") or {}).get("trades")),
            None,
        )
        if record is None:
            print("história nemá dokončený beh s obchodmi")
            return 1

    trades = store.trades(record["id"])
    if not trades:
        print(f"beh {record['id']} nemá uložené obchody")
        return 1

    fee_pct = args.fee if args.fee is not None else float((record.get("settings") or {}).get("fee") or 0.0) * 100.0
    result = analyze(trades, fee_pct=fee_pct, iterations=args.iterations, seed=args.seed, ci=args.ci)
    result["run_id"] = record["id"]

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        label, currency = _label(record)
        print(report(result, label, currency))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
