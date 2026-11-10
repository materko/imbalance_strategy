"""Opravy webapp z auditu architektúry 9. 11. 2026 (`docs/audity/AUDIT_architektura_2026-11-09.md`, §3.5 a §4.4).

Každý test drží jeden nález: čo sa pokazilo, je v jeho docstringu. Freqtrade sa tu nespúšťa a nič
nesiaha na skutočnú históriu (`tester/runs/`) — všetko beží v dočasnom adresári.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import threading
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from tester.webapp.store import RunStore
from tradebot.core.config import DEFAULT_STRATEGY
from tradebot.strategies import STRATEGIES

WEBAPP = Path(__file__).resolve().parents[1] / "webapp"
JS_DIR = WEBAPP / "static" / "js"

BT = {"strategy": "ibs", "pair": "BTC/USDT:USDT", "timeframe": "3m",
      "timerange": "20250904-20260904", "timeframe_detail": "1m", "engine": "freqtrade"}
HO = {**BT, "hyperopt": {"knobs": {"rrRatio": "2:8:0.5"}, "epochs": 100, "verify": True}}


def _record(i: int, **settings) -> dict:
    return {
        "id": f"202609{i // 100:02d}-1200{i % 100:02d}-aaaa{i % 100:02d}", "status": "done" if i % 5 else "failed",
        "created": "2026-09-01T10:00:00+00:00", "user": "tester", "note": f"beh {i}",
        "settings": {**BT, "engine": "freqtrade" if i % 2 else "multicharts",
                     "timeframe_detail": "1m" if i % 3 else "", **settings},
        "params": {"rrRatio": float(i)},
        "result": {"trades": 10 + i, "duration_s": 20.0 + i},
        "series": {"equity": [[1, 100.0]]},
    }


# --------------------------------------------------------------------------- #
# M-WEB-8: CLI a HTTP chyba
# --------------------------------------------------------------------------- #


def _cli_args(**kw):
    return SimpleNamespace(url="http://127.0.0.1:1", user="t", remote=False, no_wait=False, **kw)


def test_cli_http_chyba_nie_je_vypadok(monkeypatch):
    """`HTTPError` je podtrieda `URLError`: 404 alebo 500 pri čakaní na beh sa bralo ako výpadok webapp
    a CLI čakalo 5 minút. Teraz skončí hneď a povie, čo webapp odpovedala."""
    from tester.webapp.cli import run as cli_run

    volania = []

    def fake_api(url, path, body=None):
        volania.append(path)
        if body is not None:
            return {"id": "20260901-120000-abcdef"}
        raise urllib.error.HTTPError(url + path, 404, "Not Found", {}, io.BytesIO(b'{"detail":"beh neexistuje"}'))

    monkeypatch.setattr(cli_run, "server_alive", lambda url: True)
    monkeypatch.setattr(cli_run, "api", fake_api)
    monkeypatch.setattr(cli_run.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as exc:
        cli_run._execute(_cli_args(), {}, dict(BT), "poznámka", quiet=True)
    assert "404" in str(exc.value) and "beh neexistuje" in str(exc.value)
    assert len(volania) == 2          # zadanie + jeden dopyt, žiadne opakovanie


def test_cli_vypadok_spojenia_a_502_caka_dalej(monkeypatch):
    """Skutočný výpadok (odmietnuté spojenie, 502 z proxy pri reštarte) sa ďalej prečká."""
    from tester.webapp.cli import run as cli_run

    odpovede = [urllib.error.URLError("connection refused"),
                urllib.error.HTTPError("u", 502, "Bad Gateway", {}, io.BytesIO(b"")),
                {"record": {"id": "20260901-120000-abcdef", "status": "done"}, "live": False}]

    def fake_api(url, path, body=None):
        if body is not None:
            return {"id": "20260901-120000-abcdef"}
        x = odpovede.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    monkeypatch.setattr(cli_run, "server_alive", lambda url: True)
    monkeypatch.setattr(cli_run, "api", fake_api)
    monkeypatch.setattr(cli_run.time, "sleep", lambda s: None)
    rec = cli_run._execute(_cli_args(), {}, dict(BT), "poznámka", quiet=True)
    assert rec["status"] == "done" and not odpovede


# --------------------------------------------------------------------------- #
# M-WEB-9, N-WEB-14, N-WEB-15: fronta
# --------------------------------------------------------------------------- #


def _runner(tmp_path: Path, **kw):
    from tester.webapp.runner import BacktestRunner

    marker = tmp_path / "spustene.txt"
    r = BacktestRunner(RunStore(tmp_path / "runs"),
                       command_builder=lambda py, *a: [py, "-c", f"open(r'{marker}', 'w').close()"], **kw)
    return r, marker


def test_zrusenie_cakajuceho_behu_je_pod_zamkom_fronty(tmp_path: Path):
    """`cancel` čítal a menil stav bez zámku, pod ktorým worker prepína `queued → running` — beh zrušený
    vo chvíli štartu sa zapísal ako zrušený a aj tak zbehol."""
    from tester.webapp.runner import Job

    r, _ = _runner(tmp_path)
    job = Job(id="20260901-000001-aaaaaa", params={}, settings=dict(BT))
    r.jobs[job.id] = job
    r.order.append(job.id)

    vysledok: list[bool] = []
    with r._lock:                     # worker práve rozhoduje o štarte
        th = threading.Thread(target=lambda: vysledok.append(r.cancel(job.id)))
        th.start()
        th.join(0.3)
        assert th.is_alive() and job.status == "queued" and not vysledok   # cancel čaká na zámok
    th.join(5)
    assert vysledok == [True] and job.status == "failed" and job.error == "zrušené používateľom"
    assert r.store.get(job.id)["status"] == "failed"


def test_beh_zruseny_tesne_pred_startom_nespusti_podproces(tmp_path: Path):
    """Zrušenie medzi prepnutím na `running` a štartom podprocesu nemalo čo zabiť a beh dobehol celý."""
    from tester.webapp.runner import Job

    r, marker = _runner(tmp_path)
    job = Job(id="20260901-000002-bbbbbb", params={}, settings=dict(BT), status="running", cancel_requested=True)
    r.jobs[job.id] = job
    r.order.append(job.id)
    r._run(job)
    assert not marker.exists()
    assert job.status == "failed" and job.error == "zrušené používateľom"
    assert r.store.get(job.id)["error"] == "zrušené používateľom"


def test_fronta_si_nedrzi_dobehnute_behy_donekonecna(tmp_path: Path, monkeypatch):
    """`runner.jobs` rástol až do reštartu webapp (každý Job s tisíckami riadkov logu)."""
    from tester.webapp import runner as runner_mod
    from tester.webapp.runner import Job

    monkeypatch.setattr(runner_mod, "KEEP_FINISHED", 5)
    r, _ = _runner(tmp_path)
    for i in range(12):
        j = Job(id=f"20260901-0000{i:02d}-aaaaaa", params={}, settings=dict(BT),
                status="queued" if i in (0, 7) else "running" if i == 3 else "done")
        r.jobs[j.id] = j
        r.order.append(j.id)
    r._forget_old()
    ostali = [r.jobs[i].status for i in r.order]
    assert set(r.jobs) == set(r.order)
    assert ostali.count("done") == 5 and ostali.count("queued") == 2 and ostali.count("running") == 1
    assert r.order[-1] == "20260901-000011-aaaaaa" and "20260901-000001-aaaaaa" not in r.jobs   # ostali najnovšie
    assert r.snapshot() and r.load()["queued"] == 2          # fronta po upratovaní žije ďalej


def test_znizenie_workers_plati_hned(tmp_path: Path):
    """`start()` vlákna len pridáva; po znížení `workers` ich bežalo ďalej toľko ako predtým."""
    from tester.webapp.runner import Job

    r, _ = _runner(tmp_path, workers=3)
    a = Job(id="20260901-000001-aaaaaa", params={}, settings=dict(BT), status="running")
    b = Job(id="20260901-000002-bbbbbb", params={}, settings=dict(BT))
    r.jobs = {a.id: a, b.id: b}
    r.order = [a.id, b.id]
    assert r._can_start(b)
    r.workers = 1
    assert not r._can_start(b)        # jeden beží, strop je 1
    a.status = "done"
    assert r._can_start(b)


# --------------------------------------------------------------------------- #
# M-WEB-10: predloha C# portu, jedna konštanta defaultu, zaradenie stratégií
# --------------------------------------------------------------------------- #


def test_predlohu_portu_hovori_spec_nie_meno_kluca():
    csharp = {k: s for k, s in STRATEGIES.items() if s.csharp_dir is not None}
    assert csharp
    for key, spec in csharp.items():
        assert spec.base_key in STRATEGIES, key
        assert STRATEGIES[spec.base_key].csharp_dir is None, f"{key}: predloha má byť Python stratégia"
        assert spec.public()["base_key"] == spec.base_key
    # kópia EOD dedí predlohu od svojho `…net`
    assert STRATEGIES["ibsentryneteod"].base_key == STRATEGIES["ibsentrynet"].base_key == "ibsentry"
    assert all(s.base_key is None for s in STRATEGIES.values() if s.csharp_dir is None)

    from tester.webapp.api import catalog

    zdroj = Path(catalog.__file__).read_text(encoding="utf-8")
    assert 'endswith("eod")' not in zdroj and 'endswith("net")' not in zdroj
    js = (JS_DIR / "settings.js").read_text(encoding="utf-8")
    assert "base_key" in js and "/net$/" not in js and "/eod$/" not in js


def test_kazda_python_strategia_ma_vo_webapp_trh_a_typ():
    """`demo_breakout` bola jediná stratégia bez riadku v `STRATEGIA_TRH_TYP` — končila v OSTATNÉ."""
    js = (JS_DIR / "settings.js").read_text(encoding="utf-8")
    blok = js[js.index("const STRATEGIA_TRH_TYP = {"):js.index("const NOVE_STRATEGIE")]
    zaradene = set(re.findall(r"(\w+): \[\"", blok))
    chyba = sorted(k for k, s in STRATEGIES.items() if s.csharp_dir is None and k not in zaradene)
    assert not chyba, f"bez trhu a typu v settings.js: {chyba}"


def test_default_strategie_je_jedna_konstanta():
    """`"ibs"` ako default bol rozpísaný po celom kóde webapp; teraz je to `DEFAULT_STRATEGY` z jadra
    (v skriptoch jedna rovnomenná konštanta v core.js)."""
    vynimky = {"LEGACY_STRATEGY"}     # behy a profily spred registry — iný význam než default
    zle = []
    for p in sorted(WEBAPP.rglob("*.py")):
        for n, riadok in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            kod = riadok.split("#", 1)[0]
            if '"ibs"' in kod and not any(v in kod for v in vynimky):
                zle.append(f"{p.relative_to(WEBAPP)}:{n}")
    assert not zle, zle

    core = (JS_DIR / "core.js").read_text(encoding="utf-8")
    m = re.search(r'^const DEFAULT_STRATEGY = "(\w+)";$', core, re.M)
    assert m and m.group(1) == DEFAULT_STRATEGY
    for p in sorted(JS_DIR.glob("*.js")):
        text = p.read_text(encoding="utf-8")
        assert not re.search(r'\|\|\s*"ibs"|strategy:\s*"ibs"', text), p.name


def test_jeden_spolocny_poller_na_stranke():
    """Fronta, mriežka, hyperopt aj matica idú cez `makePoller` (pauza po chybe rastie, 404 končí, chybu
    vidno) — vlastné reťaze `setTimeout(pollX, …)` bežali navždy aj proti zmazanému celku (N-FE-4)."""
    core = (JS_DIR / "core.js").read_text(encoding="utf-8")
    assert "function makePoller(opts)" in core and "e.status === 404" in core and "err.status = r.status" in core
    for meno, funkcia in (("queue_hub.js", "pollQueue"), ("sweep.js", "pollSweep"),
                          ("hyperopt.js", "pollHyper"), ("matrix.js", "pollMatrix")):
        text = (JS_DIR / meno).read_text(encoding="utf-8")
        assert "makePoller(" in text, meno
        assert not re.search(rf"setTimeout\(\s*{funkcia}\b", text), meno
    # prázdna fronta sa pýta ďalej (beh z CLI alebo hubu), len redšie
    assert re.search(r"makePoller\(\{\s*interval: 2000, idle: 10000", (JS_DIR / "queue_hub.js").read_text(encoding="utf-8"))
    # graf Live sa po udalostiach zo streamu kreslí cez zlučovač, nie pri každej správe (N-FE-5)
    live = (JS_DIR / "live.js").read_text(encoding="utf-8")
    zaciatok = live.index("async function liveApplyRows(")
    telo = live[zaciatok:live.index("\n}\n", zaciatok)]
    assert "liveChartSoon()" in telo and "renderLiveChart(" not in telo


# --------------------------------------------------------------------------- #
# M-HUB-9: zrkadlo po resete živej DB hubu
# --------------------------------------------------------------------------- #

INSTANCE = "mt5_5012345-Demo_NAS100_3m_ibsnet"


def _ev(seq: int, t0: int = 1_790_000_000_000) -> dict:
    return {"seq": seq, "t": t0 + seq, "k": "note", "text": f"n{seq}", "level": "info"}


def _mirror(tmp_path: Path, transport, clock):
    from tester.webapp.api.live import LiveMirror

    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    return LiveMirror(tmp_path / "mirror.sqlite", tmp_path / "mirror_cursor.json",
                      local_cursor=tmp_path / "cursor_webapp.json",
                      hub_factory=lambda: (cfg, transport), reader_factory=lambda p: None, clock=clock)


def test_zrkadlo_po_resete_databazy_hubu_zacne_odznova(tmp_path: Path):
    """Kurzor zrkadla je `rowid` hubu a kľúčoval sa len adresou: po novej databáze udalostí na hube čakalo
    zrkadlo na `id > starý kurzor` a ticho stálo."""
    from tester.tests.test_live_spool import FakeTransport
    from tester.webapp.api.live import RESET_CHECK_SECONDS
    from tradebot.live.store import LiveStore

    cas = [1000.0]
    hub = LiveStore(tmp_path / "hub.sqlite")
    t = FakeTransport(hub)
    m = _mirror(tmp_path, t, lambda: cas[0])
    hub.ingest("trade-pc", INSTANCE, "s-stara", [_ev(i) for i in range(1, 9)])
    m.tick()
    assert m.hub_cursor == 8 and m.hub_resets == 0
    ulozene = json.loads((tmp_path / "mirror_cursor.json").read_text(encoding="utf-8"))
    assert ulozene["cursor"] == 8 and ulozene["anchor"][:3] == [INSTANCE, "s-stara", 8]

    # ten istý hub, nič nové: kontrola identity nič nezhodí
    cas[0] += RESET_CHECK_SECONDS + 1
    m.tick()
    assert m.hub_cursor == 8 and m.hub_resets == 0 and m.last_error is None

    # hub dostal novú databázu (menej riadkov, než zrkadlo už videlo)
    t.store = LiveStore(tmp_path / "hub2.sqlite")
    t.store.ingest("trade-pc", INSTANCE, "s-nova", [_ev(i, 1_800_000_000_000) for i in range(1, 4)])
    m.tick()                                    # do ďalšej kontroly ešte stojí…
    assert m.hub_cursor == 8
    cas[0] += RESET_CHECK_SECONDS + 1
    m.tick()                                    # …potom reset zistí a dotiahne novú databázu od začiatku
    assert m.hub_resets == 1 and m.hub_cursor == 3 and m.status()["hub_resets"] == 1
    relacie = {s["session"] for s in m.store.sessions(INSTANCE)}
    assert relacie == {"s-stara", "s-nova"}     # čo zrkadlo už malo, ostáva; nové pribudlo


def test_zrkadlo_pozna_inu_databazu_aj_ked_uz_prerastla_kurzor(tmp_path: Path):
    """Nová databáza hubu, ktorá má už viac riadkov než starý kurzor: `id > kurzor` niečo vracia, takže
    zrkadlo beží — ale riadky 1..kurzor novej databázy by nikdy nevidelo. Pozná to podľa riadku na kurzore."""
    from tester.tests.test_live_spool import FakeTransport
    from tester.webapp.api.live import RESET_CHECK_SECONDS
    from tradebot.live.store import LiveStore

    cas = [1000.0]
    t = FakeTransport(LiveStore(tmp_path / "hub.sqlite"))
    t.store.ingest("trade-pc", INSTANCE, "s-stara", [_ev(i) for i in range(1, 4)])
    m = _mirror(tmp_path, t, lambda: cas[0])
    m.tick()
    assert m.hub_cursor == 3

    t.store = LiveStore(tmp_path / "hub2.sqlite")
    t.store.ingest("trade-pc", INSTANCE, "s-nova", [_ev(i, 1_800_000_000_000) for i in range(1, 11)])
    cas[0] += RESET_CHECK_SECONDS + 1
    m.tick()
    assert m.hub_resets == 1 and m.hub_cursor == 10
    assert len(m.store.events(INSTANCE, session="s-nova")) == 10      # aj prvé tri riadky novej databázy


def test_kurzor_zrkadla_spred_kotiev_sa_len_doplni(tmp_path: Path):
    """Súbor kurzora zo starej verzie (bez `anchor`) nesmie spustiť zbytočné sťahovanie celého hubu."""
    from tester.tests.test_live_spool import FakeTransport
    from tradebot.live.store import LiveStore

    t = FakeTransport(LiveStore(tmp_path / "hub.sqlite"))
    t.store.ingest("trade-pc", INSTANCE, "s1", [_ev(i) for i in range(1, 6)])
    (tmp_path / "mirror_cursor.json").write_text(
        json.dumps({"hub_url": "http://hub.test:8790", "cursor": 5}), encoding="utf-8")
    m = _mirror(tmp_path, t, lambda: 1000.0)
    m.tick()
    assert m.hub_resets == 0 and m.hub_cursor == 5 and m.hub_anchor[:3] == [INSTANCE, "s1", 5]


# --------------------------------------------------------------------------- #
# N-WEB-4 (zvyšok): log behu a obnova z archívu
# --------------------------------------------------------------------------- #


def test_log_behu_sa_zapisuje_atomicky(tmp_path: Path, monkeypatch):
    from tester.webapp import store as store_mod

    volane = []
    povodny = store_mod.write_text_atomic
    monkeypatch.setattr(store_mod, "write_text_atomic", lambda p, t, **kw: (volane.append(Path(p).name), povodny(p, t, **kw)))
    store = RunStore(tmp_path / "runs")
    rec = _record(1)
    store.save(rec, trades=[], log="riadok 1\nriadok 2\n")
    assert volane == ["log.txt"]
    d = store.root / rec["id"]
    assert (d / "log.txt").read_bytes() == b"riadok 1\nriadok 2\n"
    assert not [p.name for p in d.iterdir() if p.name.endswith(".tmp")]


def test_obnova_z_archivu_nenecha_polovicny_beh(tmp_path: Path, monkeypatch):
    """`restore` písal `run.json` prvý a neatomicky: pád uprostred nechal v histórii beh bez obchodov alebo
    s rozbitým JSON. Teraz ide `run.json` posledný — kým nie je, beh v histórii nie je."""
    from tester.webapp import archive

    store = RunStore(tmp_path / "runs")
    rec = _record(1)
    store.save(rec, trades=[{"pnl": 1.0, "point_value": 1.0}], log="log\n")
    povodne = {p.name: p.read_bytes() for p in (store.root / rec["id"]).iterdir()}
    root = tmp_path / "archive"
    plan = archive.plan(store, store.all(), root=root)
    assert archive.apply(store, plan, root=root, log=lambda s: None)["archived"] == 1
    assert store.get(rec["id"]) is None

    def spadni(*a, **kw):
        raise OSError("disk plný")

    monkeypatch.setattr(archive, "write_json_atomic", spadni)
    assert archive.restore(store, rec["id"], root=root) is None      # chybu zápisu `restore` hlási ako None
    assert not (store.root / rec["id"] / "run.json").exists()
    assert store.get(rec["id"]) is None and rec["id"] not in [r["id"] for r in store.all()]

    monkeypatch.undo()
    assert archive.restore(store, rec["id"], root=root) is not None
    assert {p.name: p.read_bytes() for p in (store.root / rec["id"]).iterdir()} == povodne


# --------------------------------------------------------------------------- #
# N-WEB-8: odhad času a značky celkov z indexu
# --------------------------------------------------------------------------- #


def _timing_store(tmp_path: Path) -> RunStore:
    store = RunStore(tmp_path / "runs")
    for i in range(1, 40):
        extra: dict = {}
        if i % 7 == 0:
            extra["hyperopt"] = {"knobs": {"rrRatio": "2:8:0.5"}, "epochs": 50, "epochs_done": 40 + i}
        if i % 4 == 0:
            extra["ai"] = {"enabled": True}
        rec = _record(i, **extra)
        if i % 6 == 0:
            rec["result"].pop("duration_s")
        store.save(rec, trades=[], log="")
    return store


def test_odhad_casu_z_indexu_je_ten_isty_ako_z_celej_historie(tmp_path: Path):
    """Odhad času pre hub čítal pri každom zadaní celú históriu (`store.all()`); `timing_history()` berie
    z indexu len hotové behy s trvaním a len polia, ktoré odhad číta — výsledok musí byť rovnaký."""
    from tester.hub import protocol as P

    store = _timing_store(tmp_path)
    vsetko = store.all()
    for settings in (BT, {**BT, "engine": "multicharts"}, {**BT, "timeframe_detail": ""},
                     {**BT, "ai": {"enabled": True}}, HO, {**HO, "engine": "multicharts"},
                     {**HO, "hyperopt": {**HO["hyperopt"], "mode": "walkforward"}}):
        chcem = P.estimate_seconds(settings, vsetko, cores=4)
        assert P.estimate_seconds(settings, store.timing_history(), cores=4) == pytest.approx(chcem), settings
    assert len(store.timing_history()) < len(vsetko)          # zlyhané a behy bez trvania v ňom nie sú
    assert all(set(r) == {"id", "status", "result", "settings"} for r in store.timing_history())

    # bez indexu to isté zo súborov
    store.index.ok = False
    store.index._failed_at = 0.0
    assert not store.index.sync()
    for settings in (BT, HO):
        assert P.estimate_seconds(settings, store.timing_history(), cores=4) == pytest.approx(
            P.estimate_seconds(settings, vsetko, cores=4))


def _scan_tagged(store: RunStore, kind: str, batch_id: str | None) -> list[str]:
    """Definícia správania: prehľadanie súborov."""
    return [r["id"] for r in store._scan()
            if ((r.get("settings") or {}).get(kind) or {}).get("id")
            and (batch_id is None or r["settings"][kind]["id"] == batch_id)]


def test_znacky_celkov_z_indexu_su_to_iste_co_zo_suborov(tmp_path: Path):
    """Stĺpce `batch_kind`/`batch_id`: dopyt na behy celku už neprechádza JSON celej histórie, ale musí
    vrátiť presne to isté — aj pre beh s dvoma značkami (v stĺpci je len prvá)."""
    store = RunStore(tmp_path / "runs")
    for i in range(1, 25):
        extra: dict = {}
        if i % 3 == 0:
            extra["sweep"] = {"id": f"sw{i % 2}", "goal": "break_even"}
        if i % 4 == 0:
            extra["matrix"] = {"id": "MxA"}                # i = 12, 24 majú sweep aj matrix
        if i % 5 == 0:
            extra["hyperopt_run"] = {"id": "20260901-120000-abcdef"}
        if i == 7:
            extra["plateau"] = {"id": ""}                  # prázdna značka nie je značka
        store.save(_record(i, **extra), trades=[], log="")

    conn = store.index._db()
    stlpce = dict(conn.execute("SELECT id, batch_kind FROM runs").fetchall())
    assert sum(1 for v in stlpce.values() if v) == len([i for i in range(1, 25) if i % 3 == 0 or i % 4 == 0 or i % 5 == 0])
    assert "runs_batch" in {r[1] for r in conn.execute("PRAGMA index_list(runs)")}

    for kind in ("sweep", "matrix", "hyperopt_run", "plateau"):
        for batch_id in (None, "sw0", "sw1", "MxA", "mxa", "20260901-120000-abcdef", "nie-je"):
            z_indexu = [r["id"] for r in store._tagged_runs(kind, batch_id)]
            assert z_indexu == _scan_tagged(store, kind, batch_id), (kind, batch_id)


def test_stary_index_bez_stlpcov_celku_sa_postavi_znova(tmp_path: Path):
    """Index so schémou 1 (bez `batch_kind`) sa pri otvorení zahodí a postaví zo súborov — je odvodený."""
    import sqlite3

    from tester.webapp import index as index_mod

    store = RunStore(tmp_path / "runs")
    for i in range(1, 6):
        store.save(_record(i, sweep={"id": "sw"} if i % 2 else None), trades=[], log="")
    ocakavane = [r["id"] for r in store.all()]
    store.index.close()

    # podvrhni starú schému: tabuľka bez nových stĺpcov, verzia 1
    conn = sqlite3.connect(store.index.path)
    conn.executescript("DROP TABLE runs; CREATE TABLE runs (id TEXT PRIMARY KEY, mtime INTEGER NOT NULL, "
                       "size INTEGER NOT NULL, slim TEXT NOT NULL); UPDATE meta SET v = '1' WHERE k = 'schema';")
    conn.commit()
    conn.close()

    novy = RunStore(tmp_path / "runs")
    assert index_mod.SCHEMA >= 2
    assert [r["id"] for r in novy.all()] == ocakavane and novy.index.ok
    assert [r["id"] for r in novy.tagged("sweep", "sw")] == _scan_tagged(novy, "sweep", "sw")


# --------------------------------------------------------------------------- #
# N-WEB-12: GET histórie analytík nezapisuje
# --------------------------------------------------------------------------- #


def test_get_historie_analytik_nic_nezapisuje(tmp_path: Path, monkeypatch):
    """`GET /api/analytics/history` dopisoval konfiguráciu do až 500 súborov v `tester/analytics/` (idú do
    gitu) a záznamu, ktorého behy už v histórii neboli, ju vymazal. Teraz ju len doplní do odpovede."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import tester.webapp.app as app_mod
    from tester.webapp.anstore import AnalyticsStore
    from tester.webapp.runner import BacktestRunner

    an_dir = tmp_path / "analytics"
    monkeypatch.setattr(app_mod, "AnalyticsStore", lambda: AnalyticsStore(an_dir))
    store = RunStore(tmp_path / "runs")
    c = TestClient(app_mod.create_app(store, BacktestRunner(store)))
    rec = _record(1)
    store.save(rec, trades=[], log="")
    anstore = AnalyticsStore(an_dir)
    report = {"strategy": "ibs", "headline": "h", "trades": 10, "break_even_pct": 0.1, "winrate": 40.0,
              "pairs": [BT["pair"]], "runs": [{"id": rec["id"]}]}
    stary = anstore.save(report, strategy="ibs")                       # starší záznam: bez konfigurácie
    sirota = anstore.save({**report, "trades": 11, "runs": [{"id": "20200101-000000-ffffff"}]}, strategy="ibs",
                          config_key="kedysi", market="BTC|3m")        # jeho beh už v histórii nie je

    def obsah() -> dict[str, bytes]:
        return {p.name: p.read_bytes() for p in an_dir.glob("*.json")}

    pred = obsah()
    items = {x["id"]: x for x in c.get("/api/analytics/history?strategy=ibs").json()["items"]}
    assert obsah() == pred, "GET zapísal do tester/analytics/"
    assert items[stary["id"]]["config_key"] and items[stary["id"]]["timeranges"] == [BT["timerange"]]
    assert items[sirota["id"]]["config_key"] == "kedysi" and items[sirota["id"]]["market"] == "BTC|3m"

    # filter podľa dopočítanej konfigurácie funguje aj bez zápisu
    kluc = items[stary["id"]]["config_key"]
    filtrovane = c.get("/api/analytics/history", params={"strategy": "ibs", "config_key": kluc}).json()["items"]
    assert [x["id"] for x in filtrovane] == [stary["id"]]
    assert c.get("/api/analytics/history", params={"strategy": "ibs", "limit": 1}).json()["items"].__len__() == 1
    assert obsah() == pred


# --------------------------------------------------------------------------- #
# N-WEB-13, N-WEB-16: sklad behov
# --------------------------------------------------------------------------- #


def test_sklad_necita_mimo_adresara_behov(tmp_path: Path):
    """`get`/`trades`/`log` nekontrolovali tvar `run_id` — `..\\..\\x` z URL prečítalo cudzí súbor."""
    store = RunStore(tmp_path / "runs")
    cudzi = tmp_path / "cudzi"
    cudzi.mkdir()
    (cudzi / "run.json").write_text(json.dumps({"id": "x", "settings": {}}), encoding="utf-8")
    (cudzi / "trades.json").write_text("[{\"pnl\": 1, \"point_value\": 1}]", encoding="utf-8")
    (cudzi / "log.txt").write_text("tajné", encoding="utf-8")
    assert (store.root / ".." / "cudzi" / "run.json").exists()
    for zly in ("../cudzi", "..\\cudzi", "..", "", "20260901-120000-abcdef/../../cudzi"):
        assert store.get(zly) is None, zly
        assert store.trades(zly) == [] and store.log(zly) == "", zly
    rec = _record(1)
    store.save(rec, trades=[{"pnl": 1.0, "point_value": 1.0}], log="ok")
    assert store.get(rec["id"])["id"] == rec["id"] and store.trades(rec["id"]) and store.log(rec["id"]) == "ok"


def test_cache_behov_znesie_subezne_citanie(tmp_path: Path, monkeypatch):
    """Nezamknutý `OrderedDict`: `move_to_end` kľúča, ktorý iné vlákno práve vyhodilo, bol KeyError (500)."""
    from tester.webapp import store as store_mod

    monkeypatch.setattr(store_mod, "CACHE_RUNS", 3)
    store = RunStore(tmp_path / "runs")
    ids = []
    for i in range(1, 13):
        rec = _record(i)
        store.save(rec, trades=[], log="")
        ids.append(rec["id"])
    chyby: list[BaseException] = []

    def citaj(posun: int) -> None:
        try:
            for k in range(400):
                assert store.get(ids[(k * (posun + 1) + posun) % len(ids)]) is not None
        except BaseException as exc:  # noqa: BLE001 - test zbiera čokoľvek z vlákna
            chyby.append(exc)

    vlakna = [threading.Thread(target=citaj, args=(n,)) for n in range(8)]
    for t in vlakna:
        t.start()
    for t in vlakna:
        t.join(30)
    assert not chyby and len(store._cache) <= 3


def test_monte_carlo_cache_pocita_raz_a_drzi_strop(monkeypatch):
    from tester.webapp.api import common

    volania = []
    monkeypatch.setattr(common.montecarlo, "analyze", lambda trades, **o: (volania.append(o), {"n": len(volania)})[1])
    monkeypatch.setattr(common, "_MC_CACHE_MAX", 2)
    common._MC_CACHE.clear()
    a = common.montecarlo_cached("r1", [], {"x": 1})
    assert common.montecarlo_cached("r1", [], {"x": 1}) is a and len(volania) == 1 and a["run_id"] == "r1"
    common.montecarlo_cached("r2", [], {"x": 1})
    common.montecarlo_cached("r3", [], {"x": 1})
    assert len(common._MC_CACHE) == 2 and ("r1", 1) not in common._MC_CACHE
    common._MC_CACHE.clear()


# --------------------------------------------------------------------------- #
# N-WEB-17: git
# --------------------------------------------------------------------------- #


def test_git_ma_casovy_limit_a_vrati_chybu_nie_vynimku(monkeypatch):
    from tester.webapp import gitsync

    videne = {}

    def fake_run(cmd, **kw):
        videne.update(kw)
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(gitsync.subprocess, "run", fake_run)
    r = gitsync._git("fetch", "origin", "main")
    assert videne["timeout"] == gitsync.GIT_TIMEOUT
    assert r.returncode != 0 and "neodpovedal" in r.stderr and r.args == ["git", "fetch", "origin", "main"]
    assert "$ git fetch origin main" in gitsync._out(r)


def test_git_status_nerobi_fetch_pri_kazdom_volani(monkeypatch):
    from tester.webapp import gitsync

    calls = []

    def fake_git(*args, check=False):
        calls.append(args)
        return SimpleNamespace(args=("git", *args), stdout="", stderr="", returncode=1)

    monkeypatch.setattr(gitsync, "_git", fake_git)
    monkeypatch.setattr(gitsync, "_last_fetch", {})
    cas = [100.0]
    monkeypatch.setattr(gitsync.time, "monotonic", lambda: cas[0])
    for _ in range(3):
        gitsync.status()
    assert sum(1 for a in calls if a[0] == "fetch") == 1
    cas[0] += gitsync.FETCH_EVERY + 1
    gitsync.status()
    assert sum(1 for a in calls if a[0] == "fetch") == 2


def test_dva_pushe_naraz_sa_nepobiju(monkeypatch):
    """Dva Push/Pull naraz končili na `index.lock`; druhý teraz hneď povie, že iný beží."""
    from tester.webapp import gitsync

    monkeypatch.setattr(gitsync, "status", lambda: {})
    monkeypatch.setattr(gitsync, "_push", lambda *a: pytest.fail("druhý push nemal bežať"))
    monkeypatch.setattr(gitsync, "_pull", lambda: pytest.fail("pull počas pushu nemal bežať"))
    assert gitsync._WRITE_LOCK.acquire(blocking=False)
    try:
        assert gitsync.push() == {"ok": False, "output": "Iný Pull alebo Push práve beží — počkaj, kým dobehne."}
        assert gitsync.pull()["ok"] is False
    finally:
        gitsync._WRITE_LOCK.release()
    monkeypatch.setattr(gitsync, "_pull", lambda: {"ok": True})
    assert gitsync.pull() == {"ok": True} and not gitsync._WRITE_LOCK.locked()


# --------------------------------------------------------------------------- #
# N-WEB-18: čakanie na pracovné procesy C#
# --------------------------------------------------------------------------- #


def test_cakanie_na_pracovny_proces_ma_limit():
    """`POST /api/native/backtests` čakal na voľný pracovný proces bez konca (kým ich držal hyperopt)."""
    from tester import native

    pool = native.WorkerPool(limit=1)
    pool._busy = 1                                    # jediný proces je požičaný
    with pytest.raises(native.PoolBusy):
        pool.acquire(1, timeout=0.05)
    assert pool.stats()["busy"] == 1                  # neúspešné čakanie nič nepožičalo

    # uvoľnenie počas čakania čakajúceho zobudí
    pool._idle.append(SimpleNamespace(last_used=native.time.time(), alive=True, close=lambda: None))
    threading.Timer(0.05, lambda: pool.release([], failed=1)).start()
    dostal = pool.acquire(1, timeout=5)
    assert len(dostal) == 1 and pool.stats() == {"limit": 1, "busy": 1, "idle": 0}


# --------------------------------------------------------------------------- #
# dokumenty meraní v okne hodnotenia
# --------------------------------------------------------------------------- #


def test_dokumenty_merani_sa_citaju_len_ked_sa_zmenili(tmp_path: Path, monkeypatch):
    """Okno hodnotenia stratégie čítalo pri každom otvorení všetky merania z `docs/merania/`."""
    import os

    from tester.webapp.api import catalog_report as cr

    merania = tmp_path / "merania"
    merania.mkdir()
    a = merania / "2026-01-01_a.md"
    a.write_text("# Meranie A\n\n`python -m tester.webapp.cli run --strategy ibs`\n", encoding="utf-8")
    (merania / "2026-01-02_b.md").write_text("# Meranie B\n\no stratégii `orb`\n", encoding="utf-8")
    monkeypatch.setattr(cr, "MERANIA_DIR", merania)
    monkeypatch.setattr(cr, "_DOC_CACHE", {})

    citania: list[str] = []
    povodne = Path.read_text

    def pocitaj(self, *args, **kw):
        if self.parent == merania:
            citania.append(self.name)
        return povodne(self, *args, **kw)

    monkeypatch.setattr(Path, "read_text", pocitaj)
    prve = [d for d in cr.strategy_docs("ibs") if d["kind"] == "meranie"]
    assert prve == [{"id": "m/2026-01-01_a.md", "title": "Meranie A", "kind": "meranie"}]
    assert sorted(citania) == ["2026-01-01_a.md", "2026-01-02_b.md"]
    assert [d for d in cr.strategy_docs("ibs") if d["kind"] == "meranie"] == prve
    assert len(citania) == 2                          # druhé otvorenie nič nečítalo

    a.write_text("# Meranie A2\n\n`ibs` znova\n", encoding="utf-8")
    st = a.stat()
    os.utime(a, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    druhe = [d for d in cr.strategy_docs("ibs") if d["kind"] == "meranie"]
    assert druhe[0]["title"] == "Meranie A2" and citania.count("2026-01-01_a.md") == 2
