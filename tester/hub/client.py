"""Strana zadávateľa: spýtať sa hubu, či je niekto voľný, poslať výpočet, počkať, vziať výsledok.

    client = HubClient.from_config(cfg)        # cfg.send musí byť True
    cap = client.capacity("all")               # kto by hyperopt zobral hneď, kedy najskôr inak
    job = client.submit("hyperopt", payload, queue=True, max_wait_seconds=1800)
    job = client.wait(job["id"])
    run_ids = client.collect(job["id"])        # zip → tester/runs/, ack na hube

`HubHttp` je tenký obal nad `urllib` (žiadna nová závislosť) s tokenom v hlavičke —
používa ho aj agent. Chyby hubu prídu ako `HubError(status, detail)`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import RUNS_DIR

from . import protocol as P
from .config import AgentConfig
from .transfer import unpack_runs

__all__ = ["HubError", "NoCapacityError", "HubHttp", "HubClient", "fmt_eta"]


def fmt_eta(seconds: float | None) -> str:
    """`None` = nikdy, 0 = hneď, inak sekundy alebo minúty — pre konzolu aj pre webapp."""
    if seconds is None:
        return "nikdy"
    if seconds <= 0:
        return "hned"
    if seconds < 90:
        return f"{seconds:.0f} s"
    return f"{seconds / 60:.0f} min"


class HubError(Exception):
    def __init__(self, status: int, detail: Any) -> None:
        text = detail.get("message") if isinstance(detail, dict) and "message" in detail else detail
        super().__init__(f"hub {status}: {text}")
        self.status = status
        self.detail = detail


class NoCapacityError(HubError):
    """409 zo `/api/jobs`: nikto voľný a fronta nebola povolená (alebo by trvala pridlho)."""

    @property
    def eta_start(self) -> float | None:
        return (self.detail or {}).get("eta_start_seconds") if isinstance(self.detail, dict) else None


class HubHttp:
    def __init__(self, url: str, token: str = "", timeout: float = 30.0) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _call(self, method: str, path: str, data: bytes | None = None,
              content_type: str | None = None, timeout: float | None = None) -> tuple[bytes, str]:
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers=self._headers(content_type))
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                return r.read(), r.headers.get("content-type", "")
        except urllib.error.HTTPError as exc:
            telo = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(telo).get("detail", telo)
            except (json.JSONDecodeError, AttributeError):
                detail = telo
            if exc.code == 409 and path.startswith("/api/jobs") and method == "POST" and path.count("/") == 2:
                raise NoCapacityError(exc.code, detail) from None
            raise HubError(exc.code, detail) from None

    def get(self, path: str) -> Any:
        data, ct = self._call("GET", path)
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")

    def get_bytes(self, path: str) -> bytes:
        return self._call("GET", path, timeout=max(self.timeout, 300))[0]

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        data, ct = self._call("POST", path, json.dumps(body or {}).encode("utf-8"), "application/json")
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")

    def post_bytes(self, path: str, data: bytes) -> Any:
        out, ct = self._call("POST", path, data, "application/zip", timeout=max(self.timeout, 300))
        return json.loads(out) if "json" in ct else out.decode("utf-8", "replace")

    def delete(self, path: str) -> Any:
        data, ct = self._call("DELETE", path)
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")

    def alive(self) -> bool:
        try:
            self._call("GET", "/api/health", timeout=5)
            return True
        except (HubError, urllib.error.URLError, OSError, ValueError):
            return False


class HubClient:
    def __init__(self, http: HubHttp, name: str) -> None:
        self.http = http
        self.name = name

    @classmethod
    def from_config(cls, cfg: AgentConfig) -> "HubClient":
        if not cfg.send:
            raise PermissionError(f"agent {cfg.name!r} nemá povolené posielať výpočty "
                                  f"(send=false v tester/agent.json)")
        return cls(HubHttp(cfg.hub_url, cfg.token), cfg.name)

    # -- dopyty ------------------------------------------------------------- #

    def capacity(self, demand: int | str = 1) -> dict[str, Any]:
        return self.http.get(f"/api/capacity?cores={demand}")

    def status(self) -> dict[str, Any]:
        return self.http.get("/api/status")

    def job(self, job_id: str) -> dict[str, Any]:
        return self.http.get(f"/api/jobs/{job_id}")

    def jobs(self, live: bool = False, mine: bool = False) -> list[dict[str, Any]]:
        q = f"?live={'true' if live else 'false'}" + (f"&submitter={self.name}" if mine else "")
        return self.http.get("/api/jobs" + q)

    # -- zadanie ------------------------------------------------------------ #

    def submit(self, kind: str, payload: dict[str, Any], *, cores: int | str | None = None,
               queue: bool = False, max_wait_seconds: float | None = None,
               estimate_seconds: float | None = None, note: str = "",
               version: str | None = None, max_seconds: float | None = None) -> dict[str, Any]:
        """Pošle výpočet; `NoCapacityError`, keď nikto nie je voľný a fronta nebola povolená.

        `version` je commit kódu zadávateľa (`gitcode.version()`): agent ho pred behom
        overí a keď ho nemá, pullne si repozitár.
        """
        if kind not in P.KINDS:
            raise ValueError(f"neznámy druh výpočtu {kind!r}")
        return self.http.post("/api/jobs", {
            "kind": kind, "payload": payload, "submitter": self.name, "cores": cores,
            "queue": bool(queue), "max_wait_seconds": max_wait_seconds,
            "estimate_seconds": estimate_seconds, "note": note, "version": version,
            "max_seconds": max_seconds,
        })

    def events(self, limit: int = 100, job: str | None = None, agent: str | None = None,
               event: str | None = None) -> list[dict[str, Any]]:
        q = f"?limit={int(limit)}" + (f"&job={job}" if job else "") + (f"&agent={agent}" if agent else "") \
            + (f"&event={event}" if event else "")
        return self.http.get("/api/events" + q)

    def tokens(self) -> list[dict[str, Any]]:
        return self.http.get("/api/tokens")

    def add_token(self, name: str) -> str:
        return self.http.post(f"/api/tokens/{name}")["token"]

    def remove_token(self, name: str) -> bool:
        self.http.delete(f"/api/tokens/{name}")
        return True

    def set_accept(self, name: str, value: bool) -> dict[str, Any]:
        """Zapnúť alebo vypnúť prijímanie výpočtov na agentovi (prevezme si to v heartbeate)."""
        return self.http.post(f"/api/agents/{name}/accept?value={'true' if value else 'false'}")

    def cancel(self, job_id: str) -> dict[str, Any]:
        return self.http.post(f"/api/jobs/{job_id}/cancel?by={self.name}")

    def wait(self, job_id: str, on_tick: Callable[[dict[str, Any]], None] | None = None,
             poll: float = 5.0, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
        """Čaká, kým výpočet skončí (done, failed, cancelled). `on_tick` dostane každý stav."""
        while True:
            job = self.job(job_id)
            if on_tick:
                on_tick(job)
            if job.get("status") in P.FINAL_STATES:
                return job
            sleep(poll)

    def collect(self, job_id: str, store_root: Path | None = None) -> list[str]:
        """Stiahne zip výsledku do histórie a potvrdí hubu. Keď si ho už vzal agent tejto
        webapp (heartbeat), zip na hube nie je — vráti sa zoznam behov zo záznamu."""
        root = Path(store_root or RUNS_DIR)
        job = self.job(job_id)
        run_ids: list[str] = []
        if job.get("has_result") and not job.get("collected"):
            try:
                data = self.http.get_bytes(f"/api/jobs/{job_id}/result")
            except HubError as exc:
                if exc.status != 410:
                    raise
                data = b""
            if data:
                run_ids = unpack_runs(data, root)
                self.http.post(f"/api/jobs/{job_id}/ack")
        if not run_ids:
            run_ids = [r for r in (job.get("run_ids") or []) if (root / r / "run.json").exists()]
        return run_ids
