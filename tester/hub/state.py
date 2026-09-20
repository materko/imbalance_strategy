"""Stav hubu: agenti, fronta výpočtov a odovzdané výsledky (`state.json`, `results/`)."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import HUB_DIR

from . import protocol as P
from .events import EVENTS_KEEP, EventsMixin, _iso
from .tokens import ADMIN, TokensMixin


#: Po koľkých sekundách bez heartbeatu je agent offline (heartbeat je ~10 s).
DEFAULT_AGENT_TIMEOUT = 45.0
#: Koľko hotových výpočtov sa drží v zozname — staršie vyzdvihnuté sa zahodia.
KEEP_FINISHED = 300
#: Koľkokrát sa výpočet skúsi znova, keď agent zmizne uprostred behu.
MAX_ATTEMPTS = 2


class NoCapacity(Exception):
    """Nikto voľný a zadávateľ nechcel frontu (alebo by čakal dlhšie, než dovolil)."""

    def __init__(self, message: str, eta_start: float | None, agents: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.eta_start = eta_start
        self.agents = agents

    def detail(self) -> dict[str, Any]:
        return {"message": str(self), "eta_start_seconds": self.eta_start, "agents": self.agents}


class NameTaken(Exception):
    """Agent s tým istým menom už žije z iného procesu."""


class HubState(TokensMixin, EventsMixin):
    def __init__(self, root: Path | None = None, token: str | None = None, *,
                 heartbeat_seconds: int = 10, agent_timeout: float = DEFAULT_AGENT_TIMEOUT,
                 clock: Callable[[], float] = time.time) -> None:
        self.root = Path(root or HUB_DIR)
        self.token = token or None
        self.heartbeat_seconds = int(heartbeat_seconds)
        self.agent_timeout = float(agent_timeout)
        self.clock = clock
        self.agents: dict[str, dict[str, Any]] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "results").mkdir(exist_ok=True)
        #: meno agenta -> jeho token (`tokens.json`); číta sa znova, keď sa súbor zmení,
        #: takže `token add --local` platí aj pre bežiaci hub.
        self.tokens: dict[str, str] = {}
        self._tokens_stamp: tuple[int, int] | None = None
        self._events: deque[dict[str, Any]] = deque(maxlen=EVENTS_KEEP)
        self._load()
        self._load_tokens()
        self._load_events()

    # -- perzistencia ------------------------------------------------------- #

    @property
    def state_file(self) -> Path:
        return self.root / "state.json"

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.agents = dict(data.get("agents") or {})
        self.jobs = dict(data.get("jobs") or {})
        self.order = [i for i in (data.get("order") or []) if i in self.jobs]
        for name in self.agents:
            self.agents[name]["online"] = False  # kým sa znova neohlási

    def _save(self) -> None:
        tmp = self.state_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"agents": self.agents, "jobs": self.jobs, "order": self.order},
                      fh, ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, self.state_file)

    def result_path(self, job_id: str) -> Path:
        return self.root / "results" / f"{job_id}.zip"

    # -- agenti ------------------------------------------------------------- #

    def register(self, name: str, *, instance: str, cores: int, slots: int, accept: bool,
                 send: bool = True, version: str = "") -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise ValueError("agent musí mať meno")
        with self._lock:
            self._sweep()
            stary = self.agents.get(name)
            if stary and stary.get("online") and stary.get("instance") not in (None, instance):
                raise NameTaken(f"agent {name!r} už beží z iného procesu — mená musia byť jednoznačné")
            now = self.clock()
            agent = {
                **(stary or {}),
                "name": name, "instance": instance, "cores": int(cores), "slots": int(slots),
                "accept": bool(accept), "send": bool(send), "version": version,
                "registered": _iso(now), "last_seen": now, "online": True,
                "load": (stary or {}).get("load") or {},
            }
            self.agents[name] = agent
            self.log("agent_online", agent=name, version=version, cores=int(cores), slots=int(slots),
                     accept=bool(accept), how="register")
            self._dispatch()
            self._save()
            return self._agent_public(agent)

    def heartbeat(self, name: str, body: dict[str, Any]) -> dict[str, Any]:
        """Agent hlási, že žije a čo počíta; odpoveď nesie pridelené výpočty, rušenia a
        hotové výsledky pre výpočty, ktoré tento agent zadal."""
        with self._lock:
            agent = self.agents.get(name)
            if agent is None:
                raise KeyError(name)
            now = self.clock()
            if not agent.get("online"):
                self.log("agent_online", agent=name, version=body.get("version"), how="heartbeat")
            agent["last_seen"] = now
            agent["online"] = True
            agent.pop("bye_at", None)
            for k in ("accept", "send", "cores", "slots", "version", "needs_restart", "updating"):
                if k in body and body[k] is not None:
                    agent[k] = body[k]
            agent["load"] = dict(body.get("load") or {})
            if body.get("instance"):
                agent["instance"] = body["instance"]
            # Prepnutie `accept` z hubu: agent dostane pokyn, kým nehlási to isté.
            ziadane = agent.get("accept_request")
            if ziadane is not None and bool(agent.get("accept")) == bool(ziadane):
                agent.pop("accept_request", None)
                ziadane = None

            hlasene = {j.get("id"): j for j in (body.get("jobs") or []) if j.get("id")}
            self._readopt(name, hlasene, now)
            for job in self._agent_jobs(name):
                r = hlasene.get(job["id"])
                if r is None:
                    # pridelený a ešte nevzatý je v poriadku; bežiaci, ktorý zmizol, nie
                    if job["status"] in ("running", "cancelling"):
                        job["missed"] = int(job.get("missed") or 0) + 1
                        if job["missed"] >= 3:
                            self._lost(job, "agent beh stratil (reštart?)")
                    continue
                job["missed"] = 0
                if job["status"] == "assigned":
                    job["status"] = "running"
                    job["started_at"] = job.get("started_at") or _iso(now)
                    self.log("job_started", job=job["id"], agent=name, run_id=r.get("run_id"))
                for k in ("progress", "eta_seconds", "elapsed_seconds", "run_id"):
                    if r.get(k) is not None:
                        job[k] = r[k]
            self._sweep()
            self._dispatch()
            assign = [dict(j) for j in self._agent_jobs(name) if j["status"] == "assigned"]
            cancel = [j["id"] for j in self._agent_jobs(name) if j["status"] == "cancelling"]
            cancel += [i for i in hlasene if i not in cancel and self._pointless(self.jobs.get(i))]
            finished = [self._job_public(j) for j in self.jobs.values()
                        if j.get("submitter") == name and j["status"] in P.FINAL_STATES
                        and not j.get("collected")]
            self._save()
            return {"assign": assign, "cancel": cancel, "finished": finished,
                    "set_accept": ziadane,
                    "heartbeat_seconds": self.heartbeat_seconds, "now": _iso(now)}

    def request_accept(self, name: str, value: bool) -> dict[str, Any]:
        """Správca hubu zapne alebo vypne prijímanie výpočtov na agentovi — agent si to
        prevezme v najbližšom heartbeate a zapíše do svojho configu."""
        with self._lock:
            agent = self.agents.get(name)
            if agent is None:
                raise KeyError(name)
            agent["accept_request"] = bool(value)
            self.log("accept_request", agent=name, accept=bool(value))
            self._save()
            return self._agent_public(agent)

    def bye(self, name: str) -> dict[str, Any]:
        """Agent sa odhlási (reštart po pulle): meno je hneď voľné, pridelené výpočty
        ostávajú jeho — nový proces si ich vezme; keď sa nevráti do `agent_timeout`, stratia sa."""
        with self._lock:
            agent = self.agents.get(name)
            if agent is None:
                raise KeyError(name)
            agent["online"] = False
            agent["bye_at"] = self.clock()
            self.log("agent_bye", agent=name)
            self._save()
            return self._agent_public(agent)

    def forget(self, name: str, *, force: bool = False, with_token: bool = False,
               by: str = "") -> dict[str, Any]:
        """Vyhodiť agenta zo zoznamu — premenovaný stroj, zrušený agent, preklep v mene.

        Online agenta nie (o desať sekúnd by sa prihlásil späť) — iba s `force`. Čo ešte
        počítal, ide späť do fronty alebo zlyhá ako pri odmlčaní; jeho token ostáva, pokiaľ
        sa nepýta aj oň (`with_token`).
        """
        with self._lock:
            self._sweep()
            agent = self.agents.get(name)
            if agent is None:
                raise KeyError(name)
            if agent.get("online") and not force:
                raise ValueError(f"agent {name!r} je online — vypni ho (alebo to vynúť, "
                                 f"kým beží, prihlási sa späť)")
            zive = self._agent_jobs(name)
            dotknute = [j["id"] for j in zive]
            for job in zive:
                self._lost(job, f"agent {name} bol odstránený z hubu")
            self.agents.pop(name, None)
            self.log("agent_removed", agent=name, by=by or None, jobs=dotknute or None)
            self._load_tokens()
            mal_token = name in self.tokens
            if with_token and mal_token:
                self.remove_token(name, by=by or ADMIN)
            self._dispatch()
            self._save()
            return {"name": name, "jobs": dotknute, "token": mal_token,
                    "token_removed": bool(with_token and mal_token)}

    def _readopt(self, name: str, hlasene: dict[str, Any], now: float) -> None:
        """Agent sa vrátil a stále počíta, čo mu hub medzitým vzal (odmlčal sa) — vrátime
        mu to. Bez toho by sa to počítalo dvakrát alebo by jeho výsledok nemal kam prísť."""
        for job_id, r in hlasene.items():
            job = self.jobs.get(job_id)
            if job is None or job.get("agent") == name or name not in (job.get("lost_agents") or []):
                continue
            if job["status"] != "queued":
                continue  # už ho počíta niekto iný — nech dobehnú obaja, platí prvý hotový
            job.update({"status": "running", "agent": name, "missed": 0,
                        "run_id": r.get("run_id") or job.get("run_id"),
                        "started_at": job.get("started_at") or _iso(now)})
            self.log("job_readopted", job=job_id, agent=name)

    def _pointless(self, job: dict[str, Any] | None) -> bool:
        """Výpočet, ktorý agent hlási, ale počítať ho už nemá zmysel: hub má jeho výsledok
        od niekoho iného, alebo ho niekto zrušil. Stratený výpočet bez výsledku sa nezastavuje
        — práve ten sa oplatí dopočítať a odovzdať neskoro."""
        if job is None or job["status"] not in P.FINAL_STATES:
            return False
        return bool(job.get("has_result")) or job["status"] == "cancelled"

    def _agent_jobs(self, name: str) -> list[dict[str, Any]]:
        return [self.jobs[i] for i in self.order
                if self.jobs[i].get("agent") == name and self.jobs[i]["status"] in P.LIVE_STATES
                and self.jobs[i]["status"] != "queued"]

    def _agent_public(self, agent: dict[str, Any]) -> dict[str, Any]:
        moje = self._agent_jobs(agent["name"])
        b = P.busy(agent, moje)
        return {
            "name": agent["name"], "cores": agent.get("cores"), "slots": b["slots"],
            "accept": bool(agent.get("accept")), "send": bool(agent.get("send")),
            "online": bool(agent.get("online")), "last_seen": _iso(float(agent.get("last_seen") or 0)),
            "version": agent.get("version"), "needs_restart": bool(agent.get("needs_restart")),
            "updating": bool(agent.get("updating")),
            "accept_request": agent.get("accept_request"),
            "load": agent.get("load") or {},
            "used": b["used"], "exclusive": b["exclusive"],
            "jobs": [{"id": j["id"], "kind": j["kind"], "status": j["status"],
                      "progress": j.get("progress"), "eta_seconds": j.get("eta_seconds")} for j in moje],
            "eta_free_1": P.eta_free(agent, 1, moje), "eta_free_all": P.eta_free(agent, P.ALL, moje),
        }

    def _sweep(self) -> None:
        """Agenti bez heartbeatu sú offline a ich výpočty sa vrátia do fronty alebo zlyhajú."""
        now = self.clock()
        for agent in self.agents.values():
            if agent.get("online") and now - float(agent.get("last_seen") or 0) > self.agent_timeout:
                agent["online"] = False
                self.log("agent_offline", agent=agent["name"])
                for job in self._agent_jobs(agent["name"]):
                    self._lost(job, f"agent {agent['name']} sa odmlčal")
            elif agent.get("bye_at") and now - float(agent["bye_at"]) > self.agent_timeout:
                agent.pop("bye_at", None)
                for job in self._agent_jobs(agent["name"]):
                    self._lost(job, f"agent {agent['name']} sa po reštarte nevrátil")
        # Strop na čas behu stráži agent (beh zabije sám); hub je poistka, keby agent
        # bežal na starom kóde alebo strop nevymáhal — dá mu ešte dva intervaly navyše.
        for job in self.jobs.values():
            limit = job.get("max_seconds")
            if job["status"] != "running" or not limit or not job.get("started_at"):
                continue
            try:
                zacal = datetime.fromisoformat(job["started_at"]).timestamp()
            except ValueError:
                continue
            if now - zacal > float(limit) + 2 * self.agent_timeout:
                job["cancelled_by"] = "strop casu"
                job["status"] = "cancelling"
                self.log("job_timeout", job=job["id"], agent=job.get("agent"), max_seconds=limit)

    def _lost(self, job: dict[str, Any], reason: str) -> None:
        """Agent, ktorý to počítal, sa odmlčal. Výpočet ide späť do fronty alebo zlyhá —
        ale kto ho počítal, si pamätáme: on medzitým počíta ďalej (hub nepotrebuje) a keď
        sa vráti, výsledok od neho prijmeme (`result`), hoci ho už vlastní niekto iný."""
        if job.get("agent") and job["agent"] not in job.setdefault("lost_agents", []):
            job["lost_agents"].append(job["agent"])
        if job["status"] == "cancelling":
            self._finish(job, "cancelled", error=reason)
            return
        attempts = int(job.get("attempts") or 0)
        if job["status"] == "assigned" or (job.get("queue") and attempts < MAX_ATTEMPTS):
            job.update({"status": "queued", "agent": None, "progress": None, "eta_seconds": None,
                        "elapsed_seconds": None, "missed": 0, "run_id": None})
            job.setdefault("notes", []).append(reason)
            self.log("job_requeued", job=job["id"], reason=reason)
        else:
            self._finish(job, "failed", error=reason)
            job["lost"] = True  # nepočítal sa dokonca — neskorý výsledok ho ešte oživí

    # -- výpočty ------------------------------------------------------------ #

    def _online_accepting(self) -> list[dict[str, Any]]:
        # Agent, ktorý práve ťahá kód (`git pull` + dáta), nič nevezme — kód sa mu mení
        # pod rukami a trvá to aj minúty. Hlási to v heartbeate.
        return [a for a in self.agents.values()
                if a.get("online") and a.get("accept") and not a.get("updating")]

    def capacity(self, demand: int | str = 1) -> dict[str, Any]:
        """Kto by výpočet s takou požiadavkou zobral hneď a kedy najskôr inak."""
        with self._lock:
            self._sweep()
            agenti = [self._agent_public(a) for a in self.agents.values()]
            volni = [a["name"] for a in self.agents.values()
                     if P.fits(a, demand, self._agent_jobs(a["name"]))]
            eta = self._eta_start(demand)
            cakaju = [j for j in self.jobs.values() if j["status"] == "queued"]
            return {"demand": demand, "free": volni, "eta_start_seconds": eta,
                    "queued": len(cakaju), "agents": agenti,
                    "online": sum(1 for a in self.agents.values() if a.get("online"))}

    def _eta_start(self, demand: int | str) -> float | None:
        """Najskorší štart nového výpočtu: najbližšie uvoľnenie + čo je vo fronte pred ním."""
        prijimaju = self._online_accepting()
        if not prijimaju:
            return None
        etas = [e for e in (P.eta_free(a, demand, self._agent_jobs(a["name"])) for a in prijimaju)
                if e is not None]
        if not etas:
            return None
        cakaju = [j for j in self.jobs.values() if j["status"] == "queued"]
        pred = sum(float(j.get("estimate_seconds") or P.DEFAULT_ETA_SECONDS) for j in cakaju)
        return min(etas) + pred / max(1, len(prijimaju))

    def submit(self, *, kind: str, payload: dict[str, Any], submitter: str, cores: int | str | None = None,
               queue: bool = False, max_wait_seconds: float | None = None,
               estimate_seconds: float | None = None, note: str = "",
               version: str | None = None, max_seconds: float | None = None) -> dict[str, Any]:
        if kind not in P.KINDS:
            raise ValueError(f"neznámy druh výpočtu {kind!r}; známe: {', '.join(P.KINDS)}")
        if not isinstance(payload, dict) or "params" not in payload or "settings" not in payload:
            raise ValueError("payload musí mať params a settings")
        demand: int | str = cores if cores is not None else P.cores_for(payload["settings"], kind)
        if demand != P.ALL:
            demand = max(1, int(demand))
        with self._lock:
            self._sweep()
            volny = self._pick_agent(demand, version)
            eta = self._eta_start(demand)
            if volny is None:
                agenti = [self._agent_public(a) for a in self.agents.values()]
                if not queue:
                    raise NoCapacity("nikto nie je voľný a fronta nebola povolená", eta, agenti)
                if eta is None:
                    raise NoCapacity("žiadny agent online neprijíma výpočty", eta, agenti)
                if max_wait_seconds is not None and eta > float(max_wait_seconds):
                    raise NoCapacity(f"odhadované čakanie {eta / 60:.0f} min presahuje povolených "
                                     f"{float(max_wait_seconds) / 60:.0f} min", eta, agenti)
            now = self.clock()
            job = {
                "id": uuid.uuid4().hex[:12], "kind": kind, "payload": payload, "cores": demand,
                "queue": bool(queue), "max_wait_seconds": max_wait_seconds,
                "estimate_seconds": estimate_seconds, "submitter": submitter, "note": note,
                "version": version or None, "agent_version": None,
                "max_seconds": float(max_seconds) if max_seconds else None,
                "status": "queued", "created": _iso(now), "assigned_at": None, "started_at": None,
                "finished_at": None, "agent": None, "progress": None, "eta_seconds": None,
                "elapsed_seconds": None, "run_id": None, "run_ids": [], "error": None,
                "attempts": 0, "missed": 0, "has_result": False, "collected": False,
                "cancelled_by": None,
            }
            self.jobs[job["id"]] = job
            self.order.append(job["id"])
            self.log("job_submitted", job=job["id"], kind=kind, submitter=submitter, cores=demand,
                     queue=bool(queue), version=version, note=note[:120] if note else None)
            if volny is not None:
                self._assign(job, volny)
            self._prune()
            self._save()
            return self._job_public(job)

    def _pick_agent(self, demand: int | str, version: str | None = None) -> dict[str, Any] | None:
        """Voľný agent — najradšej ten, čo už má commit zadávateľa (bez pullu), a z nich
        ten s najväčšou rezervou, nech sa záťaž rozloží a nie nakopí."""
        kandidati = [a for a in self._online_accepting() if P.fits(a, demand, self._agent_jobs(a["name"]))]
        if not kandidati:
            return None
        def kluc(a: dict[str, Any]) -> tuple[bool, int, str]:
            b = P.busy(a, self._agent_jobs(a["name"]))
            ma_verziu = not version or (a.get("version") or "") == version
            return (ma_verziu, b["slots"] - b["used"], a["name"])
        return max(kandidati, key=kluc)

    def _assign(self, job: dict[str, Any], agent: dict[str, Any]) -> None:
        job.update({"status": "assigned", "agent": agent["name"], "assigned_at": _iso(self.clock()),
                    "attempts": int(job.get("attempts") or 0) + 1, "missed": 0})
        self.log("job_assigned", job=job["id"], agent=agent["name"], attempt=job["attempts"])

    def _dispatch(self) -> None:
        """Fronta v poradí zadania: čo sa zmestí na niektorého agenta, sa pridelí."""
        for job_id in list(self.order):
            job = self.jobs.get(job_id)
            if job is None or job["status"] != "queued":
                continue
            agent = self._pick_agent(job["cores"], job.get("version"))
            if agent is not None:
                self._assign(job, agent)

    def _finish(self, job: dict[str, Any], status: str, *, error: str | None = None,
                run_ids: list[str] | None = None, has_result: bool = False) -> None:
        job.update({"status": status, "error": error, "finished_at": _iso(self.clock()),
                    "has_result": has_result, "progress": 1.0 if status == "done" else job.get("progress"),
                    "eta_seconds": 0.0 if status == "done" else None})
        if run_ids:
            job["run_ids"] = list(run_ids)
        self.log("job_finished", job=job["id"], status=status, agent=job.get("agent"),
                 submitter=job.get("submitter"), error=error, run_ids=list(run_ids or []) or None)

    def cancel(self, job_id: str, by: str = "") -> dict[str, Any]:
        """Zrušenie: vo fronte hneď; pridelené alebo bežiace cez heartbeat počítajúceho agenta."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            if job["status"] in P.FINAL_STATES:
                return self._job_public(job)
            job["cancelled_by"] = by or "hub"
            self.log("job_cancel", job=job["id"], by=job["cancelled_by"], was=job["status"],
                     agent=job.get("agent"))
            if job["status"] == "queued":
                self._finish(job, "cancelled", error=f"zrušené ({job['cancelled_by']})")
            elif job["status"] != "cancelling":
                job["status"] = "cancelling"
            self._save()
            return self._job_public(job)

    def result(self, job_id: str, data: bytes, *, status: str, error: str | None = None,
               run_ids: list[str] | None = None, agent: str | None = None,
               version: str | None = None) -> dict[str, Any]:
        """Agent odovzdal výsledok (zip histórie, alebo prázdno pri chybe).

        Prijíma aj **neskorý** výsledok od agenta, ktorý sa hubu odmlčal a dopočítal to sám
        (výpadok hubu alebo siete): hotový výpočet prepíše „agent sa odmlčal" a zadávateľ
        ho dostane v svojom heartbeate. Čo už má skutočný výsledok, sa neprepisuje — platí
        prvý hotový, druhý sa zahodí.
        """
        if status not in P.FINAL_STATES:
            raise ValueError(f"stav výsledku musí byť jeden z {P.FINAL_STATES}")
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            cudzi = bool(agent) and job.get("agent") not in (None, agent)
            if cudzi and agent not in (job.get("lost_agents") or []):
                raise PermissionError(f"výpočet {job_id} počíta {job['agent']}, nie {agent}")
            if job["status"] in P.FINAL_STATES:
                # Hotový výsledok oživí aj výpočet, ktorý už hub odpísal (agent sa odmlčal,
                # alebo ho inde zlyhal) — pokiaľ naň nemá skutočný výsledok a nebol zrušený.
                if not (status == "done" and data and not job.get("has_result")
                        and job["status"] != "cancelled"):
                    return self._job_public(job)
                job.update({"agent": agent or job.get("agent"), "collected": False, "late": True})
                self.log("job_late_result", job=job_id, agent=agent, was=job["status"])
            elif cudzi:
                # Beží u niekoho iného (hub ho po výpadku pridelil znova): hotový výsledok
                # vezmeme a prvý vyhráva, chybu nie — druhý agent ešte môže uspieť.
                if status != "done" or not data:
                    return self._job_public(job)
                job["agent"] = agent
                job["late"] = True
                self.log("job_late_result", job=job_id, agent=agent, was=job["status"])
            ma_zip = bool(data)
            if ma_zip:
                self.result_path(job_id).write_bytes(data)
            if version:
                job["agent_version"] = version
            if job["status"] == "cancelling" and status != "done":
                status = "cancelled"
                error = f"zrušené ({job.get('cancelled_by') or 'hub'})" + (f": {error}" if error else "")
            self._finish(job, status, error=error, run_ids=run_ids, has_result=ma_zip)
            self._dispatch()
            self._save()
            return self._job_public(job)

    def ack(self, job_id: str) -> dict[str, Any]:
        """Zadávateľ si výsledok vzal — zip už netreba."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            job["collected"] = True
            self.result_path(job_id).unlink(missing_ok=True)
            self.log("job_collected", job=job_id, submitter=job.get("submitter"))
            self._prune()
            self._save()
            return self._job_public(job)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None or job["status"] in P.LIVE_STATES:
                return False
            self.jobs.pop(job_id, None)
            self.order = [i for i in self.order if i != job_id]
            self.result_path(job_id).unlink(missing_ok=True)
            self._save()
            return True

    def _prune(self) -> None:
        hotove = [i for i in self.order if self.jobs[i]["status"] in P.FINAL_STATES and self.jobs[i].get("collected")]
        for job_id in hotove[:-KEEP_FINISHED] if len(hotove) > KEEP_FINISHED else []:
            self.jobs.pop(job_id, None)
            self.order.remove(job_id)
            self.result_path(job_id).unlink(missing_ok=True)

    # -- čítanie ------------------------------------------------------------ #

    def _job_public(self, job: dict[str, Any], with_payload: bool = False) -> dict[str, Any]:
        out = {k: v for k, v in job.items() if k != "payload"}
        s = (job.get("payload") or {}).get("settings") or {}
        out["summary"] = {k: s.get(k) for k in ("strategy", "pair", "timeframe", "timerange", "engine")}
        if with_payload:
            out["payload"] = job.get("payload")
        return out

    def job(self, job_id: str, with_payload: bool = False) -> dict[str, Any] | None:
        with self._lock:
            job = self.jobs.get(job_id)
            return self._job_public(job, with_payload) if job else None

    def list_jobs(self, live_only: bool = False, submitter: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            self._sweep()
            out = []
            for job_id in reversed(self.order):
                job = self.jobs[job_id]
                if live_only and job["status"] not in P.LIVE_STATES:
                    continue
                if submitter and job.get("submitter") != submitter:
                    continue
                out.append(self._job_public(job))
            return out

    def overview(self) -> dict[str, Any]:
        with self._lock:
            self._sweep()
            zive = [j for j in self.jobs.values() if j["status"] in P.LIVE_STATES]
            return {
                "agents": [self._agent_public(a) for a in self.agents.values()],
                "online": sum(1 for a in self.agents.values() if a.get("online")),
                "queued": sum(1 for j in zive if j["status"] == "queued"),
                "running": sum(1 for j in zive if j["status"] in ("assigned", "running", "cancelling")),
                "jobs": [self._job_public(j) for j in zive],
                "heartbeat_seconds": self.heartbeat_seconds,
            }
