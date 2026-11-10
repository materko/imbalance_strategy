"""Týždenný export ForexFactory → kalendár stratégie SPRÁVY (naživo aj v repozitári).

Kalendár stratégie (`tradebot/strategies/spravy/calendar.json`) sa dopĺňa ručne raz za rok a úrady termíny
zverejňujú postupne — typ, ktorému termíny dôjdu, stratégia naživo ticho prestane obchodovať (audit 9. 11. 2026,
M-CORE-3). Export ForexFactory, ktorý hub aj tak denne sťahuje, má presné časy na aktuálny týždeň. Po každom
stiahnutí sa preto porovná s kalendárom (`calendar.week_diff`) a rozdiel ide dvoma cestami:

* **naživo, hneď** — do nasadení stratégií s poľami `newsAdd` / `newsSkip` na hube (`DeployStore`). Stroj si zmenu
  prevezme bežným zosúladením, bez novej DLL. Plugin spravuje len svoje záznamy: čo do nasadenia napísal človek,
  ostáva. Správa, ktorá je v kalendári a vo feede ju niet, sa **nevynecháva** (len oznámi) — môže to byť aj názov,
  ktorý nepoznáme;
* **do repozitára, najviac raz za mesiac** — správy v bežnom čase svojho typu sa dopíšu do `calendar.json` a do
  vygenerovaného `SpravyCalendar.cs` a pushnú z vlastného klonu pluginu (ten istý mechanizmus ako živé dáta,
  `livedata.gitpush`). Backtest a ďalšia DLL ich tak majú tiež. Bez `push` v configu sa len zbierajú.

Config (`hub_data/plugins/ff_calendar/config.json`):

    {"strategy_sync": true,
     "push": {"remote": "git@github.com:<kto>/<repo>.git", "ssh_key": "../livedata/deploy_key", "branch": "main",
              "author": "TradeBot hub <hub@tradebot.local>"}}

Stav je v `sync.json`. Každú zmenu plugin oznámi do Telegramu hubu a do logu udalostí (`plugin_calendar_sync`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import html
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..base import NotifyError, read_json, write_json
from .feed import NY, feed_week

__all__ = ["CalendarSync", "MAX_ADDS", "KEEP_DAYS"]

#: Viac pridaných správ za týždeň než toto je skoro určite pokazený feed — nič sa nezapíše, len oznámi.
MAX_ADDS = 12
#: Spravované záznamy staršie než toľko dní sa z nasadení odstránia (pri najbližšej zmene).
KEEP_DAYS = 30
#: Podadresár repozitára, do ktorého sa pushuje, a súbory v ňom.
REPO_SUB = "tradebot/strategies/spravy"
REPO_FILES = ("calendar.json", "ports/csharp/SpravyCalendar.cs")


def _cal():
    from tradebot.strategies.spravy import calendar

    return calendar


def _news_strategy(key: str) -> bool:
    """Stratégia má polia `newsAdd` a `newsSkip` (SPRÁVY a jej porty) — podľa configu, nie podľa mena."""
    try:
        from tradebot.strategies import get_spec

        polia = {f.name for f in dataclasses.fields(get_spec(key).config_cls)}
    except Exception:  # noqa: BLE001 - neznáma stratégia, config bez dataclass
        return False
    return {"newsAdd", "newsSkip"} <= polia


class CalendarSync:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        st = read_json(ctx.path("sync.json"), {}) or {}
        self.state: dict[str, Any] = st if isinstance(st, dict) else {}
        self.state.setdefault("add", [])        # [[deň, "HH:MM", typ]] spravované naprieč týždňami
        self.state.setdefault("skip", [])       # [[deň, typ]]
        self.state.setdefault("applied", {})    # nasadenie -> {"add": [...], "skip": [...]} čo doň plugin napísal
        self.state.setdefault("record", [])     # [[deň, typ]] čaká na zápis do repozitára
        self.state.setdefault("unrecord", [])
        self.state.setdefault("told", "")       # odtlačok posledného oznámeného rozdielu
        self.state.setdefault("pushed", "")     # mesiac posledného pushu
        self.last: dict[str, Any] = {}
        self.last_error = ""

    def _save(self) -> None:
        write_json(self.ctx.path("sync.json"), self.state)

    # -- rozdiel --------------------------------------------------------------- #

    def run(self, events: list[dict[str, Any]], *, push: dict[str, Any] | None = None, force_push: bool = False) -> dict[str, Any]:
        """Jedno kolo po stiahnutí exportu. Vráti súhrn (aj pre `status` a CLI)."""
        cal = _cal()
        now = self.ctx.clock()
        week = feed_week(events)
        if week is None:
            return {}
        diff = cal.week_diff(events, week)
        if len(diff["add"]) > MAX_ADDS:
            self.last_error = f"feed chce pridať {len(diff['add'])} správ za týždeň — vyzerá pokazený, nič sa nemení"
            self.ctx.log.warning("calendar sync: %s", self.last_error)
            return {"error": self.last_error}
        self.last_error = ""
        dni = {date.fromordinal(week.toordinal() + i).isoformat() for i in range(7)}
        stare = date.fromordinal(datetime.fromtimestamp(now, NY).date().toordinal() - KEEP_DAYS).isoformat()

        # spravované záznamy: tento týždeň nanovo z feedu (oprava vo feede sa prenesie), ostatné týždne ostávajú
        add = [a for a in self.state["add"] if a[0] not in dni and a[0] >= stare]
        skip = [s for s in self.state["skip"] if s[0] not in dni and s[0] >= stare]
        add += [[d.isoformat(), hhmm, typ] for d, hhmm, typ in diff["add"]]
        skip += [[d.isoformat(), typ] for d, typ in diff["skip"]]
        self.state["add"], self.state["skip"] = sorted(add), sorted(skip)

        zmenene = self._apply()
        for kluc in ("record", "unrecord"):
            spolu = {tuple(x) for x in self.state[kluc]} | {(d.isoformat(), typ) for d, typ in diff[kluc]}
            self.state[kluc] = sorted(list(x) for x in spolu)
        self._drop_recorded(cal)
        self._tell(week, diff, zmenene)
        commit = self._push(cal, now, push, force_push)
        self._save()
        self.last = {"week": week.isoformat(), "add": cal.fmt_add(diff["add"]), "skip": cal.fmt_skip(diff["skip"]),
                     "missing": cal.fmt_skip(diff["missing"]), "deployments": zmenene,
                     "pending_repo": len(self.state["record"]) + len(self.state["unrecord"]), "commit": commit}
        return self.last

    # -- nasadenia ------------------------------------------------------------- #

    def _apply(self) -> list[str]:
        """Zapíše spravované záznamy do nasadení so správami; vráti id tých, ktoré sa zmenili."""
        cal = _cal()
        store = getattr(self.ctx.hub, "deploy", None)
        if store is None:
            return []
        chceme_add = {(date.fromisoformat(d), hhmm, typ) for d, hhmm, typ in self.state["add"]}
        chceme_skip = {(date.fromisoformat(d), typ) for d, typ in self.state["skip"]}
        zmenene: list[str] = []
        zive: set[str] = set()
        for dep in store.deployments():
            if not dep.get("active") or not _news_strategy(str(dep.get("strategy") or "")):
                continue
            zive.add(dep["id"])
            cfg = dict(dep.get("config") or {})
            pred = self.state["applied"].get(dep["id"]) or {}
            moje_add = {(date.fromisoformat(d), hhmm, typ) for d, hhmm, typ in pred.get("add") or []}
            moje_skip = {(date.fromisoformat(d), typ) for d, typ in pred.get("skip") or []}
            try:
                rucne_add = set(cal.parse_add(str(cfg.get("newsAdd") or ""))) - moje_add
                rucne_skip = set(cal.parse_skip(str(cfg.get("newsSkip") or ""))) - moje_skip
            except ValueError:
                self.ctx.log.warning("calendar sync: nasadenie %s má nečitateľné newsAdd / newsSkip — nechávam ho tak", dep["id"])
                continue
            nove = {"newsAdd": cal.fmt_add(sorted(rucne_add | chceme_add)), "newsSkip": cal.fmt_skip(sorted(rucne_skip | chceme_skip))}
            if nove["newsAdd"] != str(cfg.get("newsAdd") or "") or nove["newsSkip"] != str(cfg.get("newsSkip") or ""):
                store.update_deployment(dep["id"], {"config": {**cfg, **nove}}, by="ff_calendar")
                zmenene.append(dep["id"])
            self.state["applied"][dep["id"]] = {"add": self.state["add"], "skip": self.state["skip"]}
        for dep_id in [i for i in self.state["applied"] if i not in zive]:
            self.state["applied"].pop(dep_id, None)
        return zmenene

    # -- oznámenie ------------------------------------------------------------- #

    def _tell(self, week: date, diff: dict[str, list], zmenene: list[str]) -> None:
        cal = _cal()
        if not (diff["add"] or diff["skip"] or diff["missing"]):
            return
        text = (f"<b>📅 Kalendár SPRÁVY, týždeň od {week.day}. {week.month}.</b>"
                + (f"\npridané: {html.escape(cal.fmt_add(diff['add']))}" if diff["add"] else "")
                + (f"\nvynechané (presunuté): {html.escape(cal.fmt_skip(diff['skip']))}" if diff["skip"] else "")
                + (f"\n⚠️ v kalendári sú, ForexFactory ich tento týždeň nemá: {html.escape(cal.fmt_skip(diff['missing']))}"
                   " — nevynechávam, over ručne" if diff["missing"] else "")
                + (f"\nnasadenia: {html.escape(', '.join(zmenene))}" if zmenene else ""))
        odtlacok = hashlib.sha1(json.dumps([week.isoformat(), diff], default=str, sort_keys=True).encode()).hexdigest()[:16]
        if odtlacok == self.state["told"] and not zmenene:
            return
        self.ctx.event("calendar_sync", week=week.isoformat(), add=cal.fmt_add(diff["add"]),
                       skip=cal.fmt_skip(diff["skip"]), missing=cal.fmt_skip(diff["missing"]), deployments=zmenene)
        if self.ctx.can_notify:
            try:
                self.ctx.notify(text)
            except NotifyError as exc:
                self.ctx.log.warning("calendar sync: telegram: %s", exc)
                return   # odtlačok sa neuloží — oznámi sa pri ďalšom stiahnutí
        self.state["told"] = odtlacok

    # -- repozitár ------------------------------------------------------------- #

    def _drop_recorded(self, cal) -> None:
        """Čo už v nainštalovanom `calendar.json` je (alebo z neho už zmizlo), netreba pushovať."""
        dates = {typ: set(ev["dates"]) for typ, ev in cal.load()["events"].items()}
        self.state["record"] = [x for x in self.state["record"] if x[0] not in dates.get(x[1], set())]
        self.state["unrecord"] = [x for x in self.state["unrecord"] if x[0] in dates.get(x[1], set())]

    def _push(self, cal, now: float, cfg: dict[str, Any] | None, force: bool) -> str:
        """Dopíše čakajúce správy do `calendar.json` + `SpravyCalendar.cs` vo vlastnom klone a pushne. Najviac raz
        za mesiac (`force` hneď). Vráti commit alebo prázdny reťazec."""
        if not (self.state["record"] or self.state["unrecord"]) or not cfg or not cfg.get("remote"):
            return ""
        mesiac = datetime.fromtimestamp(now, NY).strftime("%Y-%m")
        if not force and self.state["pushed"] == mesiac:
            return ""
        record = [(date.fromisoformat(d), typ) for d, typ in self.state["record"]]
        unrecord = [(date.fromisoformat(d), typ) for d, typ in self.state["unrecord"]]
        novy, zmien = cal.with_changes(cal.load(), record, unrecord)
        if not zmien:
            return ""
        out = self.ctx.path("calendar_out")
        (out / "ports" / "csharp").mkdir(parents=True, exist_ok=True)
        (out / "calendar.json").write_text(cal.dumps(novy), encoding="utf-8", newline="\n")
        (out / "ports" / "csharp" / "SpravyCalendar.cs").write_text(cal.csharp_source(novy), encoding="utf-8", newline="\n")
        popis = ", ".join(f"{typ} {d.isoformat()}" for d, typ in sorted(record)[:8]) + (" …" if len(record) > 8 else "")
        sprava = (f"Doplň kalendár SPRÁVY z ForexFactory ({zmien} termínov: {popis or 'presuny'})\n\n"
                  "Termíny potvrdené týždenným exportom ForexFactory, ktoré v calendar.json chýbali alebo sa presunuli; "
                  "zapísal plugin hubu ff_calendar.")
        try:
            from ..livedata import gitpush

            kluc = str(cfg.get("ssh_key") or "")
            commit = gitpush.push_files(
                self.ctx.path("repo"), str(cfg["remote"]), str(cfg.get("branch") or "main"), out, list(REPO_FILES), sprava,
                str(cfg.get("author") or "TradeBot hub <hub@tradebot.local>"), sub=REPO_SUB, log=self.ctx.log.info,
                ssh_key=((Path(kluc) if Path(kluc).is_absolute() else self.ctx.path(kluc)) if kluc else None))
        except Exception as exc:  # noqa: BLE001 - push nesmie zhodiť plugin; skúsi sa pri ďalšom stiahnutí
            self.last_error = f"push kalendára: {type(exc).__name__}: {exc}"
            self.ctx.log.warning("calendar sync: %s", self.last_error)
            return ""
        self.state["pushed"] = mesiac
        if commit:
            self.ctx.event("calendar_push", commit=commit[:10], changes=zmien)
        return commit
