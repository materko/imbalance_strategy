"""Strana zadávateľa: spýtať sa hubu, či je niekto voľný, poslať výpočet, počkať, vziať výsledok.

    client = HubClient.from_config(cfg)        # cfg.send musí byť True
    cap = client.capacity("all")               # kto by hyperopt zobral hneď, kedy najskôr inak
    job = client.submit("hyperopt", payload, queue=True, max_wait_seconds=1800)
    job = client.wait(job["id"])
    run_ids = client.collect(job["id"])        # zip → tester/runs/, ack na hube

`HubHttp` je tenký obal nad `http.client` (žiadna nová závislosť) s tokenom v hlavičke —
používa ho aj agent. Chyby hubu prídu ako `HubError(status, detail)`.

**Jedno trvalé spojenie na vlákno (HTTP/1.1 keep-alive), nie nové na každú požiadavku.**
Heartbeat každých pár sekúnd a pollovanie webapp robili stovky krátkych TCP+TLS spojení za
minútu. Domáci router alebo CGNAT, ktorý prideľuje zdrojové porty z úzkeho rozsahu, ich rýchlo
pretočí a nový SYN na port, ku ktorému firewall pred hubom ešte drží starý stav, sa zahodí —
spojenie sa nenadviaže a agent padá online/offline (10/2026, Mac za Orange optikou). Preto:
spojenie sa drží a znova používa; nadviazanie má krátky timeout (`CONNECT_TIMEOUT`) a keď
sa zasekne, skúsi sa nové spojenie (nový zdrojový port); spojenie, ktoré server medzitým
zavrel, sa zahodí a požiadavka ide raz znova na novom.
"""

from __future__ import annotations

import http.client
import json
import select
import ssl
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from tradebot.core.paths import RUNS_DIR

from ..webapp.store import RunStore
from . import protocol as P
from .config import AgentConfig
from .transfer import unpack_runs

__all__ = ["HubError", "NoCapacityError", "HubHttp", "HubClient", "fmt_eta"]


def _name(text: str) -> str:
    """Meno agenta do cesty URL — mená môžu mať medzeru („MACMINI MARTIN")."""
    from urllib.parse import quote

    return quote(text, safe="")


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


#: Na nadviazanie TCP/TLS spojenia sa čaká krátko; zaseknuté nadviazanie sa skúsi znova
#: s novým spojením (iný zdrojový port), spolu najviac `CONNECT_ATTEMPTS`-krát.
CONNECT_TIMEOUT = 5.0
CONNECT_ATTEMPTS = 3

#: Server zavrel nečinné spojenie (keep-alive timeout) práve vtedy, keď išla požiadavka.
_STALE = (http.client.RemoteDisconnected, ConnectionResetError, ConnectionAbortedError, BrokenPipeError)


def _dropped(conn: http.client.HTTPConnection) -> bool:
    """Spojenie bez rozbehnutej požiadavky, z ktorého sa dá čítať, server zavrel (EOF)."""
    if conn.sock is None:
        return True
    try:
        readable, _, _ = select.select([conn.sock], [], [], 0)
    except (OSError, ValueError):
        return True
    return bool(readable)


class HubHttp:
    def __init__(self, url: str, token: str = "", timeout: float = 30.0,
                 connect_timeout: float = CONNECT_TIMEOUT) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        parts = urlsplit(self.url)
        self._scheme = parts.scheme or "http"
        self._host = parts.hostname or ""
        self._port = parts.port
        self._prefix = parts.path
        self._ssl: ssl.SSLContext | None = None
        self._local = threading.local()
        # Cez proxy (HTTP_PROXY a spol.) ostáva pôvodná cesta cez urllib.
        self._proxied = bool(urllib.request.getproxies().get(self._scheme)) \
            and not urllib.request.proxy_bypass(self._host)

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if content_type:
            h["Content-Type"] = content_type
        return h

    @staticmethod
    def _error(status: int, telo: bytes, method: str, path: str) -> HubError:
        text = telo.decode("utf-8", "replace")
        try:
            detail = json.loads(text).get("detail", text)
        except (json.JSONDecodeError, AttributeError):
            detail = text
        if status == 409 and path.startswith("/api/jobs") and method == "POST" and path.count("/") == 2:
            return NoCapacityError(status, detail)
        return HubError(status, detail)

    # -- spojenie (jedno na vlákno) ----------------------------------------- #

    def _connect(self) -> http.client.HTTPConnection:
        posledna: OSError | None = None
        for _ in range(CONNECT_ATTEMPTS):
            if self._scheme == "https":
                if self._ssl is None:
                    self._ssl = ssl.create_default_context()
                conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                    self._host, self._port, timeout=self.connect_timeout, context=self._ssl)
            else:
                conn = http.client.HTTPConnection(self._host, self._port, timeout=self.connect_timeout)
            try:
                conn.connect()
                return conn
            except OSError as exc:
                conn.close()
                posledna = exc
                # Znova má zmysel len zaseknuté alebo zhodené nadviazanie, nie odmietnutie,
                # neznáma adresa či zlý certifikát.
                if not isinstance(exc, (TimeoutError, ConnectionResetError, ConnectionAbortedError)):
                    break
        raise urllib.error.URLError(posledna)

    def _connection(self, timeout: float) -> tuple[http.client.HTTPConnection, bool]:
        conn = getattr(self._local, "conn", None)
        if conn is not None and _dropped(conn):
            self.close()
            conn = None
        if conn is not None:
            try:
                conn.sock.settimeout(timeout)
                return conn, True
            except OSError:
                self.close()
        conn = self._connect()
        self._local.conn = conn
        conn.sock.settimeout(timeout)
        return conn, False

    def close(self) -> None:
        """Zavrie spojenie tohto vlákna (ďalšia požiadavka otvorí nové)."""
        conn = getattr(self._local, "conn", None)
        self._local.conn = None
        if conn is not None:
            conn.close()

    def _call(self, method: str, path: str, data: bytes | None = None,
              content_type: str | None = None, timeout: float | None = None) -> tuple[bytes, str]:
        if self._proxied:
            return self._call_urllib(method, path, data, content_type, timeout)
        headers = self._headers(content_type)
        for pokus in (1, 2):
            conn, reused = self._connection(timeout or self.timeout)
            try:
                conn.request(method, self._prefix + path, body=data, headers=headers)
                r = conn.getresponse()
                body = r.read()
            except _STALE as exc:
                self.close()
                if reused and pokus == 1:
                    continue
                raise urllib.error.URLError(exc) from None
            except BaseException:
                self.close()
                raise
            if r.will_close:
                self.close()
            if 300 <= r.status < 400:  # presmerovanie (proxy pred hubom) — postará sa urllib
                return self._call_urllib(method, path, data, content_type, timeout)
            if r.status >= 400:
                raise self._error(r.status, body, method, path)
            return body, r.headers.get("content-type", "")
        raise AssertionError("nedosiahnuteľné")

    def _call_urllib(self, method: str, path: str, data: bytes | None,
                     content_type: str | None, timeout: float | None) -> tuple[bytes, str]:
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers=self._headers(content_type))
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                return r.read(), r.headers.get("content-type", "")
        except urllib.error.HTTPError as exc:
            raise self._error(exc.code, exc.read(), method, path) from None

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

    def patch(self, path: str, body: dict[str, Any] | None = None) -> Any:
        data, ct = self._call("PATCH", path, json.dumps(body or {}).encode("utf-8"), "application/json")
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")

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

    def plugins(self) -> list[dict[str, Any]]:
        return self.http.get("/api/plugins")

    def tokens(self) -> list[dict[str, Any]]:
        return self.http.get("/api/tokens")

    def add_token(self, name: str) -> str:
        return self.http.post(f"/api/tokens/{name}")["token"]

    def remove_token(self, name: str) -> bool:
        self.http.delete(f"/api/tokens/{name}")
        return True

    def forget_agent(self, name: str, force: bool = False, with_token: bool = False) -> dict[str, Any]:
        """Vyhodiť agenta z hubu (premenovaný stroj, zrušený agent) — len správca."""
        return self.http.delete(f"/api/agents/{_name(name)}?force={'true' if force else 'false'}"
                                f"&token={'true' if with_token else 'false'}")

    def set_accept(self, name: str, value: bool) -> dict[str, Any]:
        """Zapnúť alebo vypnúť prijímanie výpočtov na agentovi (prevezme si to v heartbeate)."""
        return self.http.post(f"/api/agents/{_name(name)}/accept?value={'true' if value else 'false'}")

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
        store = RunStore(store_root or RUNS_DIR)
        root = store.root
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
                run_ids = unpack_runs(data, root, store.batches)
                self.http.post(f"/api/jobs/{job_id}/ack")
        if not run_ids:
            run_ids = [r for r in (job.get("run_ids") or [])
                       if (root / r / "run.json").exists() or store.batches.find(r)]
        return run_ids
