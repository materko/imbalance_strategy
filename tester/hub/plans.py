"""Plány výpočtov: zadávateľ voliteľne povie, koľko výpočtov ide dať — časť `HubState`.

Hub vidí len to, čo už dostal; hľadanie, ktoré posiela výpočty postupne (CLI `--remote`,
AI), by inak nevedelo povedať, kedy skončí. Kto ide dať veľa, pripíše pri zadaní výpočtu
`plan_total` (koľko spolu, aj tie, čo ešte nezadal) a voliteľne `plan_done` (koľko už má
hotových, aj mimo hubu) — CLI `--plan-total`, `--plan-done`, formulár „na hube". Žiadne
extra rozhranie ani meno: plán patrí zadávateľovi (jeden na meno) a hub doň započíta každý
ďalší jeho výpočet; hotových je väčšie z nahláseného a napočítaného. Kto dáva pár behov,
nepíše nič a plán nemá. Zvyšok a odhad sú z rýchlosti plánu za poslednú hodinu (inak hubu).

Hotový plán sa zahodí po `PLAN_KEEP_FINISHED`, zabudnutý (bez zmeny) po `PLAN_KEEP_IDLE`;
nové `plan_total` po hotovom pláne začne nový.
"""

from __future__ import annotations

from typing import Any

from .events import _iso

#: Hotový plán (všetko spočítané) ostáva viditeľný ešte takto dlho.
PLAN_KEEP_FINISHED = 2 * 86400
#: Plán bez zmeny (nič nové, nikto ho neobnovil) sa zahodí po tomto čase.
PLAN_KEEP_IDLE = 14 * 86400
#: Okno pre rýchlosť plánu (rovnaké ako pre celý hub, `stats.RATE_SECONDS`).
PLAN_RATE_SECONDS = 3600


class PlansMixin:
    """Plány zadávateľov (`self.plans`: meno zadávateľa -> plán, ide do `state.json`)."""

    plans: dict[str, dict[str, Any]]

    def _set_plan(self, submitter: str, kind: str, total: int | None, done: int | None) -> None:
        """Z polí zadania: nastaví alebo obnoví plán zadávateľa (volá sa pod zámkom)."""
        for meno, v in (("plan_total", total), ("plan_done", done)):
            if v is not None and int(v) < 0:
                raise ValueError(f"{meno} nesmie byť záporné")
        now = self.clock()
        plan = self.plans.get(submitter)
        if plan is None or (total is not None and self._plan_left(plan) == 0):
            plan = self.plans[submitter] = {
                "submitter": submitter, "kind": kind, "total": None, "done_reported": None,
                "created": _iso(now), "submitted": 0, "done": 0, "failed": 0, "recent": [],
            }
        if total is not None:
            plan["total"] = int(total)
        if done is not None:
            plan["done_reported"] = int(done)
        plan["kind"] = kind
        plan["updated"] = now
        self.log("plan_set", submitter=submitter, total=plan["total"], done=plan["done_reported"])

    def list_plans(self) -> list[dict[str, Any]]:
        with self._lock:
            self._prune_plans()
            return [self._plan_public(p) for p in self.plans.values()]

    # -- počítadlá z výpočtov ------------------------------------------------ #

    def _plan_submitted(self, job: dict[str, Any]) -> None:
        """Výpočet zadávateľa, ktorý má plán, doň patrí (`job.plan`)."""
        plan = self.plans.get(job.get("submitter") or "")
        if plan is None:
            return
        job["plan"] = True
        plan["submitted"] = int(plan.get("submitted", 0)) + 1
        plan["updated"] = self.clock()

    def _plan_finished(self, job: dict[str, Any], status: str) -> None:
        plan = self.plans.get(job.get("submitter") or "") if job.get("plan") else None
        if plan is None or job.get("plan_counted") in (status, "done"):
            return
        if job.get("plan_counted") == "failed":
            plan["failed"] = max(0, int(plan.get("failed", 0)) - 1)  # neskorý hotový prepíše zlyhanie
        now = self.clock()
        if status == "done":
            plan["done"] = int(plan.get("done", 0)) + 1
            plan["recent"] = [t for t in plan.get("recent") or [] if t >= now - PLAN_RATE_SECONDS] + [now]
        else:
            plan["failed"] = int(plan.get("failed", 0)) + 1
        plan["updated"] = now
        job["plan_counted"] = status

    def _prune_plans(self) -> None:
        now = self.clock()
        for k, plan in list(self.plans.items()):
            vek = now - float(plan.get("updated") or 0)
            if vek > PLAN_KEEP_IDLE or (self._plan_left(plan) == 0 and vek > PLAN_KEEP_FINISHED):
                del self.plans[k]

    # -- verejný pohľad ------------------------------------------------------ #

    def _plan_done(self, plan: dict[str, Any]) -> int:
        return max(int(plan.get("done", 0)), int(plan.get("done_reported") or 0))

    def _plan_left(self, plan: dict[str, Any]) -> int | None:
        if plan.get("total") is None:
            return None
        return max(0, int(plan["total"]) - self._plan_done(plan))

    def _plan_public(self, plan: dict[str, Any]) -> dict[str, Any]:
        from . import protocol as P

        now = self.clock()
        zive = sum(1 for j in self.jobs.values()
                   if j["status"] in P.LIVE_STATES and j.get("plan") and j.get("submitter") == plan["submitter"])
        vlastne = sum(1 for t in plan.get("recent") or [] if t >= now - PLAN_RATE_SECONDS)
        za_hodinu = vlastne * 3600 / PLAN_RATE_SECONDS
        zdroj = "plan"
        if not za_hodinu:
            za_hodinu, zdroj = self._queue_eta(0)["per_hour"], "hub"
        left = self._plan_left(plan)
        eta = 0.0 if left == 0 else (left * 3600 / za_hodinu if left and za_hodinu else None)
        return {
            "submitter": plan["submitter"], "kind": plan.get("kind"), "total": plan.get("total"),
            "done": self._plan_done(plan), "done_reported": plan.get("done_reported"),
            "done_hub": int(plan.get("done", 0)), "failed": int(plan.get("failed", 0)),
            "submitted": int(plan.get("submitted", 0)), "live": zive, "left": left,
            "per_hour": za_hodinu, "rate_from": zdroj, "eta_seconds": eta,
            "created": plan.get("created"), "updated": _iso(float(plan.get("updated") or now)),
        }
