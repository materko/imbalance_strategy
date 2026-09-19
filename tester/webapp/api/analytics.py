"""Analytika skupín obchodov a konfigurácie (`/api/analytics`, configs, fill-windows)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES

from ..runner import profile_titles
from ..store import strategy_of
from .common import clean_user, null_note, market_config_key
from .context import AppContext
from .models import RunRequest, FillWindowsRequest
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner
    defaults_of = ctx.defaults_of

    @router.get("/api/analytics")
    def analytics(q: str = "", runs: str = "", strategy: str = "ibs",
                  quantiles: int = Query(4, ge=2, le=10),
                  min_bucket: int = Query(8, ge=2, le=200),
                  limit_runs: int = Query(40, ge=1, le=500),
                  nulltest: bool = True,
                  null_iterations: int = Query(600, ge=50, le=5000),
                  portfolio: bool = True,
                  risk_pct: float = Query(1.0, gt=0, le=10),
                  decay: bool = True,
                  decay_parts: int = Query(4, ge=2, le=12)):
        """Ktorá skupina obchodov kazí výsledok — nad jedným behom alebo nad viacerými.

        `runs` je zoznam id oddelený čiarkou; bez neho sa vezmú behy podľa `q` (tá istá
        syntax ako vyhľadávanie v histórii). Obchody sa zliajú dokopy: jeden beh má rádovo
        desiatky obchodov a to je na rozdelenie na skupiny málo.
        """
        from ... import analytics as an

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        if runs.strip():
            chcene = [r.strip() for r in runs.split(",") if r.strip()]
            zaznamy = [rec for rec in (store.get(i) for i in chcene) if rec]
        else:
            vsetky = store.search(q) if q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:limit_runs]
        if not zaznamy:
            raise HTTPException(404, "žiadne dobehnuté behy s obchodmi")
        # Vlastnosti aj parametre (`FEATURE_PARAMS`) sú vec stratégie: behy inej
        # stratégie by dostali cudzie odkazy „preladiť tento parameter".
        cudzie = sorted({strategy_of(r) for r in zaznamy} - {strategy})
        if cudzie:
            raise HTTPException(422, f"vybrané behy patria stratégii {', '.join(cudzie)}, "
                                     f"nie {strategy} — prepni stratégiu podľa behov")

        # Jeden loader pre všetky zliate obchody: kresby (plán obchodu), stav trhu,
        # kalendár a dedupe prekrývajúcich sa okien (`analytics.trades_of`).
        nacitane = an.trades_of(zaznamy, store.trades, store.chart, strategy=strategy)
        obchody, duplicity = nacitane.trades, nacitane.duplicates
        pouzite = [{"id": rec["id"], "pair": rec["settings"].get("pair"),
                    "timeframe": rec["settings"].get("timeframe"),
                    "timerange": rec["settings"].get("timerange"),
                    "trades": nacitane.per_run[rec["id"]], "profile": rec["settings"].get("profile"),
                    "note": rec.get("note") or ""}
                   for rec in zaznamy if rec["id"] in nacitane.per_run]
        if not obchody:
            raise HTTPException(404, "vybrané behy nemajú uložené obchody")

        report = an.analyze(obchody, strategy=strategy, quantiles=quantiles,
                            min_bucket=min_bucket)
        pary = sorted({r["pair"] for r in pouzite if r["pair"]})
        tfs = sorted({r["timeframe"] for r in pouzite if r["timeframe"]})
        okna = sorted({r["timerange"] for r in pouzite if r["timerange"]})
        report["runs"] = pouzite
        report["pairs"] = pary
        report["timeframes"] = tfs
        report["duplicates"] = duplicity
        # Zliať obchody z rôznych párov ide, ale prahy v bodoch ani vzdialenosti stopu
        # nie sú medzi nimi porovnateľné - nech to je vidieť.
        report["mixed_pairs"] = len(pary) > 1
        # Rôzne TF: dĺžka v baroch a limity `*MaxBars` znamenajú na každom inú vec.
        report["mixed_timeframes"] = len(tfs) > 1
        # Z akej konfiguracie tie obchody su. Zliat behy tej istej konfiguracie na roznych
        # oknach je v poriadku; zliat rozne konfiguracie znamena miesat rozne strategie.
        report["config"] = an.config_spread(zaznamy)
        report["strategy"] = strategy

        # Charakter sa meria z tych istych obchodov: aky typ strategie to je, sa neda
        # oddelit od toho, ktora skupina obchodov kazi vysledok - jedno vysvetluje druhe.
        # Pohyb pred vstupom sa da zmerat len na jednom pare (sviecky su parove).
        from ... import character as chr_mod

        prvy = pouzite[0]
        report["character"] = chr_mod.measure(
            obchody, pair="" if len(pary) > 1 else (prvy["pair"] or ""),
            timeframe="" if len(tfs) > 1 else (prvy["timeframe"] or "3m")).to_dict()
        report["archetypes"] = [a.__dict__ for a in chr_mod.ARCHETYPES]

        # Test proti nahode ide z tej istej vzorky obchodov: "break-even 0,064 %" je bez
        # referencie cislo, nie odpoved. Nahodne vstupy sa losuju zo sviecok, takze to ide
        # len na jednom trhu - pri zliatych paroch by sa nemalo z coho losovat.
        # Portfolio: tie iste behy ako jeden ucet. Clen je JEDEN beh - behy toho isteho
        # trhu v tom istom case su alternativy, nie clenovia, a modul to nahlasi.
        report["portfolio"] = None
        if portfolio and len(zaznamy) > 1:
            from ... import portfolio as pf_mod

            per: dict[str, list[dict[str, Any]]] = {}
            for rec in zaznamy:
                t = store.trades(rec["id"])
                if not t:
                    continue
                nast = rec["settings"]
                meno = f"{nast.get('pair')} {nast.get('timeframe')} {nast.get('timerange')}"
                per[meno] = an.enrich([dict(x) for x in t], store.chart(rec["id"]), strategy)
            if len(per) > 1:
                report["portfolio"] = pf_mod.analyze(per, records=zaznamy, risk_pct=risk_pct)

        # Slabne edge? Posledne obdobie proti tomu, co strategia robievala. Ide to aj
        # pri zliatych paroch: break-even je pomer zisku k objemu, takze sa da scitat.
        report["decay"] = None
        if decay:
            from ... import decay as dc_mod

            try:
                report["decay"] = dc_mod.analyze(obchody, parts=decay_parts).to_dict()
            except ValueError:
                report["decay"] = None

        # Syntetický trh: to isté zadanie na trhu bez štruktúry. Nič sa nespúšťa —
        # hľadajú sa behy, ktoré v histórii už sú.
        from ... import synthetic as syn_mod

        try:
            report["synthetic"] = syn_mod.assess(zaznamy, store, strategy=strategy)
        except (ValueError, KeyError):
            report["synthetic"] = None

        report["nulltest"] = None
        if nulltest and not report["mixed_pairs"] and not report["mixed_timeframes"]:
            from ... import nulltest as nt_mod

            vysledky = {}
            for null in nt_mod.NULLS:
                try:
                    # Z okien behov, nie z celej histórie páru - náhoda dedí drift trhu
                    # a ten má byť z toho istého obdobia ako obchody.
                    vysledky[null] = nt_mod.compare(
                        obchody, pair=pary[0], timeframe=prvy["timeframe"] or "3m",
                        timerange=okna or None,
                        iterations=null_iterations, null=null).to_dict()
                except (ValueError, FileNotFoundError):
                    vysledky = {}
                    break
            if vysledky:
                report["nulltest"] = {"nulls": vysledky,
                                      "note": null_note(vysledky)}

        # Po trhoch: to isté nastavenie, riadok trh, stĺpce referenčné okná, v bunke
        # break-even mínus poplatok TOHO trhu. Odpoveď na „drží myšlienka aj inde?"
        # z hotových behov - to, čo matica, len bez spúšťania.
        from ... import hyperopt as ho

        po_trhoch: dict[str, dict[str, Any]] = {}
        for rec in zaznamy:
            s = rec.get("settings") or {}
            kluc = f"{s.get('pair') or '?'}|{s.get('timeframe') or '?'}"
            trh = po_trhoch.setdefault(kluc, {"key": kluc, "pair": s.get("pair"),
                                              "timeframe": s.get("timeframe"), "windows": {},
                                              "trades": 0})
            okno = s.get("timerange")
            v = rec.get("result") or {}
            kandidat = {"run_id": rec["id"], "trades": int(v.get("trades") or 0),
                        "edge": ho.edge_of(rec), "pnl_pct": v.get("pnl_pct")}
            if okno and (okno not in trh["windows"] or kandidat["trades"] > trh["windows"][okno]["trades"]):
                trh["windows"][okno] = kandidat
            trh["trades"] += kandidat["trades"]
        for trh in po_trhoch.values():
            trh["positive"] = sum(1 for w in ho.REFERENCE_WINDOWS
                                  if w in trh["windows"] and (trh["windows"][w]["edge"] or 0) > 0)
            trh["done_ref"] = sum(1 for w in ho.REFERENCE_WINDOWS if w in trh["windows"])
        report["by_market"] = sorted(po_trhoch.values(), key=lambda t: (-t["positive"], t["pair"] or ""))
        report["reference_windows"] = list(ho.REFERENCE_WINDOWS)
        return report

    def _config_groups(strategy: str) -> list[dict[str, Any]]:
        """Skupiny hotových behov s obchodmi podľa konfigurácie — s oknami, pármi
        a s tým, ktoré referenčné okná ešte chýbajú."""
        from ... import hyperopt as ho

        skupiny: dict[str, dict[str, Any]] = {}
        for rec in store.all():
            obchodov = int((rec.get("result") or {}).get("trades") or 0)
            if strategy_of(rec) != strategy or rec.get("status") != "done" or obchodov <= 0:
                continue
            s = rec.get("settings") or {}
            # Body mriežky a susedia z testu plató nie sú nastavenie, ktoré by niekto
            # zvolil - sú to skúšky, kde má parameter ležať, každý na jednom okne. Analytika
            # je o jednom pevnom nastavení; tie sa v ponuke len pletú. Matica (to isté
            # nastavenie na inom trhu), doplnené okná a overenie hyperoptu ostávajú.
            if s.get("sweep") or s.get("plateau"):
                continue
            kluc = market_config_key(rec)
            g = skupiny.setdefault(kluc, {
                "key": kluc, "profile": "", "run_ids": [], "pairs": set(),
                "timeframes": set(), "timeranges": set(), "trades": 0, "latest": "",
                "first": rec["id"], "note": ""})
            g["profile"] = g["profile"] or s.get("profile") or ""
            # Poznámka najstaršieho behu: pri ručne ladených behoch je to jediný text,
            # ktorý hovorí, čo sa tým skúšalo.
            if rec["id"] <= g["first"]:
                g["first"], g["note"] = rec["id"], str(rec.get("note") or "")
            g["run_ids"].append(rec["id"])
            g["pairs"].add(s.get("pair") or "?")
            g["timeframes"].add(s.get("timeframe") or "?")
            if s.get("timerange"):
                g["timeranges"].add(s["timerange"])
            g["trades"] += obchodov
            g["latest"] = max(g["latest"], rec["id"])
        out = [{**g, "profile": g["profile"] or "(Pine defaulty)",
                "runs": len(g["run_ids"]), "run_ids": sorted(g["run_ids"]),
                "sample": max(g["run_ids"]),
                "pairs": sorted(g["pairs"]), "timeframes": sorted(g["timeframes"]),
                "timeranges": sorted(g["timeranges"]),
                # Referenčné okná, ktoré konfigurácia ešte nemá - to sa dá doplniť.
                "missing": [w for w in ho.REFERENCE_WINDOWS if w not in g["timeranges"]]}
               for g in skupiny.values()]
        # Najviac behov hore (to je tá, na ktorej sa meralo), pri zhode novšia.
        out.sort(key=lambda g: g["latest"], reverse=True)
        out.sort(key=lambda g: g["runs"], reverse=True)
        return out

    def _windows_of(run_ids: list[str]) -> dict[str, dict[str, Any]]:
        """`okno -> {run_id, trades, edge, pnl_pct}` — pri viacerých behoch v jednom okne
        ten s najviac obchodmi (ako v `paper`), edge je break-even mínus poplatok behu."""
        from ... import hyperopt as ho

        out: dict[str, dict[str, Any]] = {}
        for run_id in run_ids:
            rec = store.get(run_id)
            if not rec:
                continue
            okno = (rec.get("settings") or {}).get("timerange")
            v = rec.get("result") or {}
            if not okno:
                continue
            kandidat = {"run_id": run_id, "trades": int(v.get("trades") or 0),
                        "edge": ho.edge_of(rec), "pnl_pct": v.get("pnl_pct")}
            if okno not in out or kandidat["trades"] > out[okno]["trades"]:
                out[okno] = kandidat
        return out

    def _settings_tree(strategy: str) -> list[dict[str, Any]]:
        """Nastavenia (profil + parametre) → trhy (pár + TF) → výsledky po oknách.

        Dve úrovne preto, že tá istá otázka má dva smery: „drží toto nastavenie aj na
        iných trhoch?" (nastavenie → všetky trhy) a „ktoré nastavenie na tomto trhu
        drží po oknách?" (trh → nastavenia). Jedna plochá ponuka nevie ani jedno.
        """
        from ... import hyperopt as ho

        ref = list(ho.REFERENCE_WINDOWS)
        tituly = profile_titles(strategy)
        nastavenia: dict[str, dict[str, Any]] = {}
        for trh in _config_groups(strategy):
            kluc_nast = trh["key"].split("|", 1)[0]
            pair, tf = trh["pairs"][0], trh["timeframes"][0]
            okna = _windows_of(trh["run_ids"])
            kladne = sum(1 for w in ref if w in okna and (okna[w]["edge"] or 0) > 0)
            # Popis nastavenia: `_title` profilu, keď ho má; inak meno súboru bez cesty.
            meno = str(trh["profile"]).replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".json")
            n = nastavenia.setdefault(kluc_nast, {
                "key": kluc_nast, "profile": trh["profile"], "runs": 0, "trades": 0,
                "title": "" if tituly.get(meno, meno) == meno else tituly[meno],
                "pairs": set(), "timeframes": set(), "timeranges": set(),
                # `first` = najstarší beh: kedy nastavenie vzniklo, podľa toho sa volá aj radí.
                "first": trh["first"], "note": trh["note"], "latest": "",
                "markets": []})
            n["runs"] += trh["runs"]
            n["trades"] += trh["trades"]
            n["pairs"].add(pair)
            n["timeframes"].add(tf)
            n["timeranges"].update(trh["timeranges"])
            if trh["first"] < n["first"]:
                n["first"], n["note"] = trh["first"], trh["note"]
            n["latest"] = max(n["latest"], trh["latest"])
            # Kľúč trhu je `pár|TF` bez parametrov - nastavenie je už rodič, a prehľad
            # nastavení na trhu porovnáva práve cez tento kľúč naprieč nastaveniami.
            n["markets"].append({
                "key": f"{pair}|{tf}", "pair": pair, "timeframe": tf, "run_ids": trh["run_ids"],
                "sample": trh["sample"], "runs": trh["runs"], "trades": trh["trades"],
                "timeranges": trh["timeranges"], "missing": trh["missing"],
                "windows": okna, "positive": kladne,
                "done_ref": sum(1 for w in ref if w in okna),
            })
        out = []
        for n in nastavenia.values():
            n["markets"].sort(key=lambda m: (-m["runs"], m["pair"], m["timeframe"]))
            out.append({**n, "pairs": sorted(n["pairs"]), "timeframes": sorted(n["timeframes"]),
                        "timeranges": sorted(n["timeranges"]), "variant": {}})
        # Ten istý profil s inými `--set` hodnotami: názov by bol rovnaký, tak sa k nemu
        # dopíšu parametre, v ktorých sa také nastavenia medzi sebou líšia.
        podla_profilu: dict[str, list[dict[str, Any]]] = {}
        for n in out:
            podla_profilu.setdefault(n["profile"], []).append(n)
        for skupina in podla_profilu.values():
            if len(skupina) < 2:
                continue
            # Parametre doplnené Pine defaultmi: beh bez kľúča a beh s jeho defaultom sú
            # to isté nastavenie, nie rozdiel „alertOnState2=null vs false".
            parametre = {}
            for n in skupina:
                rec = store.get(n["markets"][0]["sample"]) or {}
                parametre[n["key"]] = {**defaults_of(rec), **(rec.get("params") or {})}
            kluce = {k for p in parametre.values() for k in p}
            hodnoty = {k: [json.dumps(p.get(k), sort_keys=True, default=str) for p in parametre.values()]
                       for k in kluce}
            # Parametre, v ktorých sa skupina líši, od najrozmanitejšieho (v mriežke je to ten
            # prechádzaný, nie zapnutý filter spoločný všetkým bodom).
            rozne = sorted((k for k in kluce if len(set(hodnoty[k])) > 1),
                           key=lambda k: (-len(set(hodnoty[k])), k))
            # Do názvu ide, čím sa nastavenie líši od najbežnejšej hodnoty skupiny - to, čo
            # majú všetky ostatné rovnako, nastavenie nerozlíši.
            bezne = {k: max(set(hodnoty[k]), key=hodnoty[k].count) for k in rozne}
            dump = lambda v: json.dumps(v, sort_keys=True, default=str)  # noqa: E731
            for n in skupina:
                moje = parametre[n["key"]]
                odchylky = [k for k in rozne if dump(moje.get(k)) != bezne[k]]
                n["variant"] = {k: moje.get(k) for k in (odchylky or rozne)[:4]}
            # Kým majú dve nastavenia rovnaký názov, pridá sa im parameter, v ktorom sa od
            # seba líšia - inak by tester v ponuke nevedel, ktoré je ktoré.
            for _ in range(4):
                rovnake: dict[str, list[dict[str, Any]]] = {}
                for n in skupina:
                    rovnake.setdefault(dump(n["variant"]), []).append(n)
                kolizie = [g for g in rovnake.values() if len(g) > 1]
                if not kolizie:
                    break
                for g in kolizie:
                    dalsi = next((k for k in rozne if k not in g[0]["variant"]
                                  and len({dump(parametre[n["key"]].get(k)) for n in g}) > 1), None)
                    if dalsi is None:
                        continue
                    for n in g:
                        n["variant"][dalsi] = parametre[n["key"]].get(dalsi)
        # Najnovšie vzniknuté nastavenie hore - ponuka sa volá dátumom vzniku, tak nech
        # je aj v tom poradí (ako história).
        out.sort(key=lambda n: n["first"], reverse=True)
        return out

    @router.get("/api/analytics/configs")
    def analytics_configs(strategy: str = "ibs", limit: int = Query(0, ge=0, le=5000)):
        """Nastavenia v histórii (profil + parametre) a pod nimi trhy s výsledkami po
        referenčných oknách — z hotových behov, nič sa nespúšťa.

        Analytika má zmysel len nad jedným nastavením (zliať rôzne znamená zliať rôzne
        stratégie), a textový dopyt to nestráži. Tu si tester vyberie nastavenie a trh
        (alebo všetky trhy) a hneď vidí, koľko okien pokrýva a koľko referenčných chýba.
        """
        from ... import hyperopt as ho

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        # Bez `limit` všetky: ponuka je zoradená podľa dátumu, takže by strop odrezal
        # práve staršie, pomenované profily a nechal len čerstvé body mriežky.
        nastavenia = _settings_tree(strategy)
        return {"settings": nastavenia[:limit] if limit else nastavenia,
                "reference_windows": list(ho.REFERENCE_WINDOWS)}

    @router.post("/api/analytics/fill-windows")
    def analytics_fill_windows(req: FillWindowsRequest):
        """Zaradí behy pre referenčné okná, ktoré konfigurácii vzorového behu chýbajú.

        Málo behov = málo obchodov a každý test batérie povie „málo dát". Odpoveď nie
        je zmeniť prahy, ale dobehnúť tie isté parametre na ostatných oknách — presne
        to, čo robí `cli checkup`, len z webapp a bez nového backtestu tam, kde už je.
        """
        from ... import hyperopt as ho

        vzor = store.get(req.run_id)
        if vzor is None:
            raise HTTPException(404, "vzorový beh v histórii nie je")
        strategy = strategy_of(vzor)
        skupina = next((g for g in _config_groups(strategy) if g["key"] == market_config_key(vzor)), None)
        chybaju = skupina["missing"] if skupina else list(ho.REFERENCE_WINDOWS)
        if not chybaju:
            return {"queued": [], "windows": [], "note": "konfigurácia má všetkých päť referenčných okien"}

        s = vzor.get("settings") or {}
        ids = []
        for okno in chybaju:
            r = RunRequest(params=vzor.get("params") or {}, pair=s.get("pair") or "BTC/USDT:USDT",
                           strategy=strategy, timeframe=s.get("timeframe") or "3m", timerange=okno,
                           fee=s.get("fee"), wallet=s.get("wallet") or 10000,
                           timeframe_detail=s.get("timeframe_detail", "1m"), engine=s.get("engine"),
                           exchange=s.get("exchange"), profile=s.get("profile"), ai=s.get("ai"),
                           note=f"doplnenie okna {okno} pre analytiku (podľa {vzor['id']})",
                           user=req.user)
            settings = {**run_settings(r), "checkup": {"fill": vzor["id"], "strategy": strategy}}
            try:
                job = runner.submit(r.params, settings, note=r.note, user=clean_user(req.user))
            except (ConfigError, ValueError) as exc:
                raise HTTPException(422, f"okno {okno}: {exc}")
            ids.append(job.id)
        return {"queued": ids, "windows": chybaju,
                "note": f"zaradených {len(ids)} behov; po dobehnutí spusti Spočítať znova"}

    return router
