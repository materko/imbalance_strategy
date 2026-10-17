"""Plugin `watchdog` (docs/LIVE.md, „Strážca (hub)“): ohlási do Telegramu, čo zvnútra ohlásiť nejde.

**Stroje** s aktívnym nasadením, ktoré prestali posielať heartbeat, a ich návrat — spadnutý agent,
vypnutý stroj alebo výpadok internetu doma vidno len zvonka. Offline = `now - last_seen >
agent_timeout + OFFLINE_GRACE` a hub beží aspoň toľko (po reštarte hubu sú všetci agenti chvíľu
„offline“, kým sa neohlásia).

**Pluginy**: nenačítal sa, `tick` padá dlhšie ako `PLUGIN_GRACE`, `tick` visí dlhšie ako jeho
`max_tick`, alebo plugin sám hlási `problem` (napr. kalendár sa nedá stiahnuť) — a návrat do poriadku.

Prvé pozorovanie hlási len problém. Čo naposledy ohlásil, je v `state.json` pluginu, aby po
reštarte nehlásil to isté znova (prvý štart prevezme starý `HUB_TELEGRAM_STATE`).
"""

from __future__ import annotations

import html
from typing import Any

from tradebot.core.paths import HUB_TELEGRAM_STATE

from ..base import HubPlugin, NotifyError, read_json, write_json

#: Navyše k `agent_timeout`, kým sa stroj ohlási ako nedostupný (krátky výpadok siete nespamuje).
OFFLINE_GRACE = 120.0
#: Tak dlho musí plugin padať, kým sa ohlási (jedna chyba siete nič).
PLUGIN_GRACE = 300.0


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

    def _save(self) -> None:
        write_json(self.ctx.path("state.json"), {"online": self.reported, "plugins": self.plugins_reported})

    # -- stroje ---------------------------------------------------------------
    def machine_messages(self, now: float) -> tuple[list[tuple[str, bool, str]], bool]:
        hub = self.ctx.hub
        if getattr(hub, "deploy", None) is None:
            return [], False
        limit = float(hub.agent_timeout) + OFFLINE_GRACE
        if now - self.started < limit:
            return [], False   # po štarte hubu sa agenti ešte neohlásili
        with hub._lock:
            agents = {n: dict(a) for n, a in hub.agents.items()}
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
                "plugins_bad": sorted(n for n, v in self.plugins_reported.items() if v)}
