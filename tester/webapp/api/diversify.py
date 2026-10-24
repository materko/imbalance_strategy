"""Diverzifikácia: obchody vybraných nastavení pre spoločný prepočet (`/api/diversify`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..store import strategy_of
from .context import AppContext

def _utc(iso: str) -> str:
    """`2021-10-01T13:45:00+00:00` → `2021-10-01T13:45:00Z` (to isté, kratšie)."""
    return str(iso).replace("+00:00", "Z")


def _day(iso: str) -> str:
    """Deň obchodu = dátum zatvorenia v UTC, ako na stránke výsledkov (`tester/dashboard`)
    a v prehľade „Trojica stratégií MNQ" - nech denné čísla sedia s nimi."""
    return str(iso)[:10]


def setting_trades(store, run_ids: list[str]) -> dict[str, Any]:
    """Obchody jedného nastavenia z jeho behov (typicky päť referenčných okien).

    Okná `20231001-20241001` a `20240904-20250904` sa prekrývajú o september 2024; ten
    istý obchod je potom v dvoch behoch a do súčtu ide raz. Kontrola dát ukáže, koľko
    sa ich zahodilo a či sa niektoré pozície nastavenia neprekrývajú v čase.
    """
    recs = [rec for rec in (store.get(i) for i in run_ids) if rec]
    if not recs:
        raise HTTPException(404, "vybrané behy v histórii nie sú")
    strategies = sorted({strategy_of(r) for r in recs})
    if len(strategies) > 1:
        raise HTTPException(422, f"behy jedného nastavenia patria rôznym stratégiám: {', '.join(strategies)}")
    # Poplatok nie je súčasť nastavenia, takže pod jedným nastavením môžu byť behy
    # s rôznym poplatkom. Ten istý obchod by mal v každom iný PnL - berie sa poplatok
    # väčšiny behov, ostatné behy sa vynechajú a kontrola dát ich vymenuje.
    fees = [(r.get("settings") or {}).get("fee") for r in recs]
    fee = max(dict.fromkeys(fees), key=fees.count)
    skipped = [{"run_id": r["id"], "timerange": (r.get("settings") or {}).get("timerange"),
                "fee": (r.get("settings") or {}).get("fee")}
               for r in recs if (r.get("settings") or {}).get("fee") != fee]
    recs = [r for r in recs if (r.get("settings") or {}).get("fee") == fee]
    seen: set[tuple] = set()
    trades: list[list[Any]] = []
    windows, duplicates = [], 0
    for rec in sorted(recs, key=lambda r: (r.get("settings") or {}).get("timerange") or ""):
        s = rec.get("settings") or {}
        n = 0
        for t in store.trades(rec["id"]) or []:
            if not t.get("open_date") or not t.get("close_date"):
                continue
            key = (t["open_date"], bool(t.get("is_short")), round(float(t.get("open_rate") or 0), 6))
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            n += 1
            trades.append([_utc(t["open_date"]), _utc(t["close_date"]), "S" if t.get("is_short") else "L",
                           t.get("open_rate"), t.get("close_rate"), round(float(t.get("profit_abs") or 0), 2),
                           t.get("exit_reason") or "", _day(t["close_date"])])
        windows.append({"run_id": rec["id"], "timerange": s.get("timerange"), "trades": n,
                        "pair": s.get("pair"), "timeframe": s.get("timeframe"), "engine": s.get("engine"),
                        "fee": s.get("fee")})
    trades.sort(key=lambda x: x[0])
    # Prekrytie: nastavenie drží najviac jednu pozíciu - nový vstup pred výstupom
    # predošlého je chyba dát (alebo zlé zlúčenie okien), nie diverzifikácia.
    overlapping = sum(1 for a, b in zip(trades, trades[1:]) if b[0] < a[1])
    return {"strategy": strategies[0], "fee": fee, "trades": trades, "windows": windows,
            "skipped": skipped, "duplicates": duplicates, "overlapping": overlapping}


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store

    @router.get("/api/diversify/trades")
    def diversify_trades(runs: str = Query(..., min_length=1)):
        """Obchody nastavenia zo zadaných behov (id oddelené čiarkou), bez duplicít
        z prekrývajúcich sa okien. Polia obchodu: otvorenie a zatvorenie (UTC), smer
        L/S, vstup, výstup, PnL v $, dôvod výstupu, deň (dátum zatvorenia v UTC).
        Všetko ostatné (roky, mesiace, dni, korelácie) počíta stránka - násobok veľkosti
        sa mení bez nového dopytu."""
        ids = [r.strip() for r in runs.split(",") if r.strip()]
        return setting_trades(store, ids)

    return router
