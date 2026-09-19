"""História analytiky a posudok (`/api/analytics/history`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from tradebot.strategies import STRATEGIES

from ..anstore import fingerprint as an_fingerprint, summary as an_summary
from .common import clean_user, market_config_key
from .context import AppContext
from .models import PosudokRequest, NoteRequest, AnalyticsSaveRequest


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    anstore = ctx.anstore

    def _config_of_runs(run_ids: list[str]) -> dict[str, Any]:
        """Konfigurácia behov analytiky: nastavenie (parametre; `mixed` pri viacerých),
        trh (`pár|TF`; `mixed` pri viacerých), profil, okná, TF."""
        from ... import analytics as an

        zaznamy = [z for z in (store.get(i) for i in run_ids) if z]
        kluce = {an.config_key(z) for z in zaznamy}
        trhy = {market_config_key(z).split("|", 1)[1] for z in zaznamy}
        nast = [z.get("settings") or {} for z in zaznamy]
        return {
            "config_key": (kluce.pop() if len(kluce) == 1 else ("mixed" if kluce else "")),
            "market": (trhy.pop() if len(trhy) == 1 else ("mixed" if trhy else "")),
            "profile": next((s.get("profile") for s in nast if s.get("profile")), "")
                       or ("(Pine defaulty)" if nast else ""),
            "timeranges": sorted({s["timerange"] for s in nast if s.get("timerange")}),
            "timeframes": sorted({s["timeframe"] for s in nast if s.get("timeframe")}),
        }

    @router.get("/api/analytics/history")
    def analytics_history(strategy: str = "", limit: int = Query(50, ge=1, le=500),
                          config_key: str = "", market: str = ""):
        """Uložené analytiky — per stratégia (a voliteľne per konfigurácia), od najnovšej.

        Vlastnosti aj parametre sú pri každej stratégii iné, takže zliať ich do jedného
        zoznamu by znamenalo porovnávať neporovnateľné. Staršie záznamy bez konfigurácie
        si ju doplnia z behov, na ktoré sa odkazujú.
        """
        if strategy and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        for x in anstore.list(strategy, limit=500):
            konfig = _config_of_runs(x.get("run_ids") or [])
            if any(x.get(k) != v for k, v in konfig.items()):
                anstore.patch(x["id"], **konfig)   # starší záznam alebo kľúč z čias pred defaultmi
        return {"items": anstore.list(strategy, limit=limit, config_key=config_key, market=market)}

    @router.get("/api/analytics/history/{an_id}")
    def analytics_history_one(an_id: str):
        zaznam = anstore.get(an_id)
        if zaznam is None:
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return zaznam

    @router.post("/api/analytics/history")
    def analytics_save(req: AnalyticsSaveRequest):
        """Uloží záver, nie obchody — tie ostávajú v behoch, na ktoré sa záznam odkazuje."""
        strategy = req.report.get("strategy") or "ibs"
        if strategy not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {strategy!r}")
        if not (req.report.get("runs") or []):
            raise HTTPException(422, "report nemá behy, z ktorých vznikol")
        # Tá istá vzorka (behy, obchody, break-even) je jeden záznam: ukladá sa pri každom
        # výpočte automaticky, takže opakované Spočítať nesmie plodiť duplicity - a keď
        # už záznam má posudok, tester ho dostane hneď.
        existujuci = anstore.find_by_numbers(strategy, an_fingerprint(req.report))
        if existujuci is not None:
            # Tie isté čísla, ale report môže mať viac: syntetické behy alebo iné sekcie
            # dobehli až teraz. Uložený záznam sa obnoví, id a posudok ostávajú.
            anstore.refresh_report(existujuci["id"], req.report)
            if req.note.strip() and req.note.strip() != (existujuci.get("note") or ""):
                anstore.patch(existujuci["id"], note=req.note.strip())
            existujuci = anstore.get(existujuci["id"]) or existujuci
            return {**an_summary(existujuci), "reused": True}
        konfig = _config_of_runs([r.get("id") for r in req.report["runs"] if r.get("id")])
        return {**anstore.save(req.report, strategy=strategy, note=req.note.strip(),
                               user=clean_user(req.user) or "", **konfig), "reused": False}

    @router.post("/api/analytics/history/{an_id}/note")
    def analytics_note(an_id: str, req: NoteRequest):
        """Poznámka k uloženej analytike — dopĺňa sa dodatočne, ukladanie je automatické."""
        out = anstore.patch(an_id, note=req.note.strip())
        if out is None:
            raise HTTPException(404, "taká analytika v histórii nie je")
        return out

    @router.get("/api/analytics/history/{an_id}/zadanie")
    def analytics_zadanie(an_id: str):
        """Čísla plus otázky v tvare, ktorý sa dá podať AI."""
        from ..anstore import POSUDOK_OTAZKY, zadanie

        zaznam = anstore.get(an_id)
        if zaznam is None:
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return {"id": an_id, "text": zadanie(zaznam.get("report") or {}),
                "questions": list(POSUDOK_OTAZKY)}

    @router.post("/api/analytics/history/{an_id}/posudok")
    def analytics_posudok(an_id: str, req: PosudokRequest):
        out = anstore.set_posudok(an_id, req.text, clean_user(req.user) or "")
        if out is None:
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return out

    @router.delete("/api/analytics/history/{an_id}")
    def analytics_delete(an_id: str):
        if not anstore.delete(an_id):
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return {"deleted": an_id}

    return router
