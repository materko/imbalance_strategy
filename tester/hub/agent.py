"""Agent: hlási sa hubu, počíta, čo mu pridelí, a vyzdvihuje výsledky toho, čo sám poslal.

    agent = HubAgent(cfg, runner, store)   # runner = BacktestRunner webapp alebo vlastný
    agent.start()                          # dve vlákna: heartbeat (`tick`) a pomalá práca (`work`)

**Dve vlákna, nie jedno.** Heartbeat musí odísť každých `heartbeat_seconds` (predvolene 3 s;
hub v odpovedi pošle svoj interval a agent sa mu prispôsobí), inak hub po 45 sekundách
vyhlási agenta za mŕtveho a jeho výpočty dá inému. Zip s výsledkom, sťahovanie
výsledku a hlavne `git pull` s poskladaním dát po ňom trvajú aj minúty — preto ich robí
druhé vlákno (`work()`) a tick len povie, že je čo robiť. Bez vlákien (testy, `tick()`
naholo) sa pomalá práca spraví na konci ticku.

Jeden `tick()`:

1. **heartbeat** — čo počíta, ako ďaleko to je a koľko asi ostáva (`protocol`), plus
   lokálna záťaž bez výpočtov hubu (aby ich hub nepočítal dvakrát),
2. z odpovede **vezme** pridelené výpočty do lokálneho runnera a **zruší** tie, ktoré hub
   ruší — oboje je rýchle (runner beh len zaradí do fronty).

Jedno kolo `work()`:

1. **odovzdá** hotové výpočty — zabalí adresáre behov (u hyperoptu aj overovacie behy
   víťaza) a pošle ich hubu; kým sa upload nepodarí, skúša to znova,
2. **pullne** kód, keď naň čaká pridelený výpočet (viď nižšie),
3. **vyzdvihne** výsledky výpočtov, ktoré tento agent sám zadal (zip do vlastnej histórie,
   `ack` hubu),
4. **pošle live telemetriu** (`_ship_live`, docs/LIVE.md) — vo **vlastnom vlákne** (`_ship_loop`),
   nie v `work()`: keď je na stroji spool NinjaTradera alebo MT5 (`tradebot.live.default_roots`),
   `LiveShipper` ho odošle na hub a kurzor posunie až po 200; korene sa preverujú každú minútu, nech
   sa platforma nainštalovaná neskôr chytí. Grafové dáta (po reštarte platforiem desaťtisíce udalostí
   prehratej histórie, kolo `pump` aj 40 s) tak nezdržia riadiace kroky nižšie — nasadenia, nový kód
   a pull. Aby bar nečakal na heartbeat, **ľahké vlákno** (`_spool_watch_loop`) každú sekundu pozrie
   veľkosti súborov spoolu (`SpoolReader.status()`, len `stat`) a keď narástli, zobudí odosielanie
   hneď (`_ship`); heartbeat ostáva ako poistka. Bez vlákien (testy) posiela `work()` sám,
5. **zosúladí nasadenia** (`_apply_live`, docs/LIVE.md fáza 2b): heartbeat prinesie v `live`
   účty a nasadenia tohto agenta, `Reconciler` s drivermi platforiem (`tradebot.live.drivers`)
   ich zapíše na disk platformy a spustí terminál; čo sa podarilo, ide v `live.applied`
   ďalšieho heartbeatu. Starý hub bez `live` = nič,
6. **nasadí nový kód na platformy** (`_update_code`, docs/LIVE.md fáza 2c): keď heartbeat prinesie
   `live.code_target` (commit, `force`), `CodeUpdater` (`tradebot.live.update`) pullne chýbajúci commit,
   overí bránu (všetky nasadenia v pauze/flatten a bez pozície, inak `blocked`) a zavolá
   `install_code` každého drivera; výsledok ide v `live.code_update` (+ `live.installed` = markery
   platforiem) ďalšieho heartbeatu a hub cieľ zmaže, keď je `ok`. Kým sa kód mení, agent hlási
   `updating` (hub mu nič nepridelí); zmena HEAD = `needs_restart` (headless sa reštartuje sám, webapp
   to ukáže). Blokovaný cieľ sa skúša znova každú minútu, chybný každých 5 minút.

**Pluginy agenta** (docs/HUB.md, „Pluginy agenta“; `tester.hub.agent_plugins`): vlastný kód v procese
agenta, každý vo vlastnom vlákne, agent ho nepozná menom — dnes `telegram` (docs/LIVE.md, „Telegram“):
správy zo spoolu (vlastný kurzor, nezávisle od hubu) a príkazy (`/pause`, `/resume`, `/flatten`), ktoré
zapíšu control súbor hneď a prepnutie držia ako prekrytie požadovaného stavu (`_with_overrides`), kým ho
hub v nasadení neprevezme (`live.overrides` v heartbeate). Nový kód **len v adresári pluginu** načíta
pomalé vlákno za behu (`_update_plugins`, `PluginUpdater`): z disku vždy, na obchodnom stroji si ho aj
sám pullne — bez brány nasadení a bez reštartu agenta.

**Rola stroja** (`cfg.role`, docs/HUB.md „Druhy agentov“): obchodný stroj (`live`) výpočty
nikdy neberie — `accept` drží `false`, pokyn hubu na zapnutie ignoruje a pridelený výpočet
(starý hub) nespustí. Rolu aj druh procesu (`kind`: `webapp` / `headless`) hlási pri registrácii
a v heartbeate, aby hub vedel, komu nič neposielať, a stav ukázal, čo je ktorý stroj.

Čo agent počíta a čo poslal, si drží v `tester/agent_state.json` (`config.AgentState`):
po reštarte procesu bežiace behy ďalej hlási (runner ich už nemá, ale história áno) a
čakajúce výsledky si vyzdvihne.

**Výpadok hubu.** Výpočet, ktorý už agent prijal, dopočíta sám — lokálny runner o hube
nevie a nepotrebuje ho (platí aj pre webapp agenta). Hub je potrebný len na odovzdanie:
kým sa výsledok neodovzdá, záznam ostáva v `computing` a agent to skúša znova v každom
kole `work()`, aj po reštarte. Keď hub vstane, výsledok odíde v prvom kole — na registrácii
ani heartbeate to nezávisí. Zlyhanie jedného odovzdania neprerušuje ostatné. Keď hub medzitým výpočet pridelil inému agentovi (agent sa mu odmlčal), neskorý
výsledok aj tak prijme (`state.result`) a zadávateľovi ho vráti; keď ho hub nepozná vôbec
(stratený `state.json`), ide záznam do `undelivered` a behy ostávajú v histórii agenta.

**Verzia kódu.** Výpočet nesie commit zadávateľa (`job.version`). Agent ho pred prijatím
overí (`gitcode.has_version`); keď ho nemá, počká, kým dobehne, čo práve počíta, a zadá
pomalému vláknu `git pull` (origin main). Kým sa ťahá, hlási `updating` a nové výpočty
neberie — hub mu ich dovtedy neposiela a kód sa nemení pod rozbehnutým behom. Keď commit
nie je ani po pulle (zadávateľ ho nepushol), výpočet zlyhá s jasnou chybou. Po pulle je kód v bežiacom procese starý:
headless agent sa reštartuje sám (`restart_on_pull`), webapp to hlási v `needs_restart`
a v `/api/hub` — Freqtrade beží v podprocese, takže samotný beh už ide na novom kóde.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import AGENT_CONFIG, LIVE_APPLY_STATE, LIVE_CURSOR

from . import config as agent_config
from . import delivered, gitcode
from . import protocol as P
from .client import HubError, HubHttp, retry_delay
from .config import AgentConfig, AgentState, load_state, save_state
from .transfer import pack_runs, unpack_runs

__all__ = ["HubAgent"]

log = logging.getLogger(__name__)

#: Hotový **hyperopt** sa odovzdá až po toľkých tickoch v konečnom stave — overovacie behy
#: víťaza si zaraďuje tesne po tom, čo nastaví `done`, a jeden tick medzi tým to bezpečne
#: preklenie. Backtest nič nezaraďuje, ten ide hneď.
SETTLE_TICKS = 2

#: Strop na čas behu, keď ho zadávateľ neurčil: násobok odhadu, najmenej 10 minút.
#: Zaseknutý Freqtrade by inak držal výpočet v `running` donekonečna.
MAX_RUNTIME_FACTOR = 3.0
MIN_MAX_SECONDS = 600.0

#: Ako často sa pomalé vlákno pozrie, či je preň práca (aj bez pokynu z ticku).
WORK_POLL_SECONDS = 2.0
#: Ako dlho čaká agent v kontajneri na pull, ktorý na pokyn ⟳ robí hostiteľ (`TRADEBOT_HUB_PULL=host`).
HOST_PULL_TIMEOUT = 180.0

#: Koľkokrát sa výsledok skúsi odovzdať hubu, ktorý výpočet nepozná (404), než sa odloží
#: do `undelivered`. Hub po reštarte môže mať stav ešte nenačítaný — pár tickov mu dáme.
DELIVER_404_TRIES = 5

#: Ako často sa mažú odovzdané behy staršie než `delivered.KEEP_DAYS` (sekundy).
DELIVERED_PURGE_SECONDS = 3600.0

#: Ako často sa znova hľadajú korene live spoolu (platforma nainštalovaná po štarte agenta).
LIVE_ROOTS_RECHECK_SECONDS = 60.0

#: Ako často ľahké vlákno pozrie, či spool narástol (len `stat` súborov) — po raste zobudí
#: pomalé vlákno hneď, takže bar odíde na hub do ~1 s, nie až s heartbeatom.
SPOOL_WATCH_SECONDS = 1.0

#: Rozumné hranice pre `heartbeat_seconds`, ktoré pošle hub — mimo nich sa nechá config.
HEARTBEAT_MIN, HEARTBEAT_MAX = 1, 600

#: Ako často obchodný stroj pozrie `origin`, či nie je nový kód len pre pluginy agenta (env
#: `TRADEBOT_AGENT_PLUGIN_UPDATE` = minúty, 0 = vypnuté).
PLUGIN_UPDATE_SECONDS = 300.0

#: Heartbeat (a registrácia) čaká na odpoveď hubu najviac toľko — s nadviazaním spojenia (3 pokusy po
#: `HEARTBEAT_CONNECT_TIMEOUT`) sa jeden pokus zmestí hlboko pod `agent_timeout` hubu (45 s). So spoločným
#: 30 s timeoutom a 3×5 s na spojenie mohol jediný zaseknutý heartbeat limit presiahnuť sám (audit M-HUB-8).
HEARTBEAT_TIMEOUT = 10.0
HEARTBEAT_CONNECT_TIMEOUT = 4.0

#: Koľko najnovších hotových behov sa číta z indexu histórie na odhad času (odhad berie posledných
#: `protocol.HISTORY_WINDOW` podobných) — nie celá história pri každom heartbeate (audit N-WEB-8).
HISTORY_ROWS = 400

#: Vlákna agenta `(atribút, slučka, meno)` — spúšťa ich `start()` a stráži `supervise()` (audit M-HUB-10).
THREADS = (("_thread", "_loop", "hub-agent"), ("_worker", "_work_loop", "hub-agent-work"),
           ("_shipper_thread", "_ship_loop", "hub-agent-ship"), ("_watcher", "_spool_watch_loop", "hub-agent-spool"))

#: Nový kód na stroji (fáza 2c): ako často sa blokovaný / chybný cieľ skúša znova.
CODE_RETRY_BLOCKED = 60.0
CODE_RETRY_ERROR = 300.0


def _migrate_sparse() -> None:
    try:
        from . import sparse
        r = sparse.migrate_legacy()
        if r is not None:
            log.info("hub agent: pravidlá chudého klonu prepnuté na nové cesty (%s)", "ok" if r["ok"] else r["output"])
    except Exception as exc:   # klon bez gitu alebo len na čítanie (Docker) je v poriadku
        log.debug("hub agent: sparse migrácia preskočená: %s", exc)

class TelegramHubViews:
    """Pohľady pluginov hubu pre pluginy agenta (Telegram: 📅 Udalosti …) — vlastné spojenie s krátkym timeoutom,
    aby čakanie na hub nebrzdilo heartbeat ani long-poll príkazov."""

    def __init__(self, hub_url: str, token: str) -> None:
        self.http = HubHttp(hub_url, token, timeout=10.0)

    def views(self) -> list[dict[str, str]]:
        return list(self.http.get("/api/plugins/views") or [])

    def view(self, plugin: str, view: str) -> str:
        return str((self.http.get(f"/api/plugins/{_q(plugin)}/views/{_q(view)}") or {}).get("text") or "")


def _parse_iso(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


class HubAgent:
    def __init__(self, cfg: AgentConfig, runner: Any, store: Any, *, http: HubHttp | None = None,
                 state_path: Path | None = None, config_path: Path | None = None,
                 clock: Callable[[], float] = time.time, version: str = "",
                 live_cursor: Path | None = None, reconciler: Any = None,
                 apply_state: Path | None = None, updater: Any = None, plugins: Any = None,
                 kind: str = "headless") -> None:
        self.cfg = cfg
        #: Druh procesu: `webapp` (agent v Testeri) alebo `headless` (`python -m tester.hub agent`).
        self.kind = kind
        self.runner = runner
        self.store = store
        self.http = http or HubHttp(cfg.hub_url, cfg.token)
        #: Heartbeat a registrácia idú vlastným spojením s krátkym timeoutom (`HEARTBEAT_TIMEOUT`); zipy a dávky
        #: spoolu ostávajú na `self.http` s dlhým.
        self._hb_http = http or HubHttp(cfg.hub_url, cfg.token, timeout=HEARTBEAT_TIMEOUT,
                                        connect_timeout=HEARTBEAT_CONNECT_TIMEOUT)
        self.state_path = state_path
        self.config_path = Path(config_path or AGENT_CONFIG)
        #: Live telemetria (docs/LIVE.md): shipper vznikne, až keď je na stroji spool platformy.
        self.live_cursor = Path(live_cursor or LIVE_CURSOR)
        self._live: Any = None
        self._live_checked: float | None = None
        self._live_error: str | None = None
        #: Odtlačok spoolu (počet súborov, bajty spolu) z posledného pohľadu strážcu.
        self._spool_stamp: tuple[int, int] | None = None
        #: Bajty čakajúce za kurzorom z posledného pohľadu strážcu a kedy to bolo (`time.monotonic`) — heartbeat
        #: ich berie odtiaľ a spool sám neprehľadáva.
        self._spool_pending: tuple[float, int] | None = None
        #: Výpisy adresárov spoolu pre `latest_state` (adresár → čas zmeny a obsah).
        self._live_dirs: dict[str, Any] = {}
        #: Interval heartbeatu, ktorý poslal hub v odpovedi (None = z configu).
        self.hub_heartbeat: int | None = None
        #: Nasadenia z hubu (fáza 2b): reconciler vznikne pri prvom `live` v odpovedi; požadovaný
        #: stav si heartbeat odloží a pomalé vlákno ho aplikuje (`_apply_live`).
        self._reconciler: Any = reconciler
        self._apply_state = Path(apply_state or LIVE_APPLY_STATE)
        self._live_desired: dict[str, Any] | None = None
        self._live_desired_seq = 0
        self._live_applied_seq = 0
        self._live_cache: dict[str, Any] = {}
        self._live_lock = threading.Lock()
        #: Nový kód na stroji (fáza 2c): cieľ z heartbeatu, výsledok poslednej aktualizácie a kedy bola.
        self._updater: Any = updater
        self._code_target: dict[str, Any] | None = None
        self._code_update: dict[str, Any] | None = None
        self._code_attempt: tuple[tuple[Any, ...], float] | None = None
        #: Pluginy agenta (Telegram …): host vznikne v `start()` (`plugins` sa dá podstrčiť — testy),
        #: `PluginUpdater` ich drží na novom kóde bez reštartu.
        self._plugins: Any = plugins
        self._plugin_updater: Any = None
        self._config_mtime = self._config_stamp()
        self.clock = clock
        self.version = version or gitcode.version()
        #: Commit pri štarte procesu — keď sa kód na disku zmení (pull na hostiteľovi,
        #: kontajner), headless agent to spozná a reštartuje sa.
        self.start_version = self.version
        #: Headless agent sa po pulle reštartuje (nový proces = nový kód); webapp nie.
        self.restart_on_pull = False
        self.needs_restart = False
        #: Po pulle: kód na disku je novší než ten v tomto procese.
        self.code_changed = False
        self.instance = uuid.uuid4().hex[:12]
        self.cores = os.cpu_count() or 1
        self.slots = cfg.slots(self.cores)
        self.state: AgentState = load_state(state_path)
        #: Stav agenta bol pri štarte pokazený (odložený ako `.corrupt-…`) — čo z toho plynie, je v `public()`.
        self.state_error: str | None = None
        if getattr(self.state, "recovered", ""):
            self.state_error = (f"{self.state.recovered} — agent zabudol, čo počítal pre hub (hub to po troch "
                                "heartbeatoch zaradí znova) a ktoré zadané výpočty čakajú na vyzdvihnutie "
                                "(vyzdvihnú sa, keď ich hub ponúkne v heartbeate)")
            log.error("hub agent: %s", self.state_error)
        self.registered = False
        self.last_error: str | None = None
        self.last_ok: float | None = None
        self.ticks = 0
        #: Koľko tickov je lokálny beh výpočtu už v konečnom stave (odovzdá sa po SETTLE_TICKS).
        self._final_ticks: dict[str, int] = {}
        #: História pre odhad času, načítaná najviac raz na heartbeat (`_history`).
        self._history_memo: list[dict[str, Any]] | None = None
        #: Commit, ktorý sa práve ťahá (`git pull`). Kým sa ťahá, agent neberie nové výpočty
        #: a hub to vie z heartbeatu — kód pod bežiacim behom sa nemá meniť.
        self.updating: str | None = None
        #: Výpočet, kvôli ktorému sa ťahá; keď commit nepríde, zlyhá s jasnou chybou.
        self._pull_for: tuple[str, str] | None = None
        #: Pokyn hubu „aktualizuj sa" (čas pokynu) a čo sme z neho naposledy spravili.
        self._pull_request: str | None = None
        self._pull_done: dict[str, Any] | None = None
        self._host_pull_since: tuple[float, str] | None = None   # pokyn hostiteľovi na pull: kedy, z akej verzie
        #: Hotové výpočty zadávateľa, ktoré treba stiahnuť (zip) — robí to pomalé vlákno.
        self._collect_queue: list[dict[str, Any]] = []
        self._collecting: set[str] = set()
        self._state_lock = threading.RLock()
        self._stop = threading.Event()
        self._work = threading.Event()
        self._thread: threading.Thread | None = None
        self._worker: threading.Thread | None = None
        self._watcher: threading.Thread | None = None
        #: Odosielanie spoolu na hub — vlastné vlákno, aby backlog grafových dát nezdržal nasadenia a nový kód.
        self._ship = threading.Event()
        self._shipper_thread: threading.Thread | None = None
        #: `start()` už bežal (stráženie vlákien má zmysel) a koľkokrát ktoré vlákno umrelo a spustilo sa znova.
        self._started = False
        self.thread_restarts: dict[str, int] = {}
        self._threads_lock = threading.Lock()
        #: Kedy sa naposledy upratovali odovzdané behy (`None` = ešte nie, prvé kolo aj
        #: presunie cudzie behy spred `tester.hub.delivered`).
        self._delivered_at: float | None = None

    # -- vlákno ------------------------------------------------------------- #

    def start(self) -> None:
        self._stop.clear()
        # Klon nastavený pred presunom dát pod data/ (docs/DIRECTORIES.md): pravidlá chudého klonu na nové cesty.
        threading.Thread(target=_migrate_sparse, name="hub-agent-sparse", daemon=True).start()
        self._started = True
        self._ensure_threads()
        if self._plugins is None:
            self._plugins = self._plugin_host()
            self._plugins.start()

    def _ensure_threads(self, supervising: bool = False) -> list[str]:
        """Spustí vlákna, ktoré nebežia. Pri strážení (`supervising`) je nebežiace vlákno mŕtve vlákno: zaloguje
        sa ako chyba, spočíta (`thread_restarts`, vidno v `public()`) a spustí znova. Vráti mená znova spustených."""
        znova: list[str] = []
        with self._threads_lock:
            if self._stop.is_set():
                return znova
            for attr, loop, name in THREADS:
                t = getattr(self, attr)
                if t is not None and t.is_alive():
                    continue
                if supervising and t is not None:
                    self.thread_restarts[name] = self.thread_restarts.get(name, 0) + 1
                    znova.append(name)
                    log.error("hub agent: vlákno %s umrelo — spúšťam ho znova (%d. raz)", name, self.thread_restarts[name])
                t = threading.Thread(target=getattr(self, loop), name=name, daemon=True)
                setattr(self, attr, t)
                t.start()
        return znova

    def supervise(self) -> list[str]:
        """Dohľad nad vláknami agenta (audit M-HUB-10): vlákna sa navzájom strážia — heartbeat, pomalé vlákno aj
        strážca spoolu to volajú v každom svojom kole. Mŕtve vlákno heartbeatu by inak znamenalo agenta, ktorého
        hub odpíše, hoci proces beží; mŕtve pomalé vlákno výsledky, ktoré sa nikdy neodovzdajú."""
        if not self._started or self._stop.is_set():
            return []
        try:
            return self._ensure_threads(supervising=True)
        except Exception as exc:  # noqa: BLE001 - stráženie nesmie zhodiť vlákno, ktoré stráži (ani preskočiť heartbeat)
            log.warning("hub agent: stráženie vlákien zlyhalo: %s: %s", type(exc).__name__, exc)
            return []

    def stop(self) -> None:
        self._stop.set()
        self._work.set()
        self._ship.set()
        if self._plugins is not None:
            self._plugins.stop()

    @property
    def heartbeat_seconds(self) -> int:
        """Platný interval heartbeatu: čo poslal hub, inak config."""
        return self.hub_heartbeat or self.cfg.heartbeat_seconds

    def _loop(self) -> None:
        zlyhalo = 0
        while not self._stop.is_set():
            try:
                self.supervise()
                self.tick()
                zlyhalo = 0
            except Exception as exc:  # noqa: BLE001 - výpadok hubu nesmie zhodiť agenta
                self.registered = False
                self.last_error = f"{type(exc).__name__}: {exc}"
                zlyhalo += 1
                if zlyhalo == 1 or zlyhalo % 20 == 0:   # ten istý výpadok do logu nie každé 3 s
                    log.warning("hub agent: %s%s", self.last_error, f" ({zlyhalo}. pokus)" if zlyhalo > 1 else "")
            self._stop.wait(retry_delay(self.heartbeat_seconds, zlyhalo))

    def _spool_watch_loop(self) -> None:
        """Ľahký strážca spoolu: každú sekundu `stat` súborov; rast = zobudiť pomalé vlákno."""
        while not self._stop.wait(SPOOL_WATCH_SECONDS):
            try:
                self.supervise()
                self.watch_spool()
            except Exception as exc:  # noqa: BLE001 - strážca nesmie umrieť
                log.debug("hub agent: strážca spoolu: %s", exc)

    def watch_spool(self) -> bool:
        """Jeden pohľad na spool: keď od minula pribudli bajty alebo súbory, nastaví `_work`
        (shipper pošle hneď, nie až s heartbeatom) a vráti True. Bez shippera (žiadny koreň)
        nič nerobí — ten vzniká v `work()` a heartbeat ho zavolá."""
        shipper = self._live
        if shipper is None:
            return False
        st = shipper.reader.status()
        subory = st.get("files") or []
        stamp = (len(subory), sum(int(f.get("size") or 0) for f in subory))
        self._spool_pending = (time.monotonic(), int(st.get("pending_bytes") or 0))
        zmena = self._spool_stamp is not None and stamp != self._spool_stamp
        self._spool_stamp = stamp
        if zmena:
            (self._ship if self._has_shipper() else self._work).set()
        return zmena

    # -- pluginy agenta ---------------------------------------------------- #

    def _plugin_host(self) -> Any:
        from .agent_plugins import AgentPluginContext, AgentPluginHost

        hub = TelegramHubViews(self.cfg.hub_url, self.cfg.token) if self.cfg.hub_url else None

        def kontext(name: str, stopping: threading.Event) -> AgentPluginContext:
            from tradebot.live.spool import default_roots

            return AgentPluginContext(name, agent_name=self.cfg.name, hub_views=hub, spool_roots=default_roots,
                                      deployments=self._plugin_deployments, modes_changed=self._plugins_changed,
                                      clock=self.clock, stopping=stopping)

        host = AgentPluginHost(kontext, clock=self.clock)
        for name, st in host.status().items():
            log.info("hub agent: plugin %s%s", name, f" — CHYBA {st['load_error']}" if st["load_error"] else "")
        return host

    def _plugins_changed(self) -> None:
        """Plugin (príkaz z Telegramu) zmenil režim: zosúladiť hneď (prekrytie ide do reconcilera) a hlásiť hubu."""
        with self._live_lock:
            self._live_desired_seq += 1
        self._work.set()

    def _plugin_deployments(self) -> list[tuple[dict[str, Any], str]]:
        """Aktívne nasadenia z požadovaného stavu a výsledok reconcilera: `[(nasadenie, chyba)]`."""
        rec = self._reconciler
        with self._live_lock:
            desired = self._live_desired
        if rec is None or not desired:
            return []
        deps = {str(d.get("id")): d for d in desired.get("deployments") or [] if isinstance(d, dict)}
        out = []
        for a in rec.fragment().get("applied") or []:
            d = deps.get(str(a.get("deployment")))
            if d is not None and d.get("active", True):
                out.append((d, str(a.get("error") or "")))
        return out

    def _get_plugin_updater(self) -> Any:
        if self._plugin_updater is None and self._plugins is not None:
            from tradebot.core.env import getenv

            from .agent_plugins import PluginUpdater

            try:
                minuty = float(getenv("AGENT_PLUGIN_UPDATE") or PLUGIN_UPDATE_SECONDS / 60)
            except ValueError:
                minuty = PLUGIN_UPDATE_SECONDS / 60
            self._plugin_updater = PluginUpdater(
                self._plugins, self.start_version, version=gitcode.version, pull=gitcode.pull,
                can_pull=lambda: (self.cfg.role == agent_config.ROLE_LIVE and gitcode.pull_mode() != "host"
                                  and gitcode.pull_enabled() and not self.state.computing and not self.updating
                                  and self._pull_for is None and self._pull_request is None),
                dirty=gitcode.dirty_code, branch=(getenv("GIT_BRANCH", "").strip() or "main"),
                interval=minuty * 60, clock=self.clock)
        return self._plugin_updater

    def _update_plugins(self) -> None:
        """Pomalé vlákno: nový kód len pluginov (z disku, na obchodnom stroji aj z `origin`) → reload bez reštartu.
        Proces potom berie novú verziu ako svoju — inak by sa headless agent po prvom výpočte zbytočne reštartoval."""
        upd = self._get_plugin_updater()
        if upd is None or self.needs_restart:
            return
        upd.loaded = self.start_version or upd.loaded
        nova = upd.tick()
        if nova:
            self.start_version = self.version = nova
            self._work.set()

    def _with_overrides(self, desired: dict[str, Any]) -> dict[str, Any]:
        """Požadovaný stav s režimami prepnutými z pluginov (Telegram). Prekrytie padá, keď ho hub prevzal
        (rovnaký `mode`) alebo nasadenie zmenil neskôr (`updated` ≥ čas prepnutia — hub je novší, vyhráva)."""
        host = self._plugins
        if host is None or not isinstance(desired, dict):
            return desired
        prekrytia = {o["instance"]: o for o in host.overrides()}
        if not prekrytia:
            return desired
        deps = []
        for d in desired.get("deployments") or []:
            o = prekrytia.get(str(d.get("instance") or "")) if isinstance(d, dict) and d.get("active", True) else None
            if o is not None:
                if d.get("mode") == o["mode"] or float(d.get("updated") or 0) >= float(o.get("ts") or 0):
                    host.drop_override(o.get("plugin") or "", o["instance"])
                else:
                    d = {**d, "mode": o["mode"]}
            deps.append(d)
        return {**desired, "deployments": deps}

    def _has_worker(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _has_shipper(self) -> bool:
        return self._shipper_thread is not None and self._shipper_thread.is_alive()

    def _ship_loop(self) -> None:
        """Vlákno odosielania spoolu: zobudí ho strážca spoolu alebo heartbeat; kým ostáva backlog (kolo
        vyčerpalo všetky čítania), ide hneď ďalšie kolo."""
        while not self._stop.is_set():
            if not self._ship.wait(WORK_POLL_SECONDS):
                continue
            self._ship.clear()
            if self._stop.is_set():
                return
            try:
                if self._ship_live():
                    self._ship.set()
            except Exception as exc:  # noqa: BLE001 - vlákno nesmie umrieť
                log.warning("hub agent: odosielanie spoolu zlyhalo: %s: %s", type(exc).__name__, exc)
                self._stop.wait(5.0)

    def _work_loop(self) -> None:
        while not self._stop.is_set():
            if not self._work.wait(WORK_POLL_SECONDS):
                continue
            self._work.clear()
            if self._stop.is_set():
                return
            self.supervise()
            self.work()

    def work(self) -> None:
        """Jedno kolo pomalej práce. Beží **mimo heartbeatu** — zip s výsledkom, sťahovanie
        výsledku a hlavne `git pull` s dopočítaním dát trvajú aj minúty a hub by medzitým
        agenta vyhlásil za mŕtveho (`agent_timeout` je 45 s) a jeho výpočty dal inému."""
        kroky = [self._upload_finished, self._apply_live, self._update_code, self._do_pull, self._do_requested_pull,
                 self._update_plugins, self._drain_collects, self._tidy_delivered]
        if not self._has_shipper():   # bez vlákien (testy, jeden krok) posiela spool aj toto kolo
            kroky.insert(1, self._ship_live)
        for krok in kroky:
            try:
                krok()
            except Exception as exc:  # noqa: BLE001 - jeden krok nesmie zhodiť vlákno
                log.warning("hub agent: %s zlyhalo: %s: %s", krok.__name__, type(exc).__name__, exc)

    # -- live telemetria ---------------------------------------------------- #

    def _live_shipper(self) -> Any:
        """Shipper, keď má z čoho posielať; korene spoolu sa preverujú každú minútu, nech sa
        chytí aj platforma nainštalovaná po štarte agenta (a odpadne, keď jej spool zmizne)."""
        now = self.clock()
        if self._live_checked is not None and now - self._live_checked < LIVE_ROOTS_RECHECK_SECONDS:
            return self._live
        self._live_checked = now
        from tradebot.live.spool import SpoolReader, default_roots

        roots = default_roots()
        if not roots:
            self._live = None
            return None
        if self._live is not None and [str(r) for r in self._live.reader.roots] == [str(r) for r in roots]:
            return self._live
        from tradebot.live.shipper import LiveShipper

        self._live = LiveShipper(SpoolReader(roots, self.live_cursor), self.http, self.cfg.name)
        log.info("hub agent: live spool %s", ", ".join(str(r) for r in roots))
        if getattr(self._live.reader, "cursor_reset", False):
            log.error("hub agent: kurzor spoolu %s bol pokazený (odložený ako .corrupt-…) — celý spool sa pošle "
                      "na hub znova; hub duplicity zahodí, ale odosielanie bude chvíľu zaostávať", self.live_cursor)
        return self._live

    def _ship_live(self) -> bool:
        """Spool platforiem → hub. Chyba (hub mimo) sa zaloguje raz na jej znenie — kurzor stojí
        a ďalšie kolo to skúsi znova; nikdy nevyhodí výnimku von. Vráti True, keď kolo vyčerpalo všetky
        čítania (v spoole ostáva backlog a má ísť hneď ďalšie)."""
        shipper = self._live_shipper()
        if shipper is None:
            return False
        r = shipper.pump()
        chyba = r.get("error")
        if chyba and chyba != self._live_error:
            log.warning("hub agent: live telemetria sa nedá poslať: %s", chyba)
        self._live_error = chyba
        return not chyba and int(r.get("rounds") or 0) >= shipper.max_batches

    def live_status(self) -> dict[str, Any]:
        """Stav live telemetrie pre webapp a CLI: kde je spool, či sa posiela a čo reconciler aplikoval."""
        apply = None
        if self._reconciler is not None:
            try:
                apply = self._reconciler.status()
            except Exception as exc:  # noqa: BLE001 - stav nesmie zhodiť API
                apply = {"error": f"{type(exc).__name__}: {exc}"}
        plugins = None
        if self._plugins is not None:
            try:
                plugins = self._plugins.status()
                if self._plugin_updater is not None and self._plugin_updater.last:
                    plugins = {**plugins, "_update": dict(self._plugin_updater.last)}
            except Exception as exc:  # noqa: BLE001
                plugins = {"_error": f"{type(exc).__name__}: {exc}"}
        if self._live is None:
            return {"active": False, "roots": [], "last_ok": None, "last_error": self._live_error,
                    "sent_total": 0, "accepted_total": 0, "pending_bytes": 0, "files": 0, "apply": apply,
                    "plugins": plugins}
        st = self._live.status()
        reader = st.get("reader") or {}
        return {"active": True, "roots": reader.get("roots", []),
                "last_ok": datetime.fromtimestamp(st["last_ok"], tz=timezone.utc).isoformat(timespec="seconds")
                if st.get("last_ok") else None,
                "last_error": st.get("last_error"), "sent_total": st.get("sent_total", 0),
                "accepted_total": st.get("accepted_total", 0),
                "pending_bytes": reader.get("pending_bytes", 0), "files": len(reader.get("files") or []),
                "cursor_reset": bool(getattr(self._live.reader, "cursor_reset", False)),
                "apply": apply, "plugins": plugins}

    # -- nasadenia z hubu (fáza 2b) ----------------------------------------- #

    def _get_reconciler(self) -> Any:
        """Reconciler s drivermi platforiem tohto stroja — vznikne pri prvom použití (import driverov
        siaha na disk platforiem, do konštruktora agenta to nepatrí)."""
        if self._reconciler is None:
            from tradebot.live.apply import Reconciler
            from tradebot.live.drivers import load_drivers

            self._reconciler = Reconciler(load_drivers(), self._apply_state)
            log.info("hub agent: live drivery: %s", ", ".join(sorted(self._reconciler.drivers)) or "žiadne")
        return self._reconciler

    def _live_body(self) -> dict[str, Any]:
        """`live` do heartbeatu: inštancie zo spoolu (posledný stav súborov), čo reconciler aplikoval
        a ktoré drivery stroj má. Nikdy nevyhodí výnimku — heartbeat musí odísť."""
        out: dict[str, Any] = {"instances": [], "applied": [], "secret_ack": [], "drivers": []}
        try:
            from tradebot.live.spool import default_roots, latest_state

            roots = self._live.reader.roots if self._live is not None else default_roots()
            out["instances"] = [{"instance": s["instance"], "session": s["session"], "last_t": s["last_t"],
                                 "last_bar_ms": s["last_bar_ms"], "last_hb": s.get("last_hb"), "mode": s["mode"],
                                 "profile": s["profile"], "ended": s["ended"]}
                                for s in latest_state(roots, self._live_cache, self._live_dirs)]
        except Exception as exc:  # noqa: BLE001
            log.debug("hub agent: stav spoolu sa nedal zistiť: %s", exc)
        rec = self._reconciler
        if rec is not None:
            try:
                out.update(rec.fragment())
                out["drivers"] = sorted(rec.drivers)
            except Exception as exc:  # noqa: BLE001
                log.debug("hub agent: stav reconcilera sa nedal zistiť: %s", exc)
        # odosielanie spoolu: koľko čaká a akou dávkou — backlog po reštarte platforiem je vidno na karte Stroje
        if self._live is not None:
            try:
                st = self._live.status(reader=False)
                out["ship"] = {"pending_bytes": self._pending_bytes(),
                               "batch": st.get("batch"), "last_ok": st.get("last_ok"), "last_error": st.get("last_error"),
                               **{k: st.get(k) for k in ("read_ms", "post_ms", "rate", "files",
                                                         "rejected_total", "poison_total")}}
            except Exception as exc:  # noqa: BLE001
                log.debug("hub agent: stav odosielania spoolu: %s", exc)
        # fáza 2c: z akého commitu je kód platforiem a ako dopadla posledná aktualizácia
        upd = self._updater
        if upd is not None:
            try:
                out["installed"] = upd.installed()
            except Exception as exc:  # noqa: BLE001
                log.debug("hub agent: markery kódu sa nedali prečítať: %s", exc)
        with self._live_lock:
            out["code_update"] = dict(self._code_update) if self._code_update else None
        # režimy prepnuté z pluginov (Telegram), ktoré hub ešte nemá v nasadení
        if self._plugins is not None:
            try:
                out["overrides"] = [{k: v for k, v in o.items() if k != "plugin"} for o in self._plugins.overrides()]
            except Exception as exc:  # noqa: BLE001
                log.debug("hub agent: prekrytia pluginov: %s", exc)
        return out

    def _pending_bytes(self) -> int:
        """Bajty spoolu čakajúce za kurzorom. Keď beží strážca spoolu, berie sa jeho posledný pohľad (najviac pár
        sekúnd starý) — heartbeat tak neprehľadáva celý spool (po dňoch reštartov tisíce súborov, na Windows VM
        sekundy; audit M-HUB-8). Bez vlákien (testy, `tick()` naholo) sa spočíta hneď."""
        videne = self._spool_pending
        if videne is not None and time.monotonic() - videne[0] <= 5 * SPOOL_WATCH_SECONDS:
            return videne[1]
        return int(self._live.reader.status().get("pending_bytes") or 0)

    def _note_live(self, desired: Any) -> None:
        """Heartbeat priniesol požadovaný stav — odloží sa pomalému vláknu (nikdy sa neaplikuje tu)."""
        if not isinstance(desired, dict):
            return
        cielovy = desired.get("code_target")
        with self._live_lock:
            self._live_desired = desired
            self._live_desired_seq += 1
            self._code_target = dict(cielovy) if isinstance(cielovy, dict) and cielovy.get("version") else None
        # kto nasadenie zmenil (alebo poslal nový kód) — Telegram ho pripíše k štartu a stopu
        if self._plugins is not None:
            self._plugins.desired(desired, self.clock())
        self._work.set()

    def _apply_live(self) -> None:
        """Zosúladenie nasadení v pomalom vlákne: posledný požadovaný stav z heartbeatu → reconciler.
        Beží, len keď od minula prišiel nový stav; výsledok ide do ďalšieho heartbeatu. Bez nového stavu
        reconciler len znova pozrie, či inštancie na platforme nabehli (`refresh`, sám si stráži interval)."""
        with self._live_lock:
            novy = self._live_desired is not None and self._live_applied_seq != self._live_desired_seq
            desired, seq = self._live_desired, self._live_desired_seq
        if not novy:
            if self._reconciler is not None:
                self._reconciler.refresh()
            return
        self._get_reconciler().run(self._with_overrides(desired))
        with self._live_lock:
            self._live_applied_seq = seq

    # -- nový kód na stroji (fáza 2c) --------------------------------------- #

    def _get_updater(self) -> Any:
        """`CodeUpdater` nad drivermi reconcilera; vzniká pri prvom cieli z hubu."""
        if self._updater is None:
            from tradebot.live.update import CodeUpdater

            rec = self._get_reconciler()
            self._updater = CodeUpdater(rec.drivers, git=gitcode, reconciler=rec, clock=self.clock)
        return self._updater

    def _update_code(self) -> None:
        """Pomalé vlákno: keď hub poslal `code_target`, ktorý ešte nie je hotový, spustí aktualizáciu.
        Ten istý cieľ sa po `ok` neopakuje (hub ho zmaže), po `blocked` sa skúša o minútu, po chybe
        o 5 minút; nový cieľ (iná verzia, iný čas, `force`) ide hneď. Kým beží výpočet hubu, čaká."""
        with self._live_lock:
            target = dict(self._code_target) if self._code_target else None
        if target is None:
            return
        key = (target.get("version"), target.get("ts"), bool(target.get("force")))
        now = self.clock()
        last = self._code_attempt
        if last is not None and last[0] == key:
            posledny = self._code_update or {}
            if posledny.get("status") == "ok":
                return
            cakanie = CODE_RETRY_BLOCKED if posledny.get("status") == "blocked" else CODE_RETRY_ERROR
            if now - last[1] < cakanie:
                return
        self._code_attempt = (key, now)
        if self.state.computing:
            vysledok = {"version": target.get("version"), "status": "blocked", "ts": now,
                        "reasons": [f"agent počíta {len(self.state.computing)} výpočtov hubu — počkám, kým dobehnú"],
                        "error": "blokované: bežia výpočty hubu", "platforms": {}, "force": bool(target.get("force"))}
            with self._live_lock:
                self._code_update = vysledok
            return
        upd = self._get_updater()
        self.updating = str(target.get("version") or "")
        log.info("hub agent: nový kód %s na platformy (%s)", target.get("version"),
                 "vynútené" if target.get("force") else "brána: pauza a bez pozície")
        try:
            vysledok = upd.run(target)
        finally:
            self.updating = "pull" if self._pull_request else None
        self.version = gitcode.version() or self.version
        if vysledok.get("code_changed") or (self.start_version and self.version and self.version != self.start_version):
            # kód na disku je novší než tento proces: headless agent sa reštartuje (`__main__`), webapp to ukáže
            self.code_changed = True
            self.needs_restart = True
            vysledok["needs_restart"] = True
        with self._live_lock:
            self._code_update = vysledok
        log.info("hub agent: aktualizácia kódu %s: %s%s", vysledok.get("version"), vysledok.get("status"),
                 f" — {vysledok.get('error')}" if vysledok.get("error") else "")
        self._work.set()   # heartbeat to odnesie; ďalšie kolo reconcilera spustí zavreté terminály

    # -- jeden krok --------------------------------------------------------- #

    def tick(self) -> dict[str, Any]:
        self.ticks += 1
        self._reload_config()
        self.version = gitcode.version() or self.version
        # Pomalé veci (odovzdanie výsledku, jeho stiahnutie, pull) robí druhé vlákno —
        # tu sa len povie, že je čo robiť. Keď agent nebeží na vláknach (testy, jeden krok),
        # sa spraví hneď, ale až po heartbeate.
        self._work.set()
        self._ship.set()
        try:
            if not self.registered:
                self._register()
            odpoved = self._heartbeat()
            if odpoved.get("set_accept") is not None:
                self.set_accept(bool(odpoved["set_accept"]))
            ziadost = odpoved.get("pull")
            if ziadost and ziadost != (self._pull_done or {}).get("request") and ziadost != self._pull_request:
                # nové výpočty už neberieme (hub ich `updating` agentovi neposiela), dopočítame a pull
                log.info("hub agent: hub ziada aktualizaciu (git pull + restart)")
                self._pull_request = ziadost
                self.updating = self.updating or "pull"
            for job in odpoved.get("assign") or []:
                self._accept(job)
            for job_id in odpoved.get("cancel") or []:
                self._cancel(job_id)
            for job in odpoved.get("finished") or []:
                self._queue_collect(job)
            if "live" in odpoved:
                self._note_live(odpoved.get("live"))
            self._note_heartbeat(odpoved.get("heartbeat_seconds"))
            self.last_ok = self.clock()
            self.last_error = None
            return odpoved
        finally:
            # Bez vlákien (testy, `tick()` naholo) sa pomalá práca spraví tu — aj keď hub
            # nedvíha a heartbeat spadol: odovzdanie výsledku na ňom nezávisí.
            if not self._has_worker():
                self.work()

    def _note_heartbeat(self, value: Any) -> None:
        """Hub v odpovedi posiela svoj `heartbeat_seconds` — agent sa mu prispôsobí (mimo
        rozumných hraníc alebo chýbajúci = ostáva config)."""
        try:
            n = int(value) if value is not None else None
        except (TypeError, ValueError):
            n = None
        if n is not None and not (HEARTBEAT_MIN <= n <= HEARTBEAT_MAX):
            n = None
        if n != self.hub_heartbeat:
            if n is not None and n != self.cfg.heartbeat_seconds:
                log.info("hub agent: heartbeat podľa hubu %d s (config %d s)", n, self.cfg.heartbeat_seconds)
            self.hub_heartbeat = n

    def _heartbeat(self) -> dict[str, Any]:
        """Heartbeat; keď hub agenta nepozná (nový hub, stratený `state.json`), prihlási sa
        znova a skúsi to ešte raz — inak by agent mlčal donekonečna."""
        try:
            return self._hb_http.post(f"/api/agents/{self.cfg.name}/heartbeat", self._heartbeat_body())
        except HubError as exc:
            if exc.status != 404:
                raise
            log.info("hub agent: hub ma nepozna, prihlasujem sa znova")
            self.registered = False
            self._register()
            return self._hb_http.post(f"/api/agents/{self.cfg.name}/heartbeat", self._heartbeat_body())

    def _register(self) -> None:
        self._hb_http.post("/api/agents/register", {
            "name": self.cfg.name, "instance": self.instance, "cores": self.cores,
            "slots": self.slots, "accept": self.cfg.accept, "send": self.cfg.send,
            "version": self.version, "role": self.cfg.role, "kind": self.kind,
        })
        self.registered = True

    # -- prijímanie výpočtov za behu ---------------------------------------- #

    def _config_stamp(self) -> float | None:
        try:
            return self.config_path.stat().st_mtime
        except OSError:
            return None

    def _reload_config(self) -> None:
        """Zmena `tester/agent.json` (napr. `tester.hub setup --no-accept`) platí od
        najbližšieho heartbeatu — bez reštartu. Sloty a meno sa za behu nemenia."""
        stamp = self._config_stamp()
        if stamp == self._config_mtime:
            return
        self._config_mtime = stamp
        novy = agent_config.load(self.config_path)
        if novy is None or novy.name != self.cfg.name:
            return
        if novy.accept != self.cfg.accept or novy.send != self.cfg.send or novy.role != self.cfg.role:
            log.info("hub agent: config zmeneny - rola=%s, prijima=%s, posiela=%s",
                     novy.role, novy.accept, novy.send)
        self.cfg.role, self.cfg.accept, self.cfg.send = novy.role, novy.accept, novy.send
        self.cfg.heartbeat_seconds = novy.heartbeat_seconds

    def clear_undelivered(self) -> int:
        """Zabudne zoznam nedoručených (tester ho videl) — behy ostávajú v histórii tohto klonu."""
        with self._state_lock:
            n = len(self.state.undelivered)
            self.state.undelivered.clear()
            self._save()
        return n

    def set_accept(self, value: bool, persist: bool = True) -> bool:
        """Zapnúť alebo vypnúť prijímanie — z webapp, z hubu (`set_accept` v heartbeate)
        alebo z CLI. Zapíše sa do configu, aby to prežilo reštart. Obchodný stroj (rola `live`)
        sa zapnúť nedá — pokyn sa zahodí a vráti `False`."""
        value = bool(value)
        if value and self.cfg.live:
            log.warning("hub agent: stroj ma rolu live - vypocty nikdy neprijima, zapnutie ignorujem")
            return False
        if value == self.cfg.accept:
            return True
        self.cfg.accept = value
        # V kontajneri prichádza `accept` z prostredia a to by pri ďalšom načítaní configu
        # prebilo súbor — nech sa zhodujú.
        if os.environ.get("TRADEBOT_HUB_ACCEPT") is not None:
            os.environ["TRADEBOT_HUB_ACCEPT"] = "true" if value else "false"
        log.info("hub agent: prijimanie vypoctov %s", "zapnute" if value else "vypnute")
        if persist:
            try:
                agent_config.save(self.cfg, self.config_path)
                self._config_mtime = self._config_stamp()
            except OSError as exc:
                log.warning("hub agent: config sa nepodarilo zapisat: %s", exc)
        return True

    def bye(self) -> None:
        """Odhlásenie pred reštartom: hub meno uvoľní hneď a pridelené výpočty podrží."""
        try:
            self._hb_http.post(f"/api/agents/{self.cfg.name}/bye")   # krátky timeout: koniec procesu nečaká 30 s
        except (HubError, OSError, ValueError):
            pass
        self.registered = False

    def _save(self) -> None:
        """Stav na disk — pod zámkom, lebo doň píše heartbeat aj pomalé vlákno. Pod tým istým zámkom sa `computing`,
        `sent`, `undelivered` aj ich záznamy **menia** (`_set`, `_drop`, …): zápis ich prechádza a zmena z druhého
        vlákna uprostred dávala občasné `RuntimeError: dictionary changed size during iteration` (audit N-HUB-10)."""
        with self._state_lock:
            save_state(self.state, self.state_path)

    def _computing(self) -> list[tuple[str, dict[str, Any]]]:
        """Snímka `computing` na prechádzanie (druhé vlákno do slovníka medzitým pridáva a uberá)."""
        with self._state_lock:
            return list(self.state.computing.items())

    def _set(self, entry: dict[str, Any], **fields: Any) -> None:
        """Zmena záznamu výpočtu pod zámkom stavu."""
        with self._state_lock:
            entry.update(fields)

    def _drop(self, job_id: str) -> None:
        """Výpočet von z `computing` (odovzdaný, stratený, odložený) a stav na disk."""
        with self._state_lock:
            self.state.computing.pop(job_id, None)
            self._final_ticks.pop(job_id, None)
            self._save()

    def _history(self) -> list[dict[str, Any]]:
        """Behy pre odhad času: `HISTORY_ROWS` najnovších hotových behov s trvaním z indexu histórie, raz na
        heartbeat — nie `store.all()` (celá história, pri tisícoch behov stovky ms) pri každom odhade (audit
        N-WEB-8). Sklad bez indexu (alebo s nefunkčným) = celá história ako doteraz."""
        if self._history_memo is not None:
            return self._history_memo
        recs: list[dict[str, Any]] | None = None
        index = getattr(self.store, "index", None)
        if index is not None:
            try:
                if index.sync():
                    recs = index.page("status = ? AND duration_s > 0", ["done"], 0, HISTORY_ROWS)
            except Exception as exc:  # noqa: BLE001 - index je odvodený; bez neho sa číta po starom
                log.debug("hub agent: index histórie pre odhad času: %s", exc)
                recs = None
        if recs is None:
            recs = self.store.all()
        self._history_memo = recs
        return recs

    # -- heartbeat ---------------------------------------------------------- #

    def _hub_run_ids(self) -> set[str]:
        return {e.get("run_id") for _, e in self._computing() if e.get("run_id")}

    def _local_load(self) -> dict[str, Any]:
        """Lokálna fronta bez výpočtov hubu: čo si tester spustil sám."""
        nase = self._hub_run_ids()
        bezia: list[dict[str, Any]] = []
        caka = 0
        for j in self.runner.snapshot():
            if j.get("id") in nase:
                continue
            if j.get("status") == "running":
                bezia.append(j)
            elif j.get("status") == "queued":
                caka += 1
        eta = 0.0
        for j in bezia:
            s = j.get("settings") or {}
            odhad = P.estimate_seconds(s, self._history(), cores=self.cores)
            uplynulo = max(0.0, self.clock() - (_parse_iso(j.get("started")) or self.clock()))
            eta = max(eta, P.remaining_seconds(odhad, uplynulo, None))
        return {"running": len(bezia), "queued": caka,
                "exclusive": any(P.kind_of(j.get("settings") or {}) == P.KIND_HYPEROPT for j in bezia),
                "eta_seconds": eta if bezia else None}

    def _report(self, job_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        """Stav jedného výpočtu hubu pre heartbeat; `None`, keď beh lokálne neexistuje."""
        run_id = entry.get("run_id")
        if not run_id:
            return None
        job = self.runner.job(run_id)
        if job is not None:
            status = job.status
            settings, log_lines, started = job.settings, job.log_lines, job.started
        else:
            rec = self.store.find(run_id)
            if rec is None:
                return None
            status = rec.get("status") or "failed"
            settings, log_lines, started = rec.get("settings") or {}, [], rec.get("started")
        if status in ("done", "failed"):
            overenia = self._live_verifications(run_id)
            if not overenia:
                return {"id": job_id, "status": status, "run_id": run_id, "progress": 1.0,
                        "eta_seconds": 0.0}
            # Hyperopt dobehol, ale víťaz ešte beží na referenčných oknách — výpočet nie je
            # hotový a stroj nie je voľný. Zvyšok je najdlhšie z toho, čo ešte beží alebo čaká.
            hotove = len(self._verification_ids(run_id))
            eta = 0.0
            historia = self._history()
            for j in overenia:
                odhad = P.estimate_seconds(j.get("settings") or {}, historia, cores=self.cores)
                zacal = _parse_iso(j.get("started")) if j.get("status") == "running" else None
                uplynulo = max(0.0, self.clock() - zacal) if zacal else 0.0
                eta = max(eta, P.remaining_seconds(odhad, uplynulo, None))
            podiel = hotove / float(hotove + len(overenia))
            return {"id": job_id, "status": "running", "run_id": run_id,
                    "progress": round(0.8 + 0.2 * podiel, 3), "eta_seconds": round(eta, 1),
                    "elapsed_seconds": round(max(0.0, self.clock() - (_parse_iso(started) or self.clock())), 1)}
        uplynulo = max(0.0, self.clock() - (_parse_iso(started) or self.clock())) if started else 0.0
        odhad = entry.get("estimate_seconds")
        if odhad is None:
            odhad = P.estimate_seconds(settings, self._history(), cores=self.cores)
            self._set(entry, estimate_seconds=odhad)
        limit = entry.get("max_seconds") or max(MAX_RUNTIME_FACTOR * float(odhad), MIN_MAX_SECONDS)
        if entry.get("max_seconds") != limit:
            self._set(entry, max_seconds=limit)
        if status == "running" and uplynulo > limit and not entry.get("timed_out"):
            # Zaseknutý beh: zabiť a nahlásiť ako zlyhaný — hub nesmie čakať donekonečna.
            log.warning("hub agent: beh %s prekrocil strop %.0f min, zabijam", run_id, limit / 60)
            self._set(entry, timed_out=True)
            self._save()
            self._kill(run_id)
        epochs = (settings.get("hyperopt") or {}).get("epochs") if P.kind_of(settings) == P.KIND_HYPEROPT else None
        postup = P.progress_from_log(log_lines, epochs) if epochs else None
        if epochs and postup is None and started:
            # Freqtrade bez terminálu priebeh nevypisuje; epochy ale priebežne zapisuje
            # do `.fthypt`, ktorý vznikol po štarte behu.
            from ..hyperopt import latest_results

            postup = P.progress_from_results(latest_results(_parse_iso(started) or 0.0), epochs)
        zvysok = P.remaining_seconds(float(odhad), uplynulo, postup) if status == "running" else float(odhad)
        return {"id": job_id, "status": "running", "run_id": run_id, "progress": postup,
                "eta_seconds": round(zvysok, 1), "elapsed_seconds": round(uplynulo, 1)}

    def _heartbeat_body(self) -> dict[str, Any]:
        jobs = []
        self._history_memo = None   # história pre odhady sa číta najviac raz na heartbeat
        for job_id, entry in self._computing():
            r = self._report(job_id, entry)
            if r is not None:
                jobs.append(r)
        return {"instance": self.instance, "accept": self.cfg.accept, "send": self.cfg.send,
                "role": self.cfg.role, "kind": self.kind, "cores": self.cores, "slots": self.slots,
                "version": self.version, "needs_restart": self.needs_restart, "updating": bool(self.updating),
                "load": self._local_load(), "jobs": jobs, "live": self._live_body(), "pull_done": self._pull_done,
                "plugins": self._plugins_body()}

    def _plugins_body(self) -> dict[str, Any] | None:
        """`plugins` do heartbeatu: z ktorého commitu sú pluginy načítané (`start_version` — po reloade bez
        reštartu nový, po pulle s reštartom ešte starý) a či bežia; karta Hub ich porovná s `origin/main`.
        Nikdy nevyhodí výnimku — heartbeat musí odísť."""
        host = self._plugins
        if host is None:
            return None
        try:
            items = host.brief()
        except Exception as exc:  # noqa: BLE001
            return {"version": self.start_version, "items": {}, "error": f"{type(exc).__name__}: {exc}"}
        upd = self._plugin_updater.last if self._plugin_updater is not None else None
        return {"version": self.start_version, "items": items,
                "reloaded": dict(upd) if isinstance(upd, dict) else None}

    # -- výpočty od hubu ---------------------------------------------------- #

    def _fail(self, job_id: str, error: str) -> None:
        self.http.post_bytes(f"/api/jobs/{job_id}/result?status=failed&agent={self.cfg.name}"
                             f"&version={_q(self.version)}&error={_q(error[:500])}", b"")

    def _ensure_version(self, job: dict[str, Any]) -> bool:
        """Má tento klon commit zadávateľa? Keď nie, pull — ale až keď nič nepočíta.

        Vráti True, keď sa výpočet smie prijať teraz. False = počkať (hub ho pošle znova
        v ďalšom heartbeate), alebo už zlyhal.
        """
        wanted = job.get("version")
        if gitcode.has_version(wanted):
            if (self.restart_on_pull and self.version and self.start_version
                    and self.version != self.start_version):
                # Kód na disku je novší než tento proces (pull na hostiteľovi, kontajner):
                # nič nové nebrať, dopočítať, čo beží, a reštartovať sa.
                if self.state.computing:
                    return False
                log.info("hub agent: kod na disku je novsi (%s -> %s), restart", self.start_version, self.version)
                self.needs_restart = True
                return False
            return True
        if self.state.computing:
            log.info("hub agent: výpočet %s chce commit %s, čakám na dobehnutie %d behov",
                     job["id"], wanted, len(self.state.computing))
            return False
        if self.needs_restart or self.updating:
            return False  # pull beží, alebo už bol a čaká sa na reštart
        # Pull (a dopočítanie dát po ňom) trvá aj minúty — v tomto vlákne by sa medzitým
        # neposlal heartbeat a hub by agenta odpísal. Zadá sa pomalému vláknu a hub výpočet
        # pošle znova; kým sa ťahá, agent nič neberie a hlási to v heartbeate.
        self.updating = wanted
        self._pull_for = (job["id"], wanted or "")
        self._work.set()
        log.info("hub agent: výpočet %s chce commit %s, ťahám kód", job["id"], wanted)
        return False

    def _do_pull(self) -> None:
        """`git pull` a poskladanie dát po ňom — pomalé vlákno, nie heartbeat."""
        if self._pull_for is None:
            return
        job_id, wanted = self._pull_for
        try:
            r = gitcode.pull()
            self.version = gitcode.version() or self.version
            if not gitcode.has_version(wanted):
                vystup = (r.get("output") or "").strip()[-300:]
                self._fail(job_id, f"agent {self.cfg.name} nemá commit {wanted} ani po git pull "
                                   f"(HEAD {self.version}) — zadávateľ ho musí pushnúť do main. {vystup}")
                return
            self.code_changed = True
            self._sync_data()
            if self.restart_on_pull:
                self.needs_restart = True  # nový proces si výpočet vezme s novým kódom
            else:
                log.warning("hub agent: po git pull beží tento proces na starom kóde — "
                            "reštartuj webapp")
        finally:
            self._pull_for = None
            self.updating = "pull" if self._pull_request else None

    def _do_requested_pull(self) -> None:
        """Pokyn hubu „aktualizuj sa": keď dobehne, čo počítame, `git pull` (+ dáta) a reštart —
        headless sa reštartuje sám, webapp sama, keď sa kód v gite zmenil (`_watch_code`).

        V kontajneri s `TRADEBOT_HUB_PULL=host` pull spraví hostiteľ: agent mu zapíše pokyn
        a v ďalších kolách čaká na jeho výsledok (najviac `HOST_PULL_TIMEOUT`), vlákno neblokuje."""
        ziadost = self._pull_request
        if ziadost is None or self.state.computing or self._pull_for is not None:
            return
        r = self._host_pull(ziadost) if gitcode.pull_mode() == "host" else gitcode.pull()
        if r is None:
            return
        try:
            pred = r.get("before") or self.version
            self.version = gitcode.version() or self.version
            if r.get("ok") and self.version != pred:
                self.code_changed = True
                self._sync_data()
                if self.restart_on_pull:
                    self.needs_restart = True
            log.info("hub agent: aktualizacia na pokyn hubu: %s (%s -> %s)",
                     "ok" if r.get("ok") else "zlyhala", pred, self.version)
            self._pull_done = {"request": ziadost, "ok": bool(r.get("ok")), "version": self.version,
                               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "output": (r.get("output") or "").strip()[-300:]}
        finally:
            self._pull_request = None
            if self.updating == "pull":
                self.updating = None

    def _host_pull(self, ziadost: str) -> dict[str, Any] | None:
        """Pull na hostiteľovi: prvé kolo zapíše pokyn, ďalšie čakajú na výsledok; `None` = ešte nie."""
        r = gitcode.host_pull_result(ziadost)
        if r is not None:
            # verzia pred pullom: `tick` medzitým `self.version` prepísal na tú z disku
            pred = self._host_pull_since[1] if self._host_pull_since else None
            self._host_pull_since = None
            return {**r, "before": pred}
        if self._host_pull_since is None:
            try:
                gitcode.request_host_pull(ziadost)
            except OSError as exc:
                return {"ok": False, "output": f"pokyn na pull pre hostiteľa sa nedal zapísať: {exc}"}
            self._host_pull_since = (self.clock(), self.version)
            log.info("hub agent: pokyn na git pull poslaný hostiteľovi")
            return None
        if self.clock() - self._host_pull_since[0] < HOST_PULL_TIMEOUT:
            return None
        self._host_pull_since = None
        return {"ok": False, "output": f"hostiteľ do {HOST_PULL_TIMEOUT:.0f} s na pokyn nestiahol kód — beží na ňom "
                                       "systemd path jednotka s docker/host-pull.sh (docs/HUB.md)? Inak kód "
                                       "stiahne až jeho časovač"}

    def _sync_data(self) -> None:
        """Po pulle: čo pribudlo v `data/archive/`, zložiť do skladu, a dopočítať timeframy.

        Rovnaký commit = rovnaké dáta pre všetkých agentov — ale len keď si ich agent po
        pulle aj rozbalí; inak by beh na novom páre spadol až vo Freqtrade.
        """
        from .. import data_archive, timeframes

        try:
            if data_archive.missing():
                log.info("hub agent: skladam nove data z archivu")
                data_archive.main(["merge"])
            if timeframes.missing():
                timeframes.ensure()
        except Exception as exc:  # noqa: BLE001 - nech to povie beh, nie agent
            log.warning("hub agent: data po pulle sa nepodarilo zlozit: %s", exc)

    def _accept(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        if job_id in self.state.computing:
            return  # hub ho posiela, kým ho nenahlásime ako bežiaci — už ho máme
        if self.cfg.live:
            # Obchodný stroj nepočíta nikdy — ani keď ho pridelí hub, ktorý o roliach nevie.
            # Hub vidí `accept: false` a pridelený-nevzatý výpočet vráti do fronty.
            return
        if self.updating:
            return  # kód sa práve prepisuje pod rukami; hub ho pošle znova
        if not self._ensure_version(job):
            return
        payload = job.get("payload") or {}
        # Beh v histórii agenta (a po vrátení aj zadávateľa) nesie, odkiaľ prišiel a na
        # akom kóde bežal — inak by sa o týždeň nedalo povedať, prečo dal iné čísla.
        settings = {**(payload.get("settings") or {}),
                    "hub": {"job": job_id, "submitter": job.get("submitter"),
                            "version_requested": job.get("version"), "version": self.version,
                            "agent": self.cfg.name}}
        try:
            local = self.runner.submit(payload["params"], settings,
                                       note=payload.get("note") or "", user=payload.get("user") or "")
        except Exception as exc:  # noqa: BLE001 - zlý config nech zlyhá ako výpočet, nie ako agent
            self._fail(job_id, str(exc))
            return
        with self._state_lock:
            self.state.computing[job_id] = {"run_id": local.id, "kind": job.get("kind"),
                                            "submitter": job.get("submitter"),
                                            "max_seconds": job.get("max_seconds"),
                                            "accepted": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            self._save()

    def _cancel(self, job_id: str) -> None:
        entry = self.state.computing.get(job_id)
        if entry is None:
            # nič také nepočítame — hubu to povieme hneď, nech nečaká
            self.http.post_bytes(f"/api/jobs/{job_id}/result?status=cancelled&agent={self.cfg.name}", b"")
            return
        self._set(entry, cancel_requested=True)
        self._save()
        if entry.get("run_id"):
            self._kill(entry["run_id"])

    def _kill(self, run_id: str) -> None:
        """Zabije lokálny beh aj overovacie behy víťaza, keby už boli vo fronte."""
        self.runner.cancel(run_id)
        for j in self.runner.snapshot():
            if ((j.get("settings") or {}).get("hyperopt_run") or {}).get("id") == run_id:
                self.runner.cancel(j["id"])

    def _live_verifications(self, run_id: str) -> list[dict[str, Any]]:
        """Overovacie behy víťaza, ktoré ešte bežia alebo čakajú v lokálnom runneri."""
        return [j for j in self.runner.snapshot()
                if ((j.get("settings") or {}).get("hyperopt_run") or {}).get("id") == run_id]

    def _verification_ids(self, run_id: str) -> list[str]:
        # Overenia víťaza sú body celku v `sweeps/`, nie behy histórie — `tagged` vidí oboje.
        return [r["id"] for r in self.store.tagged("hyperopt_run", run_id)]

    def _settled(self, run_id: str) -> tuple[bool, str]:
        """(je hotové, stav) — hotové = lokálny beh v konečnom stave a nič, čo naň nadväzuje, nežije."""
        job = self.runner.job(run_id)
        if job is not None:
            status = job.status
        else:
            rec = self.store.find(run_id)
            if rec is None:
                # beh zmizol: agent sa reštartoval uprostred (runner je nový, run.json ešte nebol) -
                # hub ho podľa heartbeatu (beh chýba) zaradí znova alebo odpíše s dôvodom (N-HUB-1)
                return True, "lost"
            status = rec.get("status") or "failed"
        if status not in ("done", "failed"):
            return False, status
        if self._live_verifications(run_id):
            return False, status
        return True, status

    def _upload_finished(self) -> None:
        """Hotové výpočty hubu odovzdať — a keď hub nie je, nechať si ich na neskôr.

        Kým odovzdanie neprejde, záznam ostáva v `computing` a skúsi sa pri každom ďalšom
        ticku (aj o hodinu, aj po reštarte agenta). Zahodí sa až vtedy, keď ho hub odmietne
        natrvalo — vtedy ide do `undelivered` a behy ostanú aspoň v histórii tohto klonu.
        """
        for job_id, entry in self._computing():
            run_id = entry.get("run_id")
            if not run_id:
                continue
            hotove, status = self._settled(run_id)
            if not hotove:
                self._final_ticks.pop(job_id, None)
                continue
            if status == "lost":
                # Neodovzdávať „failed" s prázdnou chybou: hub by výpočet odpísal bez druhého pokusu.
                # Agent ho zabudne (heartbeat ho už nehlási) a hub ho po troch heartbeatoch bez neho vráti
                # do fronty (`_lost`, raz sa skúsi znova) - aj tomuto agentovi, `_accept` ho už nezahodí.
                log.warning("hub agent: vypocet %s (beh %s) sa po restarte agenta stratil - vraciam ho hubu",
                            job_id, run_id)
                self._drop(job_id)
                continue
            n = self._final_ticks.get(job_id, 0) + 1
            self._final_ticks[job_id] = n
            if entry.get("kind") == P.KIND_HYPEROPT and n < SETTLE_TICKS:
                continue
            run_ids = [run_id] + self._verification_ids(run_id)
            try:
                data = pack_runs(self.store.root, run_ids, self.store.batches)
            except OSError as exc:  # zamknutý súbor, plný disk — skúsi sa o tick znova
                self._deliver_failed(job_id, entry, f"zabalenie behu zlyhalo: {exc}")
                continue
            if entry.get("timed_out") and status != "done":
                stav = "failed"
                chyba = (f"prekročil strop {float(entry.get('max_seconds') or 0) / 60:.0f} min "
                         f"a agent {self.cfg.name} ho zabil")
            elif entry.get("cancel_requested") and status != "done":
                stav, chyba = "cancelled", ""  # kto a prečo dopíše hub (`cancelled_by`)
            else:
                stav = status
                chyba = ((self.store.find(run_id) or {}).get("error") or "") if status == "failed" else ""
            q = (f"?status={stav}&agent={self.cfg.name}&version={_q(self.version)}"
                 f"&run_ids={','.join(run_ids)}")
            if chyba:
                q += f"&error={_q(chyba[:500])}"
            try:
                self.http.post_bytes(f"/api/jobs/{job_id}/result{q}", data)
            except HubError as exc:
                if exc.status == 410:
                    # Hub výpočet medzitým vybavil inde (agent sa mu odmlčal) — náš výsledok je
                    # navyše; nie je to nedoručené, behy idú preč z histórie ako odovzdané.
                    log.info("hub agent: vypocet %s uz hub vybavil inde — vysledok %s netreba",
                             job_id, ", ".join(run_ids))
                    self._drop(job_id)
                    self._retire(entry, run_ids)
                    continue
                if exc.status == 404:
                    # Hub môže byť po reštarte ešte bez stavu — pár tickov to skúsime znova.
                    self._set(entry, notfound=int(entry.get("notfound") or 0) + 1)
                    if entry["notfound"] < DELIVER_404_TRIES:
                        self._deliver_failed(job_id, entry, f"hub 404: {exc.detail}")
                        continue
                if exc.status in (400, 403, 404, 413, 422):   # 413: zip nad strop hubu — opakovanie nepomôže
                    self._park(job_id, entry, run_ids, stav, f"hub {exc.status}: {exc.detail}")
                    continue
                self._deliver_failed(job_id, entry, str(exc))  # 401, 5xx — chyba sa dá opraviť
                continue
            except (OSError, ValueError) as exc:  # hub mimo, sieť, rozsypaná odpoveď
                self._deliver_failed(job_id, entry, f"{type(exc).__name__}: {exc}")
                continue
            self._drop(job_id)
            self._retire(entry, run_ids)

    def _retire(self, entry: dict[str, Any], run_ids: list[str]) -> None:
        """Odovzdaný výpočet iného zadávateľa von z histórie (`tester.hub.delivered`) —
        zadávateľ ho pushne a rovnaký súbor mimo gitu by tu zastavil `git pull`."""
        submitter = entry.get("submitter")
        if submitter is None:  # výpočet prijatý pred touto zmenou
            submitter = (((self.store.find(entry["run_id"]) or {}).get("settings") or {})
                         .get("hub") or {}).get("submitter")
        if not submitter or submitter == self.cfg.name:
            return
        try:
            delivered.retire(self.store, run_ids)
        except OSError as exc:  # zamknutý súbor (Windows) — dorieši upratovanie po štarte
            log.warning("hub agent: odovzdane behy %s sa nepodarilo odlozit: %s", ", ".join(run_ids), exc)

    def _tidy_delivered(self) -> None:
        """Raz po štarte odloží cudzie behy spred `tester.hub.delivered`, potom raz za
        `DELIVERED_PURGE_SECONDS` zmaže odovzdané behy staršie než `delivered.KEEP_DAYS`."""
        now = self.clock()
        if self._delivered_at is not None and now - self._delivered_at < DELIVERED_PURGE_SECONDS:
            return
        prvy = self._delivered_at is None
        self._delivered_at = now
        if prvy:
            keep: set[str] = set()
            for _, entry in self._computing():
                if entry.get("run_id"):
                    keep.add(entry["run_id"])
                    keep.update(self._verification_ids(entry["run_id"]))
            with self._state_lock:
                nedorucene = list(self.state.undelivered.values())
            for zaznam in nedorucene:
                keep.update(zaznam.get("run_ids") or [])
            ids = delivered.foreign(self.store, self.cfg.name, keep)
            if ids:
                n = len(delivered.retire(self.store, ids))
                log.info("hub agent: %d behov spocitanych pre inych odlozenych do %s", n,
                         delivered.root_for(self.store))
        n = delivered.purge(delivered.root_for(self.store))
        if n:
            log.info("hub agent: zmazanych %d odovzdanych behov starsich nez %g dni", n, delivered.KEEP_DAYS)

    def _deliver_failed(self, job_id: str, entry: dict[str, Any], reason: str) -> None:
        """Odovzdanie neprešlo (hub mimo) — necháme si ho a skúsime to o tick znova."""
        self._set(entry, deliver_fails=int(entry.get("deliver_fails") or 0) + 1, deliver_error=reason[:300])
        if entry["deliver_fails"] in (1, 10) or entry["deliver_fails"] % 60 == 0:
            log.warning("hub agent: vysledok %s sa nedari odovzdat (%dx): %s — necham si ho",
                        job_id, entry["deliver_fails"], reason)
        self._save()

    def _park(self, job_id: str, entry: dict[str, Any], run_ids: list[str], status: str,
              reason: str) -> None:
        """Hub výsledok odmietol natrvalo (nepozná ho, alebo ho medzitým dal inému).
        Beh je v histórii tohto klonu — zapíšeme, čo sa nedoručilo, nech sa to dá nájsť."""
        log.warning("hub agent: vypocet %s uz hub neprijal (%s) — behy %s ostavaju v historii "
                    "tohto klonu", job_id, reason, ", ".join(run_ids))
        with self._state_lock:
            self.state.undelivered[job_id] = {
                "run_ids": run_ids, "status": status, "reason": reason[:300],
                "kind": entry.get("kind"),
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            self._drop(job_id)

    # -- výsledky toho, čo sme poslali -------------------------------------- #

    def note_sent(self, job: dict[str, Any], note: str = "") -> None:
        """Zapíše, že sme výpočet zadali — heartbeat si potom výsledok vyzdvihne sám."""
        with self._state_lock:
            self.state.sent[job["id"]] = {
                "kind": job.get("kind"), "note": note, "created": job.get("created"),
                "status": job.get("status"), "run_ids": [], "error": None,
            }
            self._save()

    def _queue_collect(self, job: dict[str, Any]) -> None:
        """Hotový výpočet zadávateľa: zip sťahuje pomalé vlákno, nie heartbeat."""
        with self._state_lock:
            if job["id"] in self._collecting:
                return
            self._collecting.add(job["id"])
            self._collect_queue.append(job)
        self._work.set()

    def _drain_collects(self) -> None:
        while True:
            with self._state_lock:
                if not self._collect_queue:
                    return
                job = self._collect_queue.pop(0)
            try:
                self._collect(job)
            except (HubError, OSError, ValueError) as exc:
                log.warning("hub agent: vysledok %s sa nepodarilo vyzdvihnut: %s", job["id"], exc)
            finally:
                with self._state_lock:
                    self._collecting.discard(job["id"])

    def _collect(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        with self._state_lock:
            zaznam = self.state.sent.setdefault(job_id, {"kind": job.get("kind"), "note": job.get("note") or "",
                                                         "created": job.get("created"), "run_ids": []})
        run_ids: list[str] = []
        if job.get("has_result"):
            try:
                data = self.http.get_bytes(f"/api/jobs/{job_id}/result")
            except HubError as exc:
                if exc.status != 410:
                    raise
                data = b""
            if data:
                run_ids = unpack_runs(data, self.store.root, self.store.batches)
        self._set(zaznam, status=job.get("status"), error=job.get("error"),
                  run_ids=run_ids or list(job.get("run_ids") or []), agent=job.get("agent"),
                  collected=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self._save()
        self.http.post(f"/api/jobs/{job_id}/ack")

    # -- stav pre API ------------------------------------------------------- #

    def public(self) -> dict[str, Any]:
        with self._state_lock:
            computing = {k: dict(v) for k, v in self.state.computing.items()}
            sent = {k: dict(v) for k, v in self.state.sent.items()}
            undelivered = {k: dict(v) for k, v in self.state.undelivered.items()}
        return {
            "name": self.cfg.name, "hub_url": self.cfg.hub_url, "accept": self.cfg.accept,
            "role": self.cfg.role, "kind": self.kind,
            "send": self.cfg.send, "cores": self.cores, "slots": self.slots,
            "version": self.version, "needs_restart": self.needs_restart,
            "code_changed": self.code_changed, "updating": self.updating,
            "registered": self.registered, "last_error": self.last_error,
            "heartbeat_seconds": self.heartbeat_seconds,
            "last_ok": datetime.fromtimestamp(self.last_ok, tz=timezone.utc).isoformat(timespec="seconds")
            if self.last_ok else None,
            "computing": computing, "sent": sent, "undelivered": undelivered,
            # Spočítané a čakajúce na hub (výpadok) — beh je hotový, len sa ešte neodovzdal.
            "pending_upload": sum(1 for v in computing.values() if v.get("deliver_fails")),
            # dohľad (audit M-HUB-10): vlákna, ktoré umreli a bežia znova, a stav agenta stratený pri štarte
            "thread_restarts": dict(self.thread_restarts), "state_error": self.state_error,
            "live": self.live_status(),
            "code_target": dict(self._code_target) if self._code_target else None,
            "code_update": dict(self._code_update) if self._code_update else None,
        }


def _q(text: str) -> str:
    from urllib.parse import quote
    return quote(text, safe="")
