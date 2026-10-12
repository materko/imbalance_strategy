"""`HubHttp` nad skutočným socketom: jedno trvalé spojenie, zotavenie po zavretí, chyby hubu.

Ostatné testy hubu idú cez TestClient (`FakeHttp`), takže sieťovú vrstvu nevidia — tu sa
overuje, že klient nerobí nové TCP spojenie na každú požiadavku (pretáčanie portov za NAT,
10/2026) a že sa zotaví, keď server spojenie zavrie alebo nadviazanie zamrzne.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tester.hub.client import HubError, HubHttp, NoCapacityError


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # ticho v testoch
        pass

    def _reply(self, status: int, body: dict, close: bool = False) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        if close:
            self.close_connection = True

    def _handle(self) -> None:
        srv = self.server
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        srv.requests.append((self.command, self.path, self.client_address[1],
                             self.headers.get("Authorization"), body))
        if self.path.endswith("/missing"):
            self._reply(404, {"detail": "nie je"})
        elif self.path.startswith("/api/jobs") and self.command == "POST":
            self._reply(409, {"detail": {"message": "nikto voľný", "eta_start_seconds": 60}})
        elif self.path.endswith("/close"):
            self._reply(200, {"ok": True}, close=True)
        else:
            self._reply(200, {"ok": True, "path": self.path})
        if srv.drop_after_reply:
            # Server zavrie nečinné spojenie bez ohlásenia (ako keep-alive timeout).
            self.close_connection = True

    do_GET = do_POST = do_DELETE = do_PATCH = _handle


@pytest.fixture()
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.daemon_threads = True
    srv.requests = []
    srv.drop_after_reply = False
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _url(srv, prefix: str = "") -> str:
    return f"http://127.0.0.1:{srv.server_address[1]}{prefix}"


def test_jedno_spojenie_pre_viac_poziadaviek(server):
    h = HubHttp(_url(server), token="t")
    for _ in range(5):
        assert h.get("/api/health")["ok"] is True
    h.post("/api/agents/x/heartbeat", {"a": 1})
    porty = {r[2] for r in server.requests}
    assert len(server.requests) == 6
    assert len(porty) == 1, "každá požiadavka otvorila nové TCP spojenie"
    assert server.requests[-1][3] == "Bearer t"
    assert json.loads(server.requests[-1][4]) == {"a": 1}


def test_server_zavrie_necinne_spojenie(server):
    server.drop_after_reply = True
    h = HubHttp(_url(server))
    for _ in range(3):
        assert h.get("/api/health")["ok"] is True
    assert len(server.requests) == 3


def test_connection_close_v_odpovedi(server):
    h = HubHttp(_url(server))
    assert h.get("/api/close")["ok"] is True
    assert h.get("/api/health")["ok"] is True
    assert len({r[2] for r in server.requests}) == 2


def test_zavrete_spojenie_pocas_poziadavky_ide_znova(server, monkeypatch):
    server.drop_after_reply = True
    h = HubHttp(_url(server))
    h.get("/api/health")
    time.sleep(0.2)  # server medzitým spojenie zavrel
    # ...no klient to pri kontrole ešte nevidí (pretek s keep-alive timeoutom servera).
    monkeypatch.setattr("tester.hub.client._dropped", lambda c: False)
    assert h.get("/api/health")["ok"] is True
    assert h.post("/api/agents/x/heartbeat", {})["ok"] is True
    assert len(server.requests) == 3


def test_prefix_cesty(server):
    h = HubHttp(_url(server, "/hub"))
    assert h.get("/api/health")["path"] == "/hub/api/health"


def test_chyby_hubu(server):
    h = HubHttp(_url(server))
    with pytest.raises(HubError) as e:
        h.get("/api/missing")
    assert e.value.status == 404 and e.value.detail == "nie je"
    with pytest.raises(NoCapacityError) as e:
        h.post("/api/jobs", {})
    assert e.value.eta_start == 60
    # Po chybovej odpovedi sa spojenie dá ďalej používať.
    assert h.get("/api/health")["ok"] is True
    assert len({r[2] for r in server.requests}) == 1


def test_zaseknute_nadviazanie_skusi_nove_spojenie(server, monkeypatch):
    povodne = http.client.HTTPConnection.connect
    pokusy = []

    def connect(self):
        pokusy.append(1)
        if len(pokusy) == 1:
            raise TimeoutError("SYN bez odpovede")
        return povodne(self)

    monkeypatch.setattr(http.client.HTTPConnection, "connect", connect)
    h = HubHttp(_url(server))
    assert h.get("/api/health")["ok"] is True
    assert len(pokusy) == 2


def test_hub_mimo(server):
    port = server.server_address[1]
    server.shutdown()
    server.server_close()
    h = HubHttp(f"http://127.0.0.1:{port}", connect_timeout=1)
    assert h.alive() is False
    with pytest.raises(OSError):
        h.get("/api/health")


def test_vlakna_maju_vlastne_spojenie(server):
    h = HubHttp(_url(server))
    h.get("/api/health")
    t = threading.Thread(target=lambda: h.get("/api/health"))
    t.start()
    t.join()
    h.get("/api/health")
    assert len({r[2] for r in server.requests}) == 2
