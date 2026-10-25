"""Hyperopt vo fronte webapp — výsledkom nie sú obchody, ale epochy a overovacie behy.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from tradebot.core.paths import REPO, FREQTRADE_USER_DIR as USER_DIR
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import get_spec

from .. import engines


class HyperoptJobMixin:
    """Hyperopt ako druh behu vo fronte `BacktestRunner`: epochy, potom overenie víťaza."""

    def _run_hyperopt(self, job: Job, instrument: str, profile: Path, t0: float) -> None:
        """Hyperopt: epochy do zaznamu behu, vitaz na referencne okna do fronty.

        Zaznam tohto behu nie je backtest - nema obchody ani krivku kapitalu. Nesie
        zadanie, epochy a vitaza, a odkazuje na overovacie behy, ktore su uz obycajne
        behy v historii. Delenie je zamerne: hyperopt najde optimum PRAVE ladeneho okna
        a jedine, cim sa to da preverit, su behy na inych oknach.

        Nadstavba nad Freqtrade (`settings.hyperopt`): `sampler` (cez `HyperOpt.generate_estimator`),
        `windows` + `aggregate` (jeden beh cez rozpatie okien, loss ich hodnoti zvlast), `objectives`
        (Pareto z metrik epoch), `select="plateau"` (okolie kandidatov ako backtesty), `mode="walkforward"`
        (hyperopt na okne N, backtest na N+1) a `continue_from` (zlucenie epoch - novy beh s inym seedom,
        Freqtrade stare epochy do hladania vlozit nevie).
        """
        from .. import hyperopt as ho

        settings = job.settings
        zadanie = settings["hyperopt"]
        plan = ho.build_plan(zadanie["knobs"], strategy=settings.get("strategy") or "ibs",
                             goal=zadanie.get("goal") or "break_even",
                             max_dd=zadanie.get("max_dd"), min_trades=zadanie.get("min_trades"),
                             note=job.note)
        # Na emulatore MultiCharts nebezi Freqtrade vobec - epochy pocita C# (tester.native_hyperopt)
        if settings.get("engine") == engines.MULTICHARTS:
            self._run_native_hyperopt(job, instrument, profile, t0, plan)
            return
        from dataclasses import replace

        okna = list(zadanie.get("windows") or [])
        plan = replace(plan, sampler=zadanie.get("sampler") or None,
                       windows=tuple(okna) if len(okna) > 1 else (), aggregate=zadanie.get("aggregate") or "min")
        if zadanie.get("mode") == "walkforward":
            self._ft_walk_forward(job, instrument, profile, t0, plan)
            return
        spolu = int(zadanie.get("epochs") or ho.DEFAULT_EPOCHS)
        seed = zadanie.get("seed")
        predosle = []
        if zadanie.get("continue_from"):
            predosle = ho.epochs_from_dicts(self.store.extra(zadanie["continue_from"], "epochs.json")
                                            or zadanie.get("warm") or [])
            if seed is None:
                seed = int(time.time()) % 1_000_000     # iný seed, inak by Freqtrade prešiel tie isté body znova
            job.log_lines.append(f"pokracovanie {zadanie['continue_from']}: {len(predosle)} epoch sa zluci s novymi "
                                 f"(seed {seed}); Freqtrade stare epochy do hladania nevlozi - nove hladanie z nich neucí")
        tr = ho.span(okna) if len(okna) > 1 else settings["timerange"]
        epochs, results, chyba = self._ft_hyperopt(job, plan, profile, instrument, tr, spolu, seed, spolu)
        duration = round(time.time() - t0, 1)
        if chyba is not None:
            job.status = "failed"
            job.error = chyba
            job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._persist(job, None, duration)
            return

        if predosle:
            epochs = ([replace(e, number=i + 1, is_best=False) for i, e in enumerate(predosle)]
                      + [replace(e, number=len(predosle) + i + 1, is_best=False) for i, e in enumerate(epochs)])
        pareto = None
        if zadanie.get("objectives"):
            epochs = ho.pareto_front(epochs, zadanie["objectives"])
            pareto = sorted(e.number for e in epochs if e.pareto)
        vitaz = ho.best(epochs)
        plateau_info = None
        if vitaz is not None and zadanie.get("select") == "plateau":
            vitaz, plateau_info = self._ft_plateau_select(job, instrument, plan, epochs, okna or [settings["timerange"]])
        if vitaz is not None:
            epochs = [replace(e, is_best=e.number == vitaz.number) for e in epochs]
            vitaz = next(e for e in epochs if e.is_best)
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        duration = round(time.time() - t0, 1)
        if job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            return
        job.status = "done"
        zadanie = {k: v for k, v in zadanie.items() if k != "warm"}
        job.settings = {**settings, "hyperopt": {
            **zadanie,
            "epochs_done": len(epochs),
            "best": vitaz.to_dict() if vitaz else None,
            "overrides": ho.overrides(plan, vitaz.params) if vitaz else None,
            "results_file": results.name if results else None,
            "windows": okna if len(okna) > 1 else None,
            "pareto": pareto or None,
            "plateau_select": plateau_info,
            "merged": len(predosle) or None,
        }}
        self._persist(job, None, duration)
        # Zaznam behu drzi vsetky epochy zvlast - do zoznamu historie by nesadli.
        self.store.save_extra(job.id, "epochs.json", [e.to_dict() for e in epochs])

        if vitaz is None or not zadanie.get("verify", True):
            return
        self._verify_winner(job, plan, vitaz)

    def _ft_hyperopt(self, job: Job, plan, profile: Path, instrument: str, timerange: str, epochs: int,
                     seed, total: int, done_before: int = 0, label: str = ""):
        """Jeden `freqtrade hyperopt` (podproces) s priebehom vo fronte; `(epochy, súbor výsledkov, chyba | None)`."""
        from .. import hyperopt as ho

        settings = job.settings
        zadanie = settings["hyperopt"]
        plan_file = ho.plan_path(job.id + label, plan)
        inst = INSTRUMENTS[instrument]
        cmd = ho.command(
            self.python, plan=plan_file,
            config=engines.stake_config(inst, settings.get("exchange")),
            userdir=USER_DIR, datadir=engines.data_dir(inst, settings.get("exchange")),
            strategy_class=get_spec(settings.get("strategy") or "ibs").freqtrade_class,
            pair=settings["pair"], timerange=timerange,
            timeframe=settings.get("timeframe") or "3m",
            epochs=int(epochs),
            detail=settings.get("timeframe_detail"), wallet=settings.get("wallet", 10000),
            fee=settings.get("fee"), seed=seed, jobs=zadanie.get("jobs"),
        )
        job.log_lines.append("$ " + " ".join(cmd))

        env = dict(os.environ, TRADEBOT_PROFILE=str(profile),
                   TRADEBOT_HYPEROPT_PLAN=str(plan_file),
                   PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        start = time.time()
        job.proc = subprocess.Popen(
            cmd, cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        assert job.proc.stdout is not None
        # Priebeh: epochy sa počítajú v súbore výsledkov (riadok = epocha), nie z logu -
        # Freqtrade do rúry vypisuje len epochy, ktoré sú nové najlepšie.
        job.progress = ho.eta(done_before, total, start, None, 0, time.time())
        proc = job.proc

        # Vo vlákne, nie v slučke nad výstupom: Freqtrade do rúry vypíše riadok len pri
        # novej najlepšej epoche, takže neskôr v behu by sa odhad celé minúty nepohol.
        def _sleduj() -> None:
            prva_kedy, prva_pocet, posledna_kedy, predtym = None, 0, None, 0
            while proc.poll() is None:
                teraz = time.time()
                hotovo = ho.count_epochs(ho.latest_results(start))
                if hotovo and prva_kedy is None:
                    prva_kedy, prva_pocet = teraz, hotovo
                if hotovo != predtym:
                    posledna_kedy, predtym = teraz, hotovo
                job.progress = ho.eta(done_before + hotovo, total, start, prva_kedy,
                                      done_before + prva_pocet, teraz, posledna_kedy)
                time.sleep(5)

        threading.Thread(target=_sleduj, daemon=True, name=f"eta-{job.id}{label}").start()
        with job.proc.stdout:  # rúra sa zatvorí hneď — Job (a jeho Popen) ostáva v pamäti
            for line in job.proc.stdout:
                job.log_lines.append(line.rstrip("\n"))
                if len(job.log_lines) > 5000:
                    del job.log_lines[:1000]
        rc = job.proc.wait()
        if job.cancel_requested:
            return [], None, "zrušené používateľom"
        if ho.blocked_by_other(job.log_lines):
            return [], None, ("Freqtrade nepustí dva hyperopty naraz a iný práve beží (aj z iného "
                              "okna alebo klonu). Tento nezačal — pusti ho znova, keď ten dobehne.")
        if rc != 0:
            return [], None, f"freqtrade hyperopt skončil s kódom {rc}"
        results = ho.latest_results(start)
        return (ho.read_results(results) if results else []), results, None

    def _ft_points(self, job: Job, instrument: str, plan, points: list[dict], windows: list[str]) -> list[dict]:
        """Body (parametre epochy `hp_*`) × okná ako Freqtrade backtesty naraz — `[{okno: súhrn | None}]`.

        Beží vnútri hyperoptu (ten má stroj pre seba), každý backtest v podprocese na jednom jadre.
        Config bodu prejde väzbami stratégie (`constrain`) ako epocha hyperoptu.
        """
        import shutil
        from concurrent.futures import ThreadPoolExecutor

        from tradebot.core.paths import BACKTEST_RESULTS

        from .. import hyperopt as ho
        from .command import write_profile
        from .results import result_from_zip

        strategy = job.settings.get("strategy") or "ibs"
        spec = get_spec(strategy)
        base = {k: v for k, v in job.settings.items() if k != "hyperopt"}
        zaklad = {k: v for k, v in (job.params or {}).items() if not k.startswith("_")}
        out: list[dict] = [dict() for _ in points]

        def jeden(i: int, okno: str) -> None:
            if job.cancel_requested:
                return
            meno = f"{job.id}-x{i}-{okno}"
            cfg = spec.config_cls.from_dict({**zaklad, **ho.overrides(plan, points[i])})
            ho.knowledge(spec).constrain(cfg)
            prof = write_profile(meno, cfg.to_dict(), instrument, strategy)
            adresar = BACKTEST_RESULTS / meno
            adresar.mkdir(parents=True, exist_ok=True)
            cmd = self.build_command(self.python, prof, {**base, "timerange": okno}) + ["--backtest-directory", str(adresar)]
            env = dict(os.environ, TRADEBOT_PROFILE=str(prof), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            env.pop("TRADEBOT_HYPEROPT_PLAN", None)
            env.pop("TRADEBOT_DRAW_OUT", None)
            try:
                done = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace")
                zipy = sorted(adresar.glob("*.zip"), key=lambda p: p.stat().st_mtime)
                out[i][okno] = result_from_zip(zipy[-1])[0] if done.returncode == 0 and zipy else None
            finally:
                shutil.rmtree(adresar, ignore_errors=True)
                prof.unlink(missing_ok=True)

        with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as ex:
            for f in [ex.submit(jeden, i, w) for i in range(len(points)) for w in windows]:
                f.result()
        return out

    def _ft_plateau_select(self, job: Job, instrument: str, plan, epochs: list, windows: list[str]):
        """Výber podľa okolia pre Freqtrade: kandidáti aj ich susedia ako backtesty na oknách kritéria."""
        from .. import native_hyperopt as nh

        kandidati = nh.plateau_candidates(epochs, plan)
        body = [e.params for e, _ in kandidati] + [b["params"] for _e, susedia in kandidati for b in susedia]
        job.log_lines.append(f"vyber podla okolia: {len(kandidati)} kandidatov, {len(body)} backtestov "
                             f"na {len(windows)} oknach (Freqtrade)")
        suhrny = self._ft_points(job, instrument, plan, body, windows)
        strata = [nh.aggregate([nh.loss_of(s.get(w), plan, nh.window_days(w)) for w in windows], plan.aggregate or "min")
                  for s in suhrny]
        k = len(kandidati)
        scored, pos = [], k
        for i, (e, susedia) in enumerate(kandidati):
            scored.append((e, strata[i], [(b, strata[pos + j]) for j, b in enumerate(susedia)]))
            pos += len(susedia)
        info = nh.plateau_choice(scored)
        vitaz = next(e for e in epochs if e.number == info["chosen"])
        job.log_lines.append(f"vyber podla okolia: epocha {info['chosen']} (najlepsia bola {info['best_epoch']})")
        return vitaz, info

    def _ft_walk_forward(self, job: Job, instrument: str, profile: Path, t0: float, plan) -> None:
        """Walk-forward cez Freqtrade: hyperopt na okne N (alebo do N), víťaz ako backtest na N+1."""
        from dataclasses import replace

        from .. import hyperopt as ho
        from .. import native_hyperopt as nh

        settings = job.settings
        zadanie = settings["hyperopt"]
        okna = list(zadanie.get("windows") or [])
        if len(okna) < 2:
            okna = list(ho.REFERENCE_WINDOWS)
        anchored = bool(zadanie.get("anchored"))
        spolu = int(zadanie.get("epochs") or ho.DEFAULT_EPOCHS)
        foldov = len(okna) - 1
        seed = zadanie.get("seed")
        fee = float(settings.get("fee") or 0.0)
        folds, vsetky = [], []
        for i in range(foldov):
            if job.cancel_requested:
                break
            train = okna[: i + 1] if anchored else [okna[i]]
            test = okna[i + 1]
            plan_i = replace(plan, windows=tuple(train) if len(train) > 1 else ())
            job.log_lines.append(f"fold {i + 1}/{foldov}: hyperopt {' + '.join(train)} -> test {test}")
            eps, _res, chyba = self._ft_hyperopt(job, plan_i, profile, instrument, ho.span(train), spolu,
                                                 None if seed is None else seed + i, spolu * foldov,
                                                 done_before=i * spolu, label=f"-f{i}")
            if chyba is not None:
                job.status = "failed"
                job.error = f"fold {i + 1}: {chyba}"
                job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self._persist(job, None, round(time.time() - t0, 1))
                return
            offset = len(vsetky)
            vsetky.extend(replace(e, number=offset + e.number, fold=i, is_best=False) for e in eps)
            vitaz = ho.best(eps)
            if vitaz is not None and zadanie.get("select") == "plateau":
                vitaz, _info = self._ft_plateau_select(job, instrument, plan_i, eps, train)
            fold = {"fold": i, "train": train, "test": test, "epochs": len(eps)}
            if vitaz is None:
                fold.update(params=None, train_loss=None, result=None, edge=None)
            else:
                summ = self._ft_points(job, instrument, plan, [vitaz.params], [test])[0].get(test)
                edge = ho.edge_of({"result": summ or {}, "settings": {"fee": fee}})
                fold.update(params=ho.overrides(plan, vitaz.params), hp=vitaz.params, train_loss=vitaz.loss,
                            train_score=-vitaz.loss, result=summ, edge=edge,
                            test_loss=nh.loss_of(summ, plan, nh.window_days(test)))
                job.log_lines.append(f"  fold {i + 1}: ladene skore {-vitaz.loss:.4f}, test break-even "
                                     f"{(summ or {}).get('break_even_pct')}")
            folds.append(fold)
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        duration = round(time.time() - t0, 1)
        if job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            return
        verdikt = nh.walk_forward_verdict(folds)
        job.log_lines.append(verdikt)
        posledny = next((f.get("params") for f in reversed(folds) if f.get("params")), None)
        job.status = "done"
        job.settings = {**settings, "hyperopt": {
            **{k: v for k, v in zadanie.items() if k != "warm"}, "windows": okna, "epochs_done": len(vsetky),
            "best": None, "overrides": posledny, "results_file": None,
            "walk_forward": {"folds": folds, "verdict": verdikt, "anchored": anchored},
        }}
        self._persist(job, None, duration)
        self.store.save_extra(job.id, "epochs.json", [e.to_dict() for e in vsetky])

    def _run_native_hyperopt(self, job: Job, instrument: str, profile: Path, t0: float, plan) -> None:
        """Hyperopt C# strategie na emulatore MultiCharts: Optuna v tomto procese, epochy v C# na pracovnych procesoch.

        Zaznam behu ma ten isty tvar ako hyperopt cez Freqtrade (epochy v `epochs.json`, vitaz
        a `overrides` v `settings.hyperopt`), overovacie behy su obycajne behy emulatora. Navyse
        (`settings.hyperopt`): `windows` + `aggregate` (kriterium cez viac okien), `objectives`
        (viac cielov, Pareto), `select` (`plateau` = vitaz podla okolia), `mode="walkforward"`
        (+ `anchored`), `continue_from` / `warm` (pokracovanie predosleho hladania).
        """
        from .. import hyperopt as ho
        from .. import native_hyperopt as nh
        from tradebot.core.candles import timeframe_minutes

        settings = job.settings
        zadanie = settings["hyperopt"]
        spolu = int(zadanie.get("epochs") or ho.DEFAULT_EPOCHS)
        sampler = zadanie.get("sampler") or "tpe"
        fee = float(settings.get("fee") or 0.0)
        wallet = float(settings.get("wallet") or 10000)
        okna = list(zadanie.get("windows") or []) or [settings["timerange"]]
        walk = zadanie.get("mode") == "walkforward"
        if walk and len(okna) < 2:
            okna = list(ho.REFERENCE_WINDOWS)
        celkom = spolu * (len(okna) - 1) if walk else spolu
        popis = (f"walk-forward {len(okna) - 1} foldov" if walk else
                 (f"{len(okna)} okien ({zadanie.get('aggregate') or 'min'})" if len(okna) > 1 else settings["timerange"]))
        job.log_lines.append(f"$ natívny hyperopt {plan.strategy} {settings['pair']} {settings.get('timeframe')} "
                             f"{popis}: {celkom} epoch, sampler {sampler} (C# emulátor MultiCharts)")
        start = time.time()
        job.progress = ho.eta(0, celkom, start, None, 0, start)
        stav = {"prva_kedy": None, "prva": 0}

        def _priebeh(hotovo: int, _spolu: int) -> None:
            teraz = time.time()
            if stav["prva_kedy"] is None:
                stav["prva_kedy"], stav["prva"] = teraz, hotovo
            job.progress = ho.eta(hotovo, celkom, start, stav["prva_kedy"], stav["prva"], teraz, teraz)

        def _log(line: str) -> None:
            job.log_lines.append(line)
            if len(job.log_lines) > 5000:
                del job.log_lines[:1000]

        warm = None
        if zadanie.get("continue_from"):
            warm = self.store.extra(zadanie["continue_from"], "epochs.json") or zadanie.get("warm") or []
            if not warm:
                _log(f"POZOR: hyperopt {zadanie['continue_from']} nemá uložené epochy - hľadá sa odznova")
        hladanie = wf = None
        try:
            runner = nh.NativeRunner(plan.strategy, INSTRUMENTS[instrument],
                                     timeframe_minutes(settings.get("timeframe") or "3m"), fee,
                                     int(zadanie.get("jobs") or 0))
            spolocne = dict(sampler=sampler, seed=zadanie.get("seed"), wallet=wallet, log=_log,
                            aggregate_how=zadanie.get("aggregate") or "min", select=zadanie.get("select") or "best",
                            should_stop=lambda: job.cancel_requested, on_progress=_priebeh)
            if walk:
                wf = nh.walk_forward(runner, plan, str(profile), okna, epochs=spolu,
                                     anchored=bool(zadanie.get("anchored")), **spolocne)
            else:
                hladanie = nh.run_search(runner, plan, str(profile), okna[-1], epochs=spolu, windows=okna,
                                         objectives=zadanie.get("objectives") or None, warm=warm, **spolocne)
        except (ValueError, FileNotFoundError) as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._persist(job, None, round(time.time() - t0, 1))
            return
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        duration = round(time.time() - t0, 1)
        if job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            return

        zadanie = {k: v for k, v in zadanie.items() if k != "warm"}   # epochy nesie epochs.json, nie settings
        if wf is not None:
            _log(f"hotovo: {len(wf.epochs)} epoch za {wf.seconds:.1f} s - {wf.verdict}")
            job.status = "done"
            job.settings = {**settings, "hyperopt": {
                **zadanie, "native": True, "sampler": sampler, "windows": okna,
                "epochs_done": len(wf.epochs), "best": None,
                "overrides": wf.last, "results_file": None,
                "walk_forward": {"folds": wf.folds, "verdict": wf.verdict, "anchored": bool(zadanie.get("anchored"))},
            }}
            self._persist(job, None, duration)
            self.store.save_extra(job.id, "epochs.json", [e.to_dict() for e in wf.epochs])
            return   # walk-forward má overenie v sebe: každé testovacie okno optimalizátor nevidel

        epochs, vitaz = hladanie.epochs, hladanie.best
        _log(f"hotovo: {len(epochs)} epoch ({hladanie.distinct} roznych backtestov) za {hladanie.seconds:.1f} s")
        job.status = "done"
        job.settings = {**settings, "hyperopt": {
            **zadanie,
            "native": True,
            "sampler": sampler,
            "windows": okna if len(okna) > 1 else None,
            "epochs_done": len(epochs),
            "distinct": hladanie.distinct,
            "best": vitaz.to_dict() if vitaz else None,
            "overrides": ho.overrides(plan, vitaz.params) if vitaz else None,
            "results_file": None,
            "pareto": hladanie.pareto or None,
            "plateau_select": hladanie.plateau,
        }}
        self._persist(job, None, duration)
        self.store.save_extra(job.id, "epochs.json", [e.to_dict() for e in epochs])
        if vitaz is None or not zadanie.get("verify", True):
            return
        self._verify_winner(job, plan, vitaz)

    def _verify_winner(self, job: Job, plan, vitaz) -> None:
        """Vitazne parametre na referencne okna - jedine, co odhali pretrenovanie."""
        from .. import hyperopt as ho

        najdene = ho.overrides(plan, vitaz.params)
        # natívny hyperopt ladí aj na viacerých oknách naraz - všetky sú „ladené"
        ladene_okna = list((job.settings.get("hyperopt") or {}).get("windows") or []) or [job.settings["timerange"]]
        okna = ladene_okna + [w for w in ho.REFERENCE_WINDOWS if w not in ladene_okna]
        popis = ", ".join(f"{k}={v}" for k, v in najdene.items())
        for okno in okna:
            settings = {k: v for k, v in job.settings.items() if k != "hyperopt"}
            settings["timerange"] = okno
            settings["hyperopt_run"] = {"id": job.id, "values": najdene, "tuned": okno in ladene_okna,
                                        "goal": plan.goal}
            try:
                self.submit({**job.params, **najdene}, settings,
                            note=f"hyperopt {job.id}: {popis}" + (f" — {job.note}" if job.note else ""),
                            user=job.user)
            except Exception as exc:  # noqa: BLE001 - jedno okno nesmie zhodit ostatne
                job.log_lines.append(f"overenie {okno} sa nezaradilo: {exc}")
