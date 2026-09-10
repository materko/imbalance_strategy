"""Monte Carlo nad hotovým behom — interval okolo výsledku a riziko účtu.

    python -m tester.montecarlo                          # posledný beh v histórii
    python -m tester.montecarlo <run_id> --fee 0.05
    python -m tester.montecarlo <run_id> --risk 250      # 250 USD rizika na obchod
    python -m tester.montecarlo <run_id> --account 25000 --limits 10,20,30
    python -m tester.montecarlo <run_id> --risk-pct 1    # riziko ako % z equity (zložené)
    python -m tester.montecarlo <run_id> --json

### Načo to je
Backtest dá jedno číslo. Nepovie ani to, či by na inej vzorke nevyšlo úplne iné, ani
to, aký veľký účet treba, aby ho séria strát neodpísala. Toto počíta oboje z toho, čo
už v behu je — zo zoznamu obchodov, bez ďalšieho backtestu.

### Ako
Z nameraných obchodov sa ťahá `--iterations` nových sérií rovnakej dĺžky, a to
**po blokoch** (`--block`, default 10 po sebe idúcich obchodov). Blok je tam preto, že
straty nechodia rovnomerne: jeden režim trhu vyrobí päť SL za sebou a losovanie
obchod po obchode by takú sériu skoro nikdy nevyrobilo — a práve tá zabíja účet.
`--block 1` je klasický bootstrap s nezávislými obchodmi.

Z každej série sa počíta:

* **break-even poplatok** a čistý PnL — aký široký je interval okolo nameraného čísla,
  teda či je edge skutočný, alebo to bola vzorka;
* **priebeh účtu** — max drawdown, ako často účet klesne pod zadané hranice, najdlhšia
  séria strát, najdlhšie čakanie na nové maximum a konečný zostatok.

Veľkosť pozície: obchody sa preškálujú z rizika, s akým beh bežal, na `--risk`. Ktoré
pole configu to riziko nesie, povie stratégia v registry (`SPEC.risk_field` — IBS
`maxLossDollar`, ukážka `riskDollar`); tento modul názov poľa nepozná. Pri `--risk-pct`
sa riskuje percento z **aktuálnej** equity, teda so zloženým úročením. Profil s pevným
počtom kontraktov (`SPEC.fixed_size_field`, pri IBS `legacyPineSizing`) sa škálovať
nedá — vtedy sa počíta veľkosť z behu tak, ako je.

### Čo to NErieši
**Preoptimalizovanie neodhalí.** Obchody preladenej konfigurácie naozaj ziskové boli,
chyba bola vo výbere najlepšej z dvesto epoch. Proti tomu chránia jedine dáta, ktoré
optimalizátor nevidel — u nás päť referenčných okien, viď
[docs/merania/HYPEROPT_uzky_2026-09-04.md](../docs/merania/HYPEROPT_uzky_2026-09-04.md).

**Počíta len uzavreté obchody.** Pozícia, ktorá išla hlboko proti a nakoniec vyšla na
TP, je tu neviditeľná — pre margin a likvidáciu pri páke je pritom rozhodujúca.
Rovnako tu nie sú denné limity strát (séria nemá dátumy), zmena režimu trhu, ani
korelácia medzi viacerými účtami na tej istej stratégii.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

#: Nad týmto počtom obchodov už interval niečo znamená. Pod ním je široký tak, že
#: jediný poctivý záver je „málo dát" — a presne to má výpis povedať nahlas.
MIN_TRADES = 30

#: Dĺžka bloku pri losovaní. Desať obchodov je zhruba jeden „režim" na 3m grafe:
#: dosť na to, aby sa séria strát preniesla do vzorky, málo na to, aby sa všetky
#: série tvárili rovnako.
DEFAULT_BLOCK = 10

#: Hranice poklesu účtu v % z počiatočného zostatku (prop firmy merajú takto).
DEFAULT_LIMITS: tuple[float, ...] = (10.0, 20.0, 30.0, 50.0)

#: Po koľkých opakovaniach naraz sa počíta. Matíc `chunk x n` je pri simulácii
#: niekoľko; celá naraz by pri tisíckach obchodov zabrala stovky MB.
_CHUNK_CELLS = 1_000_000


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


def block_size(block: int, n: int) -> int:
    """Blok nesmie byť taký dlhý, že sa z neho poskladá celá vzorka bez losovania."""
    return max(1, min(int(block), max(1, n // 5)))


def _draw(rng, chunk: int, n: int, block: int):
    """Indexy `chunk x n`: cyklický blokový bootstrap (blok 1 = nezávislé obchody)."""
    import numpy as np

    if block <= 1:
        return rng.integers(0, n, size=(chunk, n))
    blocks = -(-n // block)
    starts = rng.integers(0, n, size=(chunk, blocks, 1))
    idx = (starts + np.arange(block)) % n
    return idx.reshape(chunk, blocks * block)[:, :n]


def _longest_run(flags):
    """Najdlhšia séria `True` v každom riadku — bez cyklu cez stĺpce."""
    import numpy as np

    counted = np.cumsum(flags, axis=1)
    reset = np.where(~flags, counted, 0)
    return (counted - np.maximum.accumulate(reset, axis=1)).max(axis=1)


def _ruin(equity):
    """Účet na nule sa už neobchoduje — zvyšok cesty ostáva na nule.

    Bez toho by simulácia pokračovala do mínusu a hlásila drawdown nad 100 % aj
    konečný zostatok −122 %, čo pre úvahu o veľkosti účtu nedáva zmysel.
    """
    import numpy as np

    dead = np.maximum.accumulate(equity <= 0.0, axis=1)
    return np.where(dead, 0.0, equity)


def _drawdown(equity, start: float):
    """(pokles v mene, pokles v % z vrcholu, krivka aj so štartom).

    Vrchol začína na počiatočnom zostatku. Percento sa počíta **z vrcholu**, nie
    z počiatočného zostatku — tak to hlási aj súhrn behu a tak sa dá porovnať.
    """
    import numpy as np

    eq = np.concatenate([np.full((equity.shape[0], 1), start), equity], axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    gap = peak - eq
    return gap.max(axis=1), (gap / peak * 100.0).max(axis=1), eq


def _histogram(sample, bins: int = 40) -> dict[str, list[float]]:
    """Rozdelenie pre graf vo webapp — stredy stĺpcov a početnosti."""
    import numpy as np

    clean = sample[~np.isnan(sample)]
    counts, edges = np.histogram(clean, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    return {"centers": [float(c) for c in centers], "counts": [int(c) for c in counts]}


def _stats(sample, observed: float | None, lo_q: float, hi_q: float) -> dict[str, float]:
    import numpy as np

    out = {
        "median": float(np.median(sample)),
        "lo": float(np.percentile(sample, lo_q)),
        "hi": float(np.percentile(sample, hi_q)),
        "p95": float(np.percentile(sample, 95.0)),
        "max": float(np.max(sample)),
    }
    if observed is not None:
        out["observed"] = float(observed)
    return out


def analyze(
    trades: list[dict[str, Any]],
    fee_pct: float = 0.0,
    iterations: int = 10_000,
    seed: int = 0,
    ci: float = 90.0,
    account: float = 10_000.0,
    risk_ref: float | None = None,
    risk: float | None = None,
    risk_pct: float | None = None,
    limits: Sequence[float] = DEFAULT_LIMITS,
    block: int = DEFAULT_BLOCK,
) -> dict[str, Any]:
    """Rozdelenia break-even poplatku, čistého PnL a priebehu účtu.

    `fee_pct` je poplatok v percentách **na jednu stranu** (Binance taker 0,05).
    `risk_ref` je dolárové riziko na obchod, s akým beh bežal (`maxLossDollar`);
    bez neho sa veľkosť pozície nedá preškálovať a `risk`/`risk_pct` sa ignorujú.
    `seed` je fixný, aby sa dal ten istý výpis zopakovať a citovať v meraní.
    """
    import numpy as np

    gross, volume = per_trade(trades)
    n = len(gross)
    block = block_size(block, n)
    rng = np.random.default_rng(seed)
    lo_q = (100.0 - ci) / 2.0
    hi_q = 100.0 - lo_q

    net_trade = gross - volume * fee_pct / 100.0

    # -- veľkosť pozície: preškálovanie z rizika behu na požadované -------------- #
    compound = bool(risk_ref and risk_pct)
    scale = float(risk / risk_ref) if (risk_ref and risk) else 1.0
    #: Výsledok obchodu v násobkoch rizika — jediné, čo sa dá preniesť na iný účet.
    units = net_trade / risk_ref if risk_ref else None
    sized = net_trade * scale

    be_s, net_s, dd_s, ddp_s, min_s, raw_s, streak_s, wait_s, final_s = ([] for _ in range(9))
    for chunk in _chunks(iterations, n):
        idx = _draw(rng, chunk, n, block)

        g = gross[idx].sum(axis=1)
        v = volume[idx].sum(axis=1)
        be_s.append(np.where(v > 0, g / v * 100.0, np.nan))
        net_s.append(g - v * fee_pct / 100.0)

        if compound:
            equity = account * np.cumprod(1.0 + units[idx] * risk_pct / 100.0, axis=1)
        else:
            # neorezaná krivka drží linearitu v riziku (potrebné pre odporúčanie nižšie);
            # to, čo sa hlási, je krivka po vynulovaní zruinovaného účtu
            raw = account + np.cumsum(sized[idx], axis=1)
            raw_s.append(raw.min(axis=1))
            equity = _ruin(raw)
        dd, dd_rel, eq = _drawdown(equity, account)
        dd_s.append(dd)
        ddp_s.append(dd_rel)
        min_s.append(eq.min(axis=1))
        final_s.append(equity[:, -1])
        streak_s.append(_longest_run(sized[idx] < 0))
        wait_s.append(_longest_run(eq < np.maximum.accumulate(eq, axis=1)))

    be_s, net_s = np.concatenate(be_s), np.concatenate(net_s)
    dd_s, ddp_s, min_s = np.concatenate(dd_s), np.concatenate(ddp_s), np.concatenate(min_s)
    streak_s, wait_s, final_s = np.concatenate(streak_s), np.concatenate(wait_s), np.concatenate(final_s)
    min_raw = np.concatenate(raw_s) if raw_s else min_s

    gross_sum, volume_sum = float(gross.sum()), float(volume.sum())
    observed_be = gross_sum / volume_sum * 100.0 if volume_sum else float("nan")
    if compound:
        observed_eq = account * np.cumprod(1.0 + units * risk_pct / 100.0)[None, :]
    else:
        observed_eq = _ruin((account + np.cumsum(sized))[None, :])
    obs_dd, obs_ddp, _ = _drawdown(observed_eq, account)

    hits = [{"limit": float(lim), "p": float((min_s <= account * (1.0 - lim / 100.0)).mean())}
            for lim in limits]
    p_ruin = float((min_s <= 0.0).mean())
    #: Ako hlboko pod počiatočný zostatok cesta klesla — tá istá definícia ako hranice
    #: vyššie, takže odporúčanie k riziku sedí s riadkom „P(účet klesne o)".
    below_start = np.maximum(account - min_raw, 0.0)

    # Koľko sa smie riskovať, aby 95 % ciest zostalo nad hranicou. Pri pevnom
    # dolárovom riziku je drawdown lineárny v risku, takže stačí trojčlenka; pri
    # zloženom úročení to neplatí a odporúčanie sa nedáva.
    advice = None
    below_p95 = float(np.percentile(below_start, 95.0))
    if risk_ref and not compound and below_p95 > 0 and limits:
        target = float(limits[min(1, len(limits) - 1)])
        advice = {"limit": target,
                  "risk": risk_ref * scale * (account * target / 100.0) / below_p95}

    return {
        "n": n,
        "min_trades": MIN_TRADES,   # aby hranicu nemusel duplikovať výpis ani webapp
        "iterations": iterations,
        "seed": seed,
        "ci": ci,
        "fee_pct": fee_pct,
        "block": block,
        "gross": gross_sum,
        "volume": volume_sum,
        "break_even": {
            **_stats(be_s, observed_be, lo_q, hi_q),
            "p_above_fee": float((be_s > fee_pct).mean()),
            "hist": _histogram(be_s),
        },
        # `p_positive` je tá istá udalosť ako `p_above_fee` (zisk > 0 práve vtedy, keď
        # hrubý zisk na objem prevýši sadzbu) — vo výpise sa preto uvádza raz.
        "net": {
            **_stats(net_s, float(sized.sum()), lo_q, hi_q),
            "p_positive": float((net_s > 0).mean()),
        },
        "account": {
            "start": float(account),
            "risk": float(risk_ref * scale) if risk_ref else None,
            "risk_ref": float(risk_ref) if risk_ref else None,
            "risk_pct": float(risk_pct) if compound else None,
            "scalable": bool(risk_ref),
            "drawdown_abs": _stats(dd_s, float(obs_dd[0]), lo_q, hi_q),
            "drawdown_pct": {**_stats(ddp_s, float(obs_ddp[0]), lo_q, hi_q),
                             "hist": _histogram(ddp_s)},
            "hits": hits,
            "p_ruin": p_ruin,
            "losing_streak": _stats(streak_s.astype(float), None, lo_q, hi_q),
            "wait_for_high": _stats(wait_s.astype(float), None, lo_q, hi_q),
            "final_pct": _stats((final_s / account - 1.0) * 100.0, None, lo_q, hi_q),
            "advice": advice,
        },
    }


def report(result: dict[str, Any], label: str = "", currency: str = "USDT") -> str:
    """Výpis pre konzolu. Bez diakritiky — Windows konzola beží v systémovej kódovej stránke."""
    fee = result["fee_pct"]
    be, net, acc = result["break_even"], result["net"], result["account"]
    ci = result["ci"]
    money = lambda v: f"{v:,.0f} {currency}"  # noqa: E731

    out = [f"\n=== Monte Carlo{': ' + label if label else ''} ==="]
    out.append(f"  obchodov              {result['n']}")
    out.append(f"  opakovani             {result['iterations']:,} (seed {result['seed']}), "
               f"bloky po {result['block']}")
    out.append(f"  poplatok v prepocte   {fee:.4f} % na stranu")

    out.append("\n  BREAK-EVEN POPLATOK (% na stranu)")
    out.append(f"    namerany            {be['observed']:.4f}")
    out.append(f"    median              {be['median']:.4f}")
    out.append(f"    {ci:.0f} % interval       {be['lo']:.4f} - {be['hi']:.4f}")
    out.append(f"    P(edge > poplatok)  {100 * be['p_above_fee']:.1f} %  (= P(cisty zisk > 0))")

    out.append(f"\n  CISTY PnL pri {fee:.4f} % ({currency})")
    out.append(f"    namerany            {net['observed']:+,.0f}")
    out.append(f"    median              {net['median']:+,.0f}")
    out.append(f"    {ci:.0f} % interval       {net['lo']:+,.0f} - {net['hi']:+,.0f}")

    if acc["risk_pct"]:
        sizing = f"riziko {acc['risk_pct']:g} % z equity na obchod (zlozene)"
    elif acc["risk"]:
        sizing = f"riziko {money(acc['risk'])} na obchod"
    else:
        sizing = "velkost pozicie z behu (neskalovatelna)"
    dd, fin = acc["drawdown_pct"], acc["final_pct"]
    out.append(f"\n  UCET {money(acc['start'])}, {sizing}")
    out.append(f"    max drawdown        median {dd['median']:.1f} %   "
               f"95. p. {dd['p95']:.1f} %   najhorsi {dd['max']:.1f} %")
    out.append("    P(ucet klesne o)    " + "   ".join(
        f"-{h['limit']:.0f} %: {100 * h['p']:.1f} %" for h in acc["hits"]))
    out.append(f"    P(ruina, ucet na 0) {100 * acc['p_ruin']:.1f} %")
    st, wt = acc["losing_streak"], acc["wait_for_high"]
    out.append(f"    seria strat         median {st['median']:.0f}   95. p. {st['p95']:.0f}   "
               f"najdlhsia {st['max']:.0f} obchodov")
    out.append(f"    cakanie na nove max median {wt['median']:.0f}   95. p. {wt['p95']:.0f}   "
               f"najdlhsie {wt['max']:.0f} obchodov")
    out.append(f"    konecny zostatok    median {fin['median']:+.1f} %   "
               f"{ci:.0f} % interval {fin['lo']:+.1f} % - {fin['hi']:+.1f} %")
    if acc["advice"]:
        a = acc["advice"]
        out.append(f"    riziko pre -{a['limit']:.0f} %    najviac {money(a['risk'])} na obchod, "
                   "aby 95 % ciest zostalo nad hranicou")

    if result["n"] < result["min_trades"]:
        out.append(
            f"\n  POZOR: {result['n']} obchodov je pod hranicou {result['min_trades']}. Interval je taky"
            "\n  siroky, ze o strategii nehovori nic - je to anekdota, nie vysledok.")
    if be["p_above_fee"] < 0.95 and fee > 0:
        out.append(
            f"\n  Edge nad poplatkom nie je isty: v {100 * (1 - be['p_above_fee']):.0f} % vzoriek"
            "\n  by burza zobrala viac, nez strategia zarobi.")
    out.append(
        "\n  Bootstrap nemeria preoptimalizovanie - hovori len o rozptyle vzorky."
        "\n  Ucet sa pocita z uzavretych obchodov: priebeh otvorenej pozicie (a teda"
        "\n  margin) v tom nie je, rovnako ako denne limity strat.")
    return "\n".join(out)


def sizing_of(record: dict[str, Any]) -> float | None:
    """Dolárové riziko na obchod, s akým beh bežal — alebo `None`, ak sa nedá preškálovať.

    Ktoré pole je riziko a ktoré prepínač pevnej veľkosti, vie len stratégia
    (`SPEC.risk_field`, `SPEC.fixed_size_field`). Pevný počet kontraktov (pri IBS Pine
    `legacyPineSizing`) nie je riziko: taký beh sa dá premiešať, ale nie prepočítať
    na iný účet.
    """
    from tradebot.strategies import get_spec

    from .webapp.store import strategy_of

    params = record.get("params") or {}
    try:
        spec = get_spec(strategy_of(record))
    except KeyError:
        return None
    if spec.fixed_size_field and params.get(spec.fixed_size_field):
        return None
    value = params.get(spec.risk_field) if spec.risk_field else None
    return float(value) if value else None


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
    ap.add_argument("--account", type=float, default=None,
                    help="veľkosť účtu (default: peňaženka behu)")
    ap.add_argument("--risk", type=float, default=None,
                    help="dolárové riziko na obchod (default: maxLossDollar z behu)")
    ap.add_argument("--risk-pct", type=float, default=None,
                    help="riziko ako %% z aktuálnej equity — zložené úročenie")
    ap.add_argument("--limits", default=",".join(f"{x:g}" for x in DEFAULT_LIMITS),
                    help="hranice poklesu účtu v %% (čiarkou)")
    ap.add_argument("--block", type=int, default=DEFAULT_BLOCK,
                    help="dĺžka bloku pri losovaní; 1 = nezávislé obchody")
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

    settings = record.get("settings") or {}
    fee_pct = args.fee if args.fee is not None else float(settings.get("fee") or 0.0) * 100.0
    account = args.account if args.account is not None else float(settings.get("wallet") or 10_000.0)
    risk_ref = sizing_of(record)
    result = analyze(
        trades, fee_pct=fee_pct, iterations=args.iterations, seed=args.seed, ci=args.ci,
        account=account, risk_ref=risk_ref, risk=args.risk if args.risk else risk_ref,
        risk_pct=args.risk_pct, block=args.block,
        limits=[float(x) for x in args.limits.split(",") if x.strip()],
    )
    result["run_id"] = record["id"]

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        label, currency = _label(record)
        print(report(result, label, currency))
        if args.risk and not risk_ref:
            print("\n  (--risk sa ignoruje: beh ma pevny pocet kontraktov, nie dolarove riziko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
