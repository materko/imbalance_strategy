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
        plan_file = ho.plan_path(job.id, plan)
        inst = INSTRUMENTS[instrument]
        cmd = ho.command(
            self.python, plan=plan_file,
            config=engines.stake_config(inst, settings.get("exchange")),
            userdir=USER_DIR, datadir=engines.data_dir(inst, settings.get("exchange")),
            strategy_class=get_spec(settings.get("strategy") or "ibs").freqtrade_class,
            pair=settings["pair"], timerange=settings["timerange"],
            timeframe=settings.get("timeframe") or "3m",
            epochs=int(zadanie.get("epochs") or ho.DEFAULT_EPOCHS),
            detail=settings.get("timeframe_detail"), wallet=settings.get("wallet", 10000),
            fee=settings.get("fee"), seed=zadanie.get("seed"), jobs=zadanie.get("jobs"),
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
        spolu = int(zadanie.get("epochs") or ho.DEFAULT_EPOCHS)
        job.progress = ho.eta(0, spolu, start, None, 0, time.time())

        # Vo vlákne, nie v slučke nad výstupom: Freqtrade do rúry vypíše riadok len pri
        # novej najlepšej epoche, takže neskôr v behu by sa odhad celé minúty nepohol.
        def _sleduj() -> None:
            prva_kedy, prva_pocet, posledna_kedy, predtym = None, 0, None, 0
            while job.proc is not None and job.proc.poll() is None:
                teraz = time.time()
                hotovo = ho.count_epochs(ho.latest_results(start))
                if hotovo and prva_kedy is None:
                    prva_kedy, prva_pocet = teraz, hotovo
                if hotovo != predtym:
                    posledna_kedy, predtym = teraz, hotovo
                job.progress = ho.eta(hotovo, spolu, start, prva_kedy, prva_pocet, teraz,
                                      posledna_kedy)
                time.sleep(5)

        threading.Thread(target=_sleduj, daemon=True, name=f"eta-{job.id}").start()
        with job.proc.stdout:  # rúra sa zatvorí hneď — Job (a jeho Popen) ostáva v pamäti
            for line in job.proc.stdout:
                job.log_lines.append(line.rstrip("\n"))
                if len(job.log_lines) > 5000:
                    del job.log_lines[:1000]
        rc = job.proc.wait()
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        duration = round(time.time() - t0, 1)

        if job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            return
        if ho.blocked_by_other(job.log_lines):
            job.status = "failed"
            job.error = ("Freqtrade nepustí dva hyperopty naraz a iný práve beží (aj z iného "
                         "okna alebo klonu). Tento nezačal — pusti ho znova, keď ten dobehne.")
            self._persist(job, None, duration)
            return
        if rc != 0:
            job.status = "failed"
            job.error = f"freqtrade hyperopt skončil s kódom {rc}"
            self._persist(job, None, duration)
            return

        results = ho.latest_results(start)
        epochs = ho.read_results(results) if results else []
        vitaz = ho.best(epochs)
        job.status = "done"
        job.settings = {**settings, "hyperopt": {
            **zadanie,
            "epochs_done": len(epochs),
            "best": vitaz.to_dict() if vitaz else None,
            "overrides": ho.overrides(plan, vitaz.params) if vitaz else None,
            "results_file": results.name if results else None,
        }}
        self._persist(job, None, duration)
        # Zaznam behu drzi vsetky epochy zvlast - do zoznamu historie by nesadli.
        self.store.save_extra(job.id, "epochs.json", [e.to_dict() for e in epochs])

        if vitaz is None or not zadanie.get("verify", True):
            return
        self._verify_winner(job, plan, vitaz)

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
