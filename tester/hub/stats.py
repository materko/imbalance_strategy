"""Štatistika agentov: koľko výpočtov z hubu spravili a ako dlho trvali — časť `HubState`.

Počíta sa pri dokončení výpočtu a drží sa v zázname agenta (`state.json`), lebo hotové
výpočty sa zo zoznamu po čase zahadzujú (`KEEP_FINISHED`). Čas výpočtu je od prvého
hlásenia „running" (inak od pridelenia) po odovzdanie výsledku.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import protocol as P


#: Okno „posledný deň" v sekundách (kĺzavých 24 h, nie kalendárny deň).
DAY_SECONDS = 24 * 3600


def _ts(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _empty() -> dict[str, Any]:
    return {**{k: {"done": 0, "failed": 0, "seconds": 0.0} for k in P.KINDS}, "recent": []}


class StatsMixin:
    """Súhrny výpočtov na agenta — volá ich `_finish` a `_load` v `HubState`."""

    def _job_seconds(self, job: dict[str, Any]) -> float | None:
        koniec = _ts(job.get("finished_at"))
        zaciatok = _ts(job.get("started_at")) or _ts(job.get("assigned_at"))
        if koniec is None or zaciatok is None or koniec < zaciatok:
            return None
        return koniec - zaciatok

    def _count_stats(self, job: dict[str, Any]) -> None:
        """Započíta hotový (`done`) alebo zlyhaný výpočet agentovi, ktorý ho počítal — každý
        výpočet raz; neskorý výsledok po „agent sa odmlčal" prepíše zlyhanie na hotový."""
        status, kind, meno = job.get("status"), job.get("kind"), job.get("agent")
        if status not in ("done", "failed") or kind not in P.KINDS:
            return
        agent = self.agents.get(meno) if meno else None
        bolo = job.get("stats_counted")
        if agent is None or bolo == status or bolo == "done":
            return
        st = agent.setdefault("stats", _empty())
        for k in P.KINDS:
            st.setdefault(k, {"done": 0, "failed": 0, "seconds": 0.0})
        st.setdefault("recent", [])
        if bolo == "failed":
            # zlyhanie mohlo patriť inému agentovi (výpočet sa medzitým pridelil znova)
            stary = self.agents.get(job.get("stats_agent") or meno)
            if stary and stary.get("stats", {}).get(kind):
                stary["stats"][kind]["failed"] = max(0, int(stary["stats"][kind]["failed"]) - 1)
        if status == "done":
            sekundy = self._job_seconds(job)
            st[kind]["done"] += 1
            if sekundy is not None:
                st[kind]["seconds"] = float(st[kind]["seconds"]) + sekundy
                st[kind]["timed"] = int(st[kind].get("timed", 0)) + 1
            koniec = _ts(job.get("finished_at")) or self.clock()
            st["recent"].append([koniec, kind, sekundy])
        else:
            st[kind]["failed"] += 1
        hranica = self.clock() - DAY_SECONDS
        st["recent"] = [r for r in st["recent"] if r[0] >= hranica]
        job["stats_counted"] = status
        job["stats_agent"] = meno

    def _seed_stats(self) -> None:
        """Pri štarte započíta hotové výpočty v `state.json`, ktoré ešte započítané nie sú
        (hub zo staršieho kódu) — z toho, čo zostalo v zozname."""
        for job_id in self.order:
            job = self.jobs[job_id]
            if job["status"] in P.FINAL_STATES and not job.get("stats_counted"):
                self._count_stats(job)

    def _agent_stats(self, agent: dict[str, Any]) -> dict[str, Any]:
        st = agent.get("stats") or {}
        hranica = self.clock() - DAY_SECONDS
        dnes = [r for r in st.get("recent") or [] if r[0] >= hranica]
        out: dict[str, Any] = {}
        for k in P.KINDS:
            s = st.get(k) or {}
            timed = int(s.get("timed", 0))
            den = [r[2] for r in dnes if r[1] == k]
            den_cas = [x for x in den if x is not None]
            out[k] = {
                "done": int(s.get("done", 0)), "failed": int(s.get("failed", 0)),
                "avg_seconds": float(s.get("seconds", 0.0)) / timed if timed else None,
                "day_done": len(den),
                "day_avg_seconds": sum(den_cas) / len(den_cas) if den_cas else None,
            }
        out["done"] = sum(out[k]["done"] for k in P.KINDS)
        out["day_done"] = len(dnes)
        return out
