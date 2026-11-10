"""Plugin `ff_calendar`: červené (High impact) udalosti ForexFactory → upozornenie do Telegramu hubu.

Súbory v `hub_data/plugins/ff_calendar/`: `config.json` (voliteľný), `state.json` (čo už odišlo:
udalosť → minúty pred; reštart hubu nič nezopakuje), `cache.json` (posledný export).

Sťahuje sa **raz denne** o `refresh` (predvolene 07:00 v `tz`). Navyše, keď export ešte drží
minulý týždeň (prehadzuje sa v nedeľu), skúša to každú hodinu — inak by vypadli pondelkové ranné
ázijské správy. Neúspech = ide sa zo zásoby a skúsi sa znova o 15 min; dlhý výpadok či chýbajúci
týždeň plugin hlási ako `problem` a strážca (`watchdog`) ho pošle do Telegramu.

Po každom úspešnom stiahnutí sa export porovná s kalendárom stratégie SPRÁVY a rozdiel sa zapíše do jej
nasadení (`newsAdd` / `newsSkip`) a raz za mesiac do repozitára — `sync.py`. Vypína sa `"strategy_sync": false`.
"""

from __future__ import annotations

import argparse
import html
import sys
import urllib.error
from datetime import datetime, timedelta
from typing import Any, Callable

from ..base import HubPlugin, NotifyError, read_json, write_json
from . import alerts
from .alerts import CalendarConfig
from .feed import FF_URL, NY, feed_week, fetch, ny_week, parse_feed
from .sync import CalendarSync

#: Po neúspešnom stiahnutí znova o toľko.
RETRY_FAIL = 900.0
#: Keď export ešte nemá aktuálny týždeň, znova o toľko.
RETRY_WEEK = 3600.0
#: Bez úspešného stiahnutia dlhšie ako toto = problém.
STALE_AFTER = 26 * 3600.0
#: Toľko po začiatku týždňa (New York) bez nového exportu = problém.
WEEK_LATE = 12 * 3600.0
#: Odoslané upozornenia sa pamätajú ešte toľko po udalosti.
KEEP_SENT = 3 * 86400.0


class FFCalendar(HubPlugin):
    title = "Kalendár ForexFactory"
    interval = 20.0
    max_tick = 300.0

    def __init__(self, fetcher: Callable[[str], Any] = fetch) -> None:
        self.fetcher = fetcher
        self.events: list[dict[str, Any]] = []
        self.fetched = 0.0      # posledný pokus
        self.fetched_ok = 0.0   # posledný úspech
        self.last_error = ""
        self.sent: dict[str, list[float]] = {}
        self.cfg = CalendarConfig()
        self.sync: CalendarSync | None = None

    # -- stav -----------------------------------------------------------------
    def setup(self, ctx) -> None:
        super().setup(ctx)
        self.started = ctx.clock()
        self.sync = CalendarSync(ctx)
        st = read_json(ctx.path("state.json"), {}) or {}
        try:
            self.sent = {str(k): [float(x) for x in v] for k, v in (st.get("sent") or {}).items()}
        except (AttributeError, TypeError, ValueError):
            self.sent = {}
        cache = read_json(ctx.path("cache.json"), {}) or {}
        if isinstance(cache, dict):
            self.events = parse_feed(cache.get("feed"))
            self.fetched_ok = self.fetched = float(cache.get("fetched") or 0) if self.events else 0.0

    def _save_state(self) -> None:
        now = self.ctx.clock()
        self.sent = {k: v for k, v in self.sent.items() if float(k.split("|", 1)[0]) > now - KEEP_SENT}
        write_json(self.ctx.path("state.json"), {"sent": self.sent})

    def config(self) -> CalendarConfig:
        self.cfg = CalendarConfig.from_dict(self.ctx.config())
        return self.cfg

    # -- zdroj ----------------------------------------------------------------
    def _last_scheduled(self, now: float) -> float:
        """Posledný čas `refresh` (v `tz`) pred `now`."""
        z = self.cfg.zone()
        h, m = self.cfg.refresh_hm()
        d = datetime.fromtimestamp(now, z)
        t = d.replace(hour=h, minute=m, second=0, microsecond=0)
        if t > d:
            t -= timedelta(days=1)
        return t.timestamp()

    def week_behind(self, now: float) -> bool:
        fw = feed_week(self.events)
        return fw is None or fw < ny_week(now)

    def need_fetch(self, now: float) -> str:
        """Prečo stiahnuť teraz (prázdne = netreba)."""
        if self.fetched > self.fetched_ok and now - self.fetched < RETRY_FAIL:
            return ""
        if not self.events:
            return "zásoba je prázdna"
        if self.fetched < self._last_scheduled(now):
            return "denné stiahnutie"
        if self.week_behind(now) and now - self.fetched >= RETRY_WEEK:
            return "export ešte nemá tento týždeň"
        return ""

    def refresh(self, force: bool = False) -> bool:
        now = self.ctx.clock()
        if not force and not self.need_fetch(now):
            return False
        self.fetched = now
        try:
            raw = self.fetcher(self.cfg.url or FF_URL)
            events = parse_feed(raw)
            if not events:
                raise ValueError("prázdny kalendár")
        except (OSError, ValueError, urllib.error.URLError) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.ctx.log.warning("stiahnutie: %s", self.last_error)
            return False
        self.events, self.fetched_ok, self.last_error = events, now, ""
        write_json(self.ctx.path("cache.json"), {"fetched": now, "url": self.cfg.url or FF_URL, "feed": raw})
        self.sync_strategy()
        return True

    def sync_strategy(self, force_push: bool = False) -> dict[str, Any]:
        """Export → kalendár stratégie SPRÁVY (nasadenia na hube, raz za mesiac repozitár). Chyba plugin nezhodí:
        upozornenia na správy musia chodiť ďalej."""
        raw = self.ctx.config()
        if self.sync is None or raw.get("strategy_sync", True) is False:
            return {}
        try:
            return self.sync.run(self.events, push=raw.get("push") if isinstance(raw.get("push"), dict) else None,
                                 force_push=force_push)
        except Exception as exc:  # noqa: BLE001
            self.sync.last_error = f"{type(exc).__name__}: {exc}"
            self.ctx.log.exception("calendar sync zlyhal: %s", self.sync.last_error)
            return {"error": self.sync.last_error}

    # -- tick -----------------------------------------------------------------
    def tick(self) -> None:
        self.config()
        self.refresh()
        self.send_due()

    def send_due(self) -> list[str]:
        """Pošle splatné upozornenia; Telegram dole = neuloží sa a skúsi sa v ďalšom ticku."""
        if not self.ctx.can_notify:
            return []
        now = self.ctx.clock()
        odoslane = []
        for group, minuty in alerts.due(self.events, self.cfg, self.sent, now):
            text = alerts.message(group, self.cfg, now)
            try:
                self.ctx.notify(text, chats=self.cfg.chats or None)
            except NotifyError as exc:
                self.ctx.log.warning("telegram: %s", exc)
                break
            for e in group:
                k = alerts.event_key(e)
                self.sent[k] = sorted(set(self.sent.get(k, [])) | set(minuty), reverse=True)
            odoslane.append(text)
        if odoslane:
            self._save_state()
        return odoslane

    def problem(self, now: float) -> str | None:
        bez = now - (self.fetched_ok or self.started)
        if self.last_error and bez > STALE_AFTER:
            return f"kalendár sa nedá stiahnuť {int(bez // 3600)} h ({self.last_error}) — upozornenia idú zo starej zásoby"
        zaciatok = datetime.combine(ny_week(now), datetime.min.time(), tzinfo=NY).timestamp()
        if self.fetched and self.week_behind(now) and now - zaciatok > WEEK_LATE:
            return "ForexFactory ešte nemá tento týždeň — upozornenia nepôjdu, kým ho nedá"
        return None

    def status(self) -> dict[str, Any]:
        now = self.ctx.clock()
        nxt = [e for e in alerts.wanted(self.events, self.cfg) if e["ts"] >= now]
        return {"events": len(self.events), "watched": len(alerts.wanted(self.events, self.cfg)),
                "fetched_ok": self.fetched_ok, "last_error": self.last_error,
                "remind_min": self.cfg.remind_min, "tz": self.cfg.tz, "refresh": self.cfg.refresh,
                "next": (f"{nxt[0]['country']} {nxt[0]['title']} "
                         f"{alerts.when(nxt[0]['ts'], now, self.cfg.zone())}") if nxt else "",
                "sync": {**self.sync.last, "error": self.sync.last_error} if self.sync is not None else None,
                "problem": self.problem(now)}

    def upcoming(self, now: float | None = None) -> list[dict[str, Any]]:
        """Budúce sledované udalosti s časom v `tz` a plánovanými upozorneniami."""
        now = self.ctx.clock() if now is None else now
        z = self.cfg.zone()
        out = []
        for e in alerts.wanted(self.events, self.cfg):
            if e["ts"] < now - alerts.AT_GRACE:
                continue
            d = datetime.fromtimestamp(e["ts"], z)
            out.append({**e, "local": f"{alerts.DNI[d.weekday()]} {d.strftime('%d.%m. %H:%M')}",
                        "alerts": [datetime.fromtimestamp(e["ts"] - o * 60, z).strftime("%H:%M")
                                   for o in self.cfg.remind_min],
                        "sent": self.sent.get(alerts.event_key(e), [])})
        return out

    # -- Telegram -------------------------------------------------------------
    def views(self) -> dict[str, str]:
        return {"upcoming": "📅 Udalosti"}

    def view(self, name: str) -> str:
        if name != "upcoming":
            raise KeyError(name)
        self.config()
        now = self.ctx.clock()
        c = self.cfg
        hlava = (f"<b>📅 {'Červené správy' if [i.lower() for i in c.impact] == ['high'] else '/'.join(c.impact)}</b>"
                 f" · {html.escape(','.join(c.currencies) or 'všetky meny')} · čas {html.escape(c.tz)}")
        rows = self.upcoming(now)
        riadky, den = [hlava], None
        z = c.zone()
        for e in rows[:40]:
            d = datetime.fromtimestamp(e["ts"], z)
            if d.date() != den:
                den = d.date()
                riadky.append(f"\n<b>{alerts.DNI[d.weekday()]} {d.day}. {d.month}.</b>")
            cisla = " · ".join(f"{n} {html.escape(e[k])}" for n, k in (("progn.", "forecast"), ("pred.", "previous"))
                               if e[k])
            riadky.append(f"{d.strftime('%H:%M')} <b>{html.escape(e['country'])}</b> {html.escape(e['title'])}"
                          + (f" · {cisla}" if cisla else "") + (" ✓" if e["sent"] else ""))
        if len(rows) > 40:
            riadky.append(f"… a ďalších {len(rows) - 40}")
        if not rows:
            riadky.append("\nTento týždeň už nič sledované.")
        poz = ", ".join(f"{m:g}" for m in c.remind_min)
        riadky.append(f"\n<i>Upozornenie {poz} min pred · ✓ = už odišlo</i>")
        if p := self.problem(now):
            riadky.append(f"⚠️ {html.escape(p)}")
        return "\n".join(riadky)

    # -- príkaz ---------------------------------------------------------------
    def cli(self, argv: list[str]) -> int:
        ap = argparse.ArgumentParser(prog="python -m tester.hub plugin ff_calendar",
                                     description="červené správy tohto týždňa v čase hubu a kedy príde upozornenie")
        ap.add_argument("--fetch", action="store_true", help="stiahnuť export hneď (inak zo zásoby hubu)")
        ap.add_argument("--test", action="store_true", help="poslať najbližšiu udalosť do Telegramu na skúšku")
        ap.add_argument("--sync", action="store_true", help="porovnať export s kalendárom stratégie SPRÁVY a zapísať rozdiel do nasadení")
        ap.add_argument("--push", action="store_true", help="s --sync: čakajúce termíny pushnúť do repozitára hneď (nie až o mesiac)")
        args = ap.parse_args(argv)
        c = self.config()
        if (args.fetch or not self.events) and not self.refresh(force=True):
            print(f"stiahnutie zlyhalo: {self.last_error}")
        print(f"{'/'.join(c.impact)} · {','.join(c.currencies) or 'všetky meny'} · upozornenia "
              f"{', '.join(f'{m:g}' for m in c.remind_min)} min pred · {c.tz} · stiahnutie denne o {c.refresh} · "
              f"Telegram {'áno' if self.ctx.can_notify else 'NENASTAVENÝ (hub_data/telegram.json)'}")
        rows = self.upcoming()
        for e in rows:
            odislo = f"  odišlo {','.join(f'{m:g}' for m in e['sent'])}" if e["sent"] else ""
            print(f"{e['local']:<16}{e['country']:<5}{e['title'][:44]:<46}upozorní {', '.join(e['alerts'])}{odislo}")
        if not rows:
            print("tento týždeň už nič sledované")
        if p := self.problem(self.ctx.clock()):
            print(f"POZOR: {p}")
        if args.sync or args.push:
            s = self.sync_strategy(force_push=args.push)
            if s.get("error"):
                print(f"kalendár SPRÁVY: {s['error']}")
            elif s:
                print(f"kalendár SPRÁVY, týždeň od {s['week']}: pridať [{s['add']}] vynechať [{s['skip']}] "
                      f"chýba vo feede [{s['missing']}] · zmenené nasadenia: {', '.join(s['deployments']) or 'žiadne'} · "
                      f"do repozitára čaká {s['pending_repo']}" + (f" · commit {s['commit'][:10]}" if s.get("commit") else ""))
        if args.test:
            if not rows:
                print("nie je čo poslať", file=sys.stderr)
                return 1
            group = [e for e in rows if e["ts"] == rows[0]["ts"]]
            self.ctx.notify("🧪 test · " + alerts.message(group, c, self.ctx.clock()), chats=c.chats or None)
            print("test odoslaný")
        return 0
