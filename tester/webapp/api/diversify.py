"""Diverzifikácia: obchody vybraných nastavení pre spoločný prepočet (`/api/diversify`), obchody
živých stratégií pre kartu Naživo (`/api/diversify/live`) a živé behy zo skladu `data_live` k nastaveniam
(`/api/diversify/livedata`: skutočné obchody, sviečky za hranicou živého behu a simulácia toho obdobia)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
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

    # Karta Naživo: tá istá sekcia `live` ako na stránke výsledkov (tester/dashboard/live.py) zo zrkadla
    # webapp. Čítanie zrkadla trvá ~1 s, preto krátka cache — karta sa otvára a prepína často.
    cache: dict[str, Any] = {"t": 0.0, "data": None}
    lock = threading.Lock()

    def _mirror_path() -> Path:
        from tradebot.core.paths import LIVE_MIRROR

        mirror = getattr(ctx.app.state, "live_mirror", None)
        return Path(getattr(mirror, "mirror_path", None) or LIVE_MIRROR)

    @router.get("/api/diversify/live")
    def diversify_live(fresh: bool = False):
        """Inštancie naživo s obchodmi, otvorenými pozíciami, signálmi a varovaniami (formát sekcie `live`
        v tester/dashboard/README.md). Párovanie s behmi v histórii a celý prepočet robí stránka."""
        from tester.dashboard.live import build_live

        with lock:
            if fresh or cache["data"] is None or time.monotonic() - cache["t"] > LIVE_CACHE_S:
                cache["data"], cache["t"] = build_live(_mirror_path()), time.monotonic()
            return cache["data"]

    @router.get("/api/diversify/livedata")
    def diversify_livedata():
        """Živé behy v `data_live` (aj stratégie, ktoré už nebežia): jeden riadok na inštanciu × profil
        s obdobím a počtom skutočných obchodov. Párovanie s nastavením robí stránka (meno profilu)."""
        from tester import livedata

        runs = []
        for inst in livedata.instances():
            trades = livedata.trades(inst["id"])
            by_profile: dict[str, list[dict[str, Any]]] = {}
            for s in inst.get("sessions") or []:
                by_profile.setdefault(s.get("profile") or "", []).append(s)
            for profile, ses in by_profile.items():
                if profile not in (inst.get("configs") or {}):
                    continue
                runs.append({"instance": inst["id"], "profile": profile, "platform": inst["platform"],
                             "account": inst["account"], "symbol": inst["symbol"], "tf": inst["tf"],
                             "engine": inst["engine"], "strategy": inst["strategy"],
                             "start": min((x["start"] for x in ses if x.get("start")), default=None),
                             "end": max(((x.get("end") or x["start"]) for x in ses if x.get("start")), default=None),
                             "trades": sum(1 for t in trades if t.get("profile") == profile)})
        return {"runs": runs}

    @router.get("/api/diversify/livedata/view")
    def diversify_livedata_view(instance: str = Query(..., min_length=1), profile: str | None = None,
                                pair: str | None = None):
        """Živý beh k nastaveniu: hranica (odkiaľ sú dáta zo živého behu), sviečky pred ňou (stiahnuté)
        a za ňou (živé), skutočné obchody, simulácia toho istého obdobia a ich párovanie (`tester.livesim`)."""
        from tester import livesim

        try:
            return livesim.live_view(instance, profile=profile, pair=pair)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from None

    return router


LIVE_CACHE_S = 30.0
