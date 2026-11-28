"""Plugin `watchdog` (docs/LIVE.md, „Strážca (hub)“): ohlási do Telegramu, čo zvnútra ohlásiť nejde.

**Stroje** s aktívnym nasadením, ktoré prestali posielať heartbeat, a ich návrat — spadnutý agent,
vypnutý stroj alebo výpadok internetu doma vidno len zvonka. Offline = `now - last_seen >
agent_timeout + OFFLINE_GRACE` a hub beží aspoň toľko (po reštarte hubu sú všetci agenti chvíľu
„offline“, kým sa neohlásia).

**Inštancie** (SMERNICA V2 U1.5): aktívne nasadenie, ktorého inštancia počas seansy (predvolene Ne 23:00 – Pi 21:00
UTC) neposlala heartbeat ani udalosť dlhšie ako `INSTANCE_SILENT_MIN` minút (30), a jej návrat — platforma spadla,
zamrzla alebo stratila spojenie, hoci agent stroja beží. Stop účtu na tom nezávisí (je v EA / NT), alarm áno.
Stav sa číta priamo z `live.sqlite` hubu (len na čítanie), cesta `live_db` v config.json pluginu.

**Pluginy**: nenačítal sa, `tick` padá dlhšie ako `PLUGIN_GRACE`, `tick` visí dlhšie ako jeho
`max_tick`, alebo plugin sám hlási `problem` (napr. kalendár sa nedá stiahnuť) — a návrat do poriadku.

Prvé pozorovanie hlási len problém. Čo naposledy ohlásil, je v `state.json` pluginu, aby po
reštarte nehlásil to isté znova (prvý štart prevezme starý `HUB_TELEGRAM_STATE`).
"""

from __future__ import annotations

import html
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.paths import HUB_LIVE_DB, HUB_TELEGRAM_STATE

from ..base import HubPlugin, NotifyError, read_json, write_json

#: Navyše k `agent_timeout`, kým sa stroj ohlási ako nedostupný (krátky výpadok siete nespamuje).
OFFLINE_GRACE = 120.0
#: Tak dlho musí plugin padať, kým sa ohlási (jedna chyba siete nič).
PLUGIN_GRACE = 300.0
#: Toľko minút bez heartbeatu a udalosti počas seansy, kým sa inštancia ohlási (V2 U1.5).
INSTANCE_SILENT_MIN = 30.0
#: Seansa pre alarm inštancií v UTC: od nedele 23:00 do piatku 21:00 (futures CME aj CFD); mimo nej sa mlčanie
#: nehlási (víkend, platforma vedome vypnutá).
SESSION_OPEN = (6, 23)     # (weekday() nedele, hodina)
SESSION_CLOSE = (4, 21)    # (piatok, hodina)

#: Tak dlho musí stroj hlásiť chybu odosielania spoolu (`live.ship.last_error`), kým sa ohlási.
SHIP_GRACE = 600.0


class Watchdog(HubPlugin):
    title = "Strážca strojov a pluginov"
    interval = 20.0
    max_tick = 120.0

    def setup(self, ctx) -> None:
        super().setup(ctx)
        self.started = ctx.clock()
        st = read_json(ctx.path("state.json"))
        if st is None:   # prvý štart pluginu: stav starého strážcu
            st = read_json(ctx.dir.parent.parent / HUB_TELEGRAM_STATE.name, {}) or {}
        self.reported: dict[str, bool] = {str(k): bool(v) for k, v in (st.get("online") or {}).items()}
        self.plugins_reported: dict[str, str] = {str(k): str(v) for k, v in (st.get("plugins") or {}).items()}
        #: stroj → chyba odosielania spoolu, ktorú sme ohlásili (prázdne = nič) a odkedy ju stroj hlási (len v pamäti)
        self.ship_reported: dict[str, str] = {str(k): str(v) for k, v in (st.get("ship") or {}).items() if v}
        self.ship_since: dict[str, float] = {}
        #: inštancia → ohlásené mlčanie (True) / návrat ohlásený alebo nič (chýba)
        self.instances_reported: dict[str, bool] = {str(k): bool(v) for k, v in (st.get("instances") or {}).items() if v}

    def _save(self) -> None:
        write_json(self.ctx.path("state.json"), {"online": self.reported, "plugins": self.plugins_reported,
                                                 "ship": {k: v for k, v in self.ship_reported.items() if v},
                                                 "instances": {k: True for k, v in self.instances_reported.items() if v}})

    # -- inštancie (V2 U1.5) --------------------------------------------------
    @staticmethod
    def in_session(now: float) -> bool:
        d = datetime.fromtimestamp(now, timezone.utc)
        wd, h = d.weekday(), d.hour
        if wd == 5:
            return False                                   # sobota
        if wd == SESSION_OPEN[0]:
            return h >= SESSION_OPEN[1]                    # nedeľa od 23:00
        if wd == SESSION_CLOSE[0]:
            return h < SESSION_CLOSE[1]                    # piatok do 21:00
        return True

    def _live_db(self) -> Path:
        c = self.ctx.config()
        if c.get("live_db"):
            return Path(str(c["live_db"]))
        root = getattr(self.ctx.hub, "root", None)
        return Path(root) / HUB_LIVE_DB.name if root else HUB_LIVE_DB

    def _last_seen_ms(self) -> dict[str, int]:
        path = self._live_db()
        if not path.exists():
            return {}
        try:
            con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
            try:
                rows = con.execute("SELECT id, last_t, last_hb FROM instances").fetchall()
            finally:
                con.close()
        except sqlite3.Error as exc:
            self.ctx.log.warning("watchdog: live.sqlite - %s", exc)
            return {}
        return {str(i): max(int(a or 0), int(b or 0)) for i, a, b in rows}

    def instance_messages(self, now: float) -> list[tuple[str, bool, str]]:
        """`[(inštancia, mlčí, text)]` — nasadenie aktívne, stroj online, inštancia mlčí > 30 min počas seansy."""
        hub = self.ctx.hub
        deploy = getattr(hub, "deploy", None)
        if deploy is None or not hasattr(deploy, "deployments"):
            return []
        minuty = float(self.ctx.config().get("instance_silent_min") or INSTANCE_SILENT_MIN)
        agents = self.ctx.agents()
        limit = float(getattr(hub, "agent_timeout", 45.0)) + OFFLINE_GRACE
        seen = self._last_seen_ms()
        spravy: list[tuple[str, bool, str]] = []
        sledovane = set()
        for d in deploy.deployments():
            inst = str(d.get("instance") or "")
            if not inst or not d.get("active", True) or d.get("mode") == "paused":
                continue
            sledovane.add(inst)
            a = agents.get(str(d.get("agent") or "")) or {}
            stroj_online = now - float(a.get("last_seen") or 0) <= limit
            last = seen.get(inst, 0)
            ticho = (now * 1000 - last) / 60000 if last else None
            mlci = stroj_online and self.in_session(now) and ticho is not None and ticho > minuty
            predtym = self.instances_reported.get(inst, False)
            if mlci and not predtym:
                spravy.append((inst, True, f"🔴 inštancia {html.escape(inst)} na stroji {html.escape(str(d.get('agent') or ''))} "
                                           f"mlčí {int(ticho)} min — žiadny heartbeat počas seansy (platforma spadla "
                                           f"alebo zamrzla; stop účtu beží v EA / NT ďalej)"))
            elif predtym and ticho is not None and ticho <= minuty:
                spravy.append((inst, False, f"🟢 inštancia {html.escape(inst)} sa znova hlási"))
        for inst in [i for i in self.instances_reported if i not in sledovane]:
            self.instances_reported.pop(inst, None)        # nasadenie zmizlo - nesledovať
        return spravy

    # -- stroje ---------------------------------------------------------------
    def machine_messages(self, now: float) -> tuple[list[tuple[str, bool, str]], bool]:
        hub = self.ctx.hub
        if getattr(hub, "deploy", None) is None:
            return [], False
        limit = float(hub.agent_timeout) + OFFLINE_GRACE
        if now - self.started < limit:
            return [], False   # po štarte hubu sa agenti ešte neohlásili
        agents = self.ctx.agents()   # kópia cez kontext — na zámok ani slovníky hubu plugin nesiaha (M-HUB-11)
        spravy: list[tuple[str, bool, str]] = []
        zmena = False
        for name in hub.deploy.active_agents():
            a = agents.get(name) or {}
            ticho = now - float(a.get("last_seen") or 0)
            online = ticho <= limit
            predtym = self.reported.get(name)
            dole = (f"🔴 stroj {html.escape(name)} sa neozval {int(ticho // 60)} min — nasadenia na ňom bežia ďalej, "
                    f"ale bez dohľadu a bez príkazov z webapp")
            if predtym is None:
                if not online:   # prvé pozorovanie: hlásiť len problém
                    spravy.append((name, online, dole))
                else:
                    self.reported[name] = True
                    zmena = True
            elif predtym and not online:
                spravy.append((name, online, dole))
            elif not predtym and online:
                spravy.append((name, online, f"🟢 stroj {html.escape(name)} sa znova hlási"))
        return spravy, zmena

    # -- odosielanie telemetrie ----------------------------------------------
    def ship_messages(self, now: float) -> tuple[list[tuple[str, str, str]], bool]:
        """Stroj je online, ale spool sa mu nedarí poslať (`live.ship.last_error` v heartbeate) dlhšie ako
        `SHIP_GRACE` — grafy a obchody na hube starnú, hoci heartbeat chodí (zvyšok auditu M-HUB-6). Vek chyby
        sa meria hodinami hubu od prvého heartbeatu, ktorý ju niesol (hodiny stroja sa neporovnávajú).
        Vráti `([(stroj, ohlásená chyba, text)], zmenil sa stav)`."""
        hub = self.ctx.hub
        if getattr(hub, "deploy", None) is None:
            return [], False
        agents = self.ctx.agents()
        aktivne = set(hub.deploy.active_agents())
        spravy: list[tuple[str, str, str]] = []
        zmena = False
        for name in sorted(set(self.ship_since) - aktivne):   # stroj už nemá nasadenie — nesledovať
            self.ship_since.pop(name, None)
            zmena = zmena or bool(self.ship_reported.pop(name, ""))
        for name in sorted(aktivne):
            a = agents.get(name) or {}
            if not a.get("online"):
                continue   # ticho celého stroja hlási `machine_messages`; posledný známy `ship` je vtedy starý
            ship = (a.get("live") or {}).get("ship") or {}
            chyba = str(ship.get("last_error") or "")
            if not chyba:
                self.ship_since.pop(name, None)
                if self.ship_reported.get(name):
                    spravy.append((name, "", f"🟢 stroj {html.escape(name)} znova posiela telemetriu"))
                continue
            od = self.ship_since.setdefault(name, now)
            if now - od >= SHIP_GRACE and not self.ship_reported.get(name):
                spravy.append((name, chyba, f"⚠️ stroj {html.escape(name)} už {int((now - od) // 60)} min neposiela "
                                            f"telemetriu na hub: {html.escape(chyba[:300])}"))
        return spravy, zmena

    # -- pluginy --------------------------------------------------------------
    @staticmethod
    def plugin_problem(p: dict[str, Any], now: float) -> str:
        if p.get("load_error"):
            return f"nenačítal sa: {p['load_error']}"
        if not p.get("enabled"):
            return ""
        if p.get("tick_started") and now - float(p["tick_started"]) > float(p.get("max_tick") or 600):
            return f"visí {int((now - float(p['tick_started'])) // 60)} min"
        if p.get("errors") and p.get("error_since") and now - float(p["error_since"]) >= PLUGIN_GRACE:
            return f"padá {int((now - float(p['error_since'])) // 60)} min: {p.get('last_error')}"
        return str(p.get("problem") or "")

    def plugin_messages(self, now: float) -> list[tuple[str, str, str]]:
        spravy = []
        for p in self.ctx.plugins():
            name = p["name"]
            if name == self.name:
                continue
            problem = self.plugin_problem(p, now)
            predtym = self.plugins_reported.get(name, "")
            titul = html.escape(p.get("title") or name)
            if problem and not predtym:
                spravy.append((name, problem, f"⚠️ plugin {titul}: {html.escape(problem)}"))
            elif predtym and not problem:
                spravy.append((name, "", f"🟢 plugin {titul} je znova v poriadku"))
        return spravy

    # -- tick -----------------------------------------------------------------
    def tick(self) -> list[str]:
        if not self.ctx.can_notify:
            return []
        now = self.ctx.clock()
        stroje, zmena = self.machine_messages(now)
        odoslane: list[str] = []
        try:
            for name, online, text in stroje:
                self.ctx.notify(text)
                self.reported[name] = online
                odoslane.append(text)
                zmena = True
            odosielanie, zmena_ship = self.ship_messages(now)
            zmena = zmena or zmena_ship
            for name, chyba, text in odosielanie:
                self.ctx.notify(text)
                self.ship_reported[name] = chyba
                odoslane.append(text)
                zmena = True
            for inst, mlci, text in self.instance_messages(now):
                self.ctx.notify(text)
                self.instances_reported[inst] = mlci
                odoslane.append(text)
                zmena = True
            for name, problem, text in self.plugin_messages(now):
                self.ctx.notify(text)
                self.plugins_reported[name] = problem
                odoslane.append(text)
                zmena = True
        except NotifyError as exc:
            self.ctx.log.warning("telegram: %s", exc)
        if zmena:
            self._save()
        return odoslane

    def status(self) -> dict[str, Any]:
        return {"offline": sorted(n for n, v in self.reported.items() if not v),
                "ship_bad": sorted(n for n, v in self.ship_reported.items() if v),
                "plugins_bad": sorted(n for n, v in self.plugins_reported.items() if v),
                "instances_silent": sorted(n for n, v in self.instances_reported.items() if v)}
