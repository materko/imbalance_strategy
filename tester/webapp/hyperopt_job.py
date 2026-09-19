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

    def _verify_winner(self, job: Job, plan, vitaz) -> None:
        """Vitazne parametre na referencne okna - jedine, co odhali pretrenovanie."""
        from .. import hyperopt as ho

        najdene = ho.overrides(plan, vitaz.params)
        ladene = job.settings["timerange"]
        okna = [ladene] + [w for w in ho.REFERENCE_WINDOWS if w != ladene]
        popis = ", ".join(f"{k}={v}" for k, v in najdene.items())
        for okno in okna:
            settings = {k: v for k, v in job.settings.items() if k != "hyperopt"}
            settings["timerange"] = okno
            settings["hyperopt_run"] = {"id": job.id, "values": najdene, "tuned": okno == ladene,
                                        "goal": plan.goal}
            try:
                self.submit({**job.params, **najdene}, settings,
                            note=f"hyperopt {job.id}: {popis}" + (f" — {job.note}" if job.note else ""),
                            user=job.user)
            except Exception as exc:  # noqa: BLE001 - jedno okno nesmie zhodit ostatne
                job.log_lines.append(f"overenie {okno} sa nezaradilo: {exc}")
