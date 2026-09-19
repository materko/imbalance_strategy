"""AI vrstva, prop výzva a meranie do `docs/merania` (`/api/ai`, `/api/prop`, `/api/paper`)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tradebot.strategies import STRATEGIES, get_spec

from ..runner import REPO
from ..store import strategy_of
from .context import AppContext
from .models import PropRequest, PaperRequest


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store

    @router.get("/api/ai/meta")
    def ai_meta(strategy: str = "ibs"):
        """Predvolené hodnoty AI vrstvy a to, čo daná stratégia dovolí meniť."""
        from tradebot.strategies.hyperopt import StrategyHyperopt

        from ... import engines as eng

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        povolene = (get_spec(strategy).hyperopt_cls or StrategyHyperopt).ai_adjustable()
        return {"defaults": dict(eng.AI_DEFAULTS),
                "adjustable": [{"key": k, "param": v[0], "title": v[1]}
                               for k, v in povolene.items()]}

    @router.get("/api/prop/meta")
    def prop_meta():
        """Predlohy pravidiel pre formulár — vrátane toho, odkiaľ sú čísla."""
        from ... import prop as pr

        return {"presets": {k: {**v.__dict__, "targets": list(v.targets),
                                "phases": v.phases}
                            for k, v in pr.PRESETS.items()},
                "risks": list(pr.RISKS),
                "trailing": {"nie": "statický (z počiatočného zostatku)",
                             "vrchol": "trailing z vrcholu (intraday)",
                             "koniec_dna": "trailing z konca dňa (EOD)"}}

    @router.post("/api/prop")
    def prop_run(req: PropRequest):
        """Prehrá obchody vybraných behov cez pravidlá výzvy, riziko po riziku.

        `rules` je jedna predloha alebo zoznam — tie isté obchody sa prehrajú cez každú
        a odpoveď nesie `variants` vedľa seba, nech je vidieť, ktorá firma to unesie.
        """
        from ... import analytics as an, prop as pr

        if req.strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {req.strategy!r}")
        zmeny = {k: v for k, v in req.model_dump().items()
                 if v is not None and k in pr.Rules.__dataclass_fields__ and k != "name"}
        if req.targets:
            zmeny["targets"] = tuple(req.targets)
        # Viac predlôh naraz: tie isté obchody, pravidlá rôznych firiem vedľa seba.
        # Prepisy z polí platia na `custom` a na jedinú vybranú predlohu.
        kluce = req.rules if isinstance(req.rules, list) else [req.rules]
        try:
            predlohy = pr.rules_for(kluce, zmeny)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        if req.runs:
            zaznamy = [rec for rec in (store.get(i) for i in req.runs) if rec]
        else:
            vsetky = store.search(req.q) if req.q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == req.strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:req.limit]
        if not zaznamy:
            raise HTTPException(404, "žiadne dobehnuté behy s obchodmi")

        nacitane = an.trades_of(zaznamy, store.trades, store.chart, strategy=req.strategy,
                                with_market=False)
        obchody, duplicity = nacitane.trades, nacitane.duplicates
        if not obchody:
            raise HTTPException(404, "vybrané behy nemajú uložené obchody")

        rizika = req.risks or list(pr.RISKS)
        varianty = []
        for kluc, pravidla in predlohy:
            vysledky = pr.risk_table(obchody, pravidla, risks=rizika, step=req.step)
            najlepsi = max(vysledky, key=lambda r: (r.ev if r.ev is not None else -1e18))
            varianty.append({
                "key": kluc,
                "rules": {**pravidla.__dict__, "targets": list(pravidla.targets),
                          "phases": pravidla.phases},
                "results": [r.to_dict() for r in vysledky],
                "best_risk": najlepsi.risk_pct, "verdict": najlepsi.verdict,
            })
        prvy = varianty[0]
        return {"trades": len(obchody), "runs": len(zaznamy), "duplicates": duplicity,
                # Odkial su obchody: prop vyzva sa nepocita z ziadnej vlastnej
                # konfiguracie, ale z obchodov vybranych behov.
                "config": an.config_spread(zaznamy),
                "pairs": sorted({r["settings"].get("pair") for r in zaznamy
                                 if r["settings"].get("pair")}),
                "run_ids": [r["id"] for r in zaznamy],
                "variants": varianty,
                # Prvý variant aj na vrchu - tvar, na ktorý sú zvyknuté staršie skripty.
                **{k: prvy[k] for k in ("rules", "results", "best_risk", "verdict")}}

    @router.post("/api/paper")
    def paper_write(req: PaperRequest):
        """Zapíše meranie do `docs/merania/` zo všetkého, čo o tých behoch vieme.

        Nové backtesty nespúšťa — píše sa len to, čo v histórii už je. Na čo behy
        nestačia, dokument povie nahlas aj s príkazom, ktorým sa to doplní.
        """
        from ... import paper as pp

        if req.strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {req.strategy!r}")
        if req.runs:
            zaznamy = [rec for rec in (store.get(i) for i in req.runs) if rec]
        else:
            vsetky = store.search(req.q) if req.q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == req.strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:req.limit]

        prikaz = ("python -m tester.webapp.cli paper --runs "
                  + ",".join(r["id"] for r in zaznamy))
        try:
            doc = pp.build(zaznamy, store, strategy=req.strategy, title=req.title,
                           risk_pct=req.risk_pct, null_iterations=req.iterations,
                           command=prikaz)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        cesta = pp.write(doc, req.name)
        return {"path": str(cesta.relative_to(REPO) if cesta.is_relative_to(REPO) else cesta),
                "runs": len(zaznamy),
                "sections": [{"title": x.title, "verdict": x.verdict, "gap": x.gap}
                             for x in doc.sections]}

    return router
