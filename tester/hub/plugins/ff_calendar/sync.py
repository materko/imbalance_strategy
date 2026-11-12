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

Export má len aktuálny týždeň, takže koniec pokrytia sám neposunie. Na to je `extend`: raz za týždeň (kým niektorému
typu končí pokrytie, denne) prečíta **oficiálne rozvrhy úradov** (`official.py`) a termíny za koncom kalendára
pridá tými istými dvoma cestami — naživo hneď, do repozitára hneď. U typov s úplným rozvrhom (BLS, FOMC) opraví aj
budúce termíny, ktoré sa s rozvrhom rozchádzajú (najviac `MAX_FIXES` na typ, inak len oznámi). Typ, ktorému sa
pokrytie ani tak nepredĺži (RETAIL nemá oficiálny zdroj), hlási plugin ako `problem` `PROBLEM_DAYS` dní vopred.

Config (`hub_data/plugins/ff_calendar/config.json`):

    {"strategy_sync": true, "official": true, "official_days": 75,
     "push": {"remote": "git@github.com:<kto>/<repo>.git", "ssh_key": "../livedata/deploy_key", "branch": "main",
              "author": "TradeBot hub <hub@tradebot.local>"}}

Stav je v `sync.json`. Každú zmenu plugin oznámi do Telegramu hubu a do logu udalostí (`plugin_calendar_sync`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ..base import NotifyError, read_json, write_json
from . import official
from .feed import NY, feed_week

__all__ = ["CalendarSync", "MAX_ADDS", "KEEP_DAYS", "OFFICIAL_DAYS", "PROBLEM_DAYS", "MAX_FIXES"]

#: Viac pridaných správ za týždeň než toto je skoro určite pokazený feed — nič sa nezapíše, len oznámi.
MAX_ADDS = 12
#: Spravované záznamy staršie než toľko dní sa z nasadení odstránia (pri najbližšej zmene).
KEEP_DAYS = 30
#: Oficiálne rozvrhy sa čítajú raz za týždeň; kým niektorému typu končí pokrytie, raz za deň.
OFFICIAL_EVERY = 7 * 86400.0
OFFICIAL_DUE_EVERY = 86400.0
#: Typ, ktorému pokrytie končí do toľkých dní, sa predlžuje z oficiálneho zdroja (EA varuje 45 dní vopred).
OFFICIAL_DAYS = 75
#: Typ, ktorému pokrytie končí do toľkých dní a nikto ho nepredĺžil = `problem` pluginu (strážca → Telegram).
PROBLEM_DAYS = 30
#: Viac rozdielov oproti rozvrhu u jedného typu je skôr zmenená stránka než presun — nemení sa, len oznámi.
MAX_FIXES = 3
#: Viac nových termínov jedného typu naraz (CLAIMS má ~52 za rok) je skôr chyba rozboru.
MAX_EXTEND = 60
#: Typy, ktorých oficiálny zdroj je úplný rozvrh — termín kalendára, ktorý v ňom nie je, je presunutý.
FIX_TYPES = ("CPI", "NFP", "PPI", "JOLTS", "FOMC", "FOMC_MIN")
#: Typy, ktoré kalendár drží raz za mesiac (posledné vydanie mesiaca, ako ALFRED); BEA ich má niekedy viac.
ONE_PER_MONTH = ("GDP",)
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


def _feed_seen(cal, events: list[dict[str, Any]], dni: set[str]) -> dict[str, dict[str, str]]:
    """Typy správ, ktoré feed má v týždni `dni`: `{typ: {deň: "HH:MM"}}` — tým istým výberom ako `calendar.week_diff`."""
    known = cal.load()["events"]
    out: dict[str, dict[str, str]] = {}
    for e in events:
        if str(e.get("country") or "").upper() != "USD":
            continue
        typ = cal.ff_type(str(e.get("title") or ""))
        if typ is None or typ not in known:
            continue
        local = datetime.fromtimestamp(float(e["ts"]), tz=NY)
        if local.date().isoformat() not in dni or not cal.FF_HOURS[0] <= local.hour < cal.FF_HOURS[1]:
            continue
        hhmm = f"{local.hour:02d}:{local.minute:02d}"
        byday = out.setdefault(typ, {})
        byday[local.date().isoformat()] = min(hhmm, byday.get(local.date().isoformat(), hhmm))
    return out


def _one_per_month(rows: list[tuple[date, str]]) -> list[tuple[date, str]]:
    """Posledné vydanie každého mesiaca."""
    out: dict[tuple[int, int], tuple[date, str]] = {}
    for d, hhmm in sorted(rows):
        out[(d.year, d.month)] = (d, hhmm)
    return sorted(out.values())


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
        self.state.setdefault("official_at", 0.0)   # posledné čítanie oficiálnych rozvrhov
        self.state.setdefault("official_told", "")
        self.last: dict[str, Any] = {}
        self.last_error = ""
        self.official: dict[str, Any] = dict(self.state.get("official") or {})

    def _save(self) -> None:
        self.state["official"] = self.official
        write_json(self.ctx.path("sync.json"), self.state)

    # -- pokrytie -------------------------------------------------------------- #

    def planned(self) -> dict[str, dict[date, str]]:
        """Čo naživo platí: `{typ: {deň: "HH:MM"}}` = kalendár + spravované `newsAdd` − spravované `newsSkip`."""
        events = _cal().load()["events"]
        out = {typ: {date.fromisoformat(d): ev["time_et"] for d in ev["dates"]} for typ, ev in events.items()}
        for d, hhmm, typ in self.state["add"]:
            if typ in out:
                out[typ][date.fromisoformat(d)] = hhmm
        for d, typ in self.state["skip"]:
            out.get(typ, {}).pop(date.fromisoformat(d), None)
        return out

    def coverage_end(self) -> dict[str, date]:
        """Posledný známy termín každého typu (kalendár aj spravované záznamy)."""
        return {typ: max(dni) for typ, dni in self.planned().items() if dni}

    def coverage_problem(self, now: float, days: int = PROBLEM_DAYS) -> str | None:
        """Typy, ktorým pokrytie končí do `days` dní a nikto ho nepredĺžil — stratégia by ich naživo ticho prestala
        obchodovať. Text pre `problem` pluginu."""
        dnes = datetime.fromtimestamp(now, NY).date()
        kratke = sorted((d, typ) for typ, d in self.coverage_end().items() if (d - dnes).days < days)
        if not kratke:
            return None
        return ("kalendár SPRÁVY končí: " + ", ".join(f"{typ} {d.isoformat()}" for d, typ in kratke)
                + " — oficiálny rozvrh ho nepredĺžil, doplň termíny do calendar.json alebo newsAdd")

    # -- oficiálne rozvrhy ------------------------------------------------------ #

    def extend(self, fetch, *, push: dict[str, Any] | None = None, horizon: int = OFFICIAL_DAYS,
               force: bool = False) -> dict[str, Any]:
        """Oficiálne rozvrhy úradov → termíny za koncom pokrytia (a opravy budúcich termínov u `FIX_TYPES`) do
        nasadení a hneď do repozitára. Raz za týždeň, kým niektorému typu končí pokrytie, raz za deň."""
        cal = _cal()
        now = self.ctx.clock()
        posledne = float(self.state.get("official_at") or 0)
        if not force and now - posledne < OFFICIAL_DUE_EVERY:
            return self.official
        dnes = datetime.fromtimestamp(now, NY).date()
        events = cal.load()["events"]
        plan = self.planned()
        konce = {typ: max(dni) for typ, dni in plan.items() if dni}
        due = sorted(t for t in events if t not in konce or (konce[t] - dnes).days < horizon)
        if not force and not due and now - posledne < OFFICIAL_EVERY:
            return self.official
        self.state["official_at"] = now
        typy = sorted(set(due) | {t for t in FIX_TYPES if t in events})
        found, errors = official.official_dates(
            typy, fetch, years=(dnes.year, dnes.year + 1),
            known_fomc=[date.fromisoformat(d) for d in events.get("FOMC", {}).get("dates", [])])

        adds: list[tuple[date, str, str]] = []
        skips: list[tuple[date, str]] = []
        for typ in typy:
            rows = found.get(typ) or []
            if typ in ONE_PER_MONTH:
                rows = _one_per_month(rows)
            buduce = [(d, h) for d, h in rows if d > dnes]
            if not buduce:
                continue
            moje = plan.get(typ, {})
            koniec = konce.get(typ, dnes)
            nove = [(d, h, typ) for d, h in buduce if d > koniec and d not in moje] if typ in due else []
            if len(nove) > MAX_EXTEND:
                errors[typ] = f"zdroj dáva {len(nove)} nových termínov naraz — vyzerá pokazený, nemením"
                nove = []
            oprav_add: list[tuple[date, str, str]] = []
            oprav_skip: list[tuple[date, str]] = []
            if typ in FIX_TYPES:
                rozvrh = dict(buduce)
                po = max(rozvrh)
                # Fed dáva rozvrh po celých rokoch: zasadnutie po poslednom v roku nie je, aj keď ho kalendár má
                if typ == "FOMC":
                    po = date(po.year, 12, 31)
                elif typ == "FOMC_MIN":
                    po = date((po - timedelta(days=official.MINUTES_AFTER)).year, 12, 31) + timedelta(days=official.MINUTES_AFTER)
                oprav_add = [(d, h, typ) for d, h in buduce if d <= koniec and d not in moje]
                oprav_skip = [(d, typ) for d in sorted(moje) if dnes < d <= po and d not in rozvrh]
                if len(oprav_add) + len(oprav_skip) > MAX_FIXES:
                    errors[typ] = (f"{len(oprav_add) + len(oprav_skip)} rozdielov oproti oficiálnemu rozvrhu — skôr "
                                   "zmenená stránka než presun, nemením (over ručne)")
                    oprav_add, oprav_skip = [], []
            adds += nove + oprav_add
            skips += oprav_skip

        zmenene: list[str] = []
        commit = ""
        if adds or skips:
            self.state["add"] = sorted(list(x) for x in {tuple(a) for a in self.state["add"]}
                                       | {(d.isoformat(), h, t) for d, h, t in adds})
            self.state["skip"] = sorted(list(x) for x in {tuple(s) for s in self.state["skip"]}
                                        | {(d.isoformat(), t) for d, t in skips})
            rec = {(d.isoformat(), t) for d, h, t in adds if h == events[t]["time_et"]}
            self.state["record"] = sorted(list(x) for x in {tuple(r) for r in self.state["record"]} | rec)
            self.state["unrecord"] = sorted(list(x) for x in {tuple(r) for r in self.state["unrecord"]}
                                            | {(d.isoformat(), t) for d, t in skips})
            self._drop_recorded(cal)
            zmenene = self._apply()
            commit = self._push(cal, now, push, True, zdroj="oficiálnych rozvrhov úradov")
        koniec_po = self.coverage_end()
        self.official = {
            "checked": now, "types": typy, "due": due,
            "added": cal.fmt_add(adds), "skipped": cal.fmt_skip(skips),
            "errors": dict(sorted(errors.items())), "deployments": zmenene, "commit": commit,
            "short": {t: d.isoformat() for t, d in sorted(koniec_po.items()) if (d - dnes).days < horizon},
        }
        self._tell_official(adds, skips, errors, zmenene, koniec_po, dnes, horizon)
        self._save()
        return self.official

    def _tell_official(self, adds, skips, errors, zmenene, konce, dnes, horizon) -> None:
        cal = _cal()
        po_typoch: dict[str, list[date]] = {}
        for d, _h, t in adds:
            po_typoch.setdefault(t, []).append(d)
        kratke = {t: d for t, d in konce.items() if (d - dnes).days < horizon}
        # chyba typu, ktorý netreba predĺžiť ani nemá čo opraviť, nie je správa — len stav
        chyby = {t: e for t, e in errors.items() if t in kratke or "rozdielov" in e or "pokazený" in e}
        if not (adds or skips or chyby):
            return
        riadky = ["<b>📅 Kalendár SPRÁVY z oficiálnych rozvrhov</b>"]
        for t, dni in sorted(po_typoch.items()):
            riadky.append(f"{t}: +{len(dni)} ({html.escape(min(dni).isoformat())} … {html.escape(max(dni).isoformat())})"
                          if len(dni) > 3 else f"{t}: +{html.escape(', '.join(d.isoformat() for d in sorted(dni)))}")
        if skips:
            riadky.append(f"vynechané (presunuté): {html.escape(cal.fmt_skip(skips))}")
        for t, e in sorted(chyby.items()):
            kon = f" (končí {kratke[t].isoformat()})" if t in kratke else ""
            riadky.append(f"⚠️ {t}{kon}: {html.escape(e)}")
        if zmenene:
            riadky.append(f"nasadenia: {html.escape(', '.join(zmenene))}")
        # zmena kalendára sa oznámi vždy; samotné chyby len keď sú iné než naposledy (denné čítanie by ich opakovalo)
        odtlacok = hashlib.sha1(json.dumps(chyby, sort_keys=True).encode()).hexdigest()[:16]
        if odtlacok == self.state["official_told"] and not (adds or skips):
            return
        self.ctx.event("calendar_official", added=cal.fmt_add(adds), skipped=cal.fmt_skip(skips), errors=chyby,
                       deployments=zmenene)
        if self.ctx.can_notify:
            try:
                self.ctx.notify("\n".join(riadky))
            except NotifyError as exc:
                self.ctx.log.warning("calendar official: telegram: %s", exc)
                return
        self.state["official_told"] = odtlacok

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

        # spravované záznamy: typy, ktoré feed tento týždeň má, nanovo z feedu (oprava vo feede sa prenesie); ostatné
        # týždne a typy, ktoré feed tento týždeň nemá (termín z oficiálneho rozvrhu), ostávajú
        videne = _feed_seen(cal, events, dni)
        add = [a for a in self.state["add"] if a[0] >= stare
               and (a[0] not in dni or a[2] not in videne or videne[a[2]].get(a[0]) == a[1])]
        skip = [s for s in self.state["skip"] if s[0] >= stare and (s[0] not in dni or s[1] not in videne)]
        add += [[d.isoformat(), hhmm, typ] for d, hhmm, typ in diff["add"]]
        skip += [[d.isoformat(), typ] for d, typ in diff["skip"]]
        self.state["add"] = sorted(list(x) for x in {tuple(a) for a in add})
        self.state["skip"] = sorted(list(x) for x in {tuple(s) for s in skip})

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

    def _push(self, cal, now: float, cfg: dict[str, Any] | None, force: bool, zdroj: str = "") -> str:
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
        if zdroj:
            sprava = (f"Doplň kalendár SPRÁVY z {zdroj} ({zmien} termínov: {popis or 'presuny'})\n\n"
                      "Termíny z oficiálnych rozvrhov (BLS, BEA, Fed, pravidlá ISM a CLAIMS), ktoré v calendar.json "
                      "chýbali alebo sa presunuli; zapísal plugin hubu ff_calendar.")
        else:
            sprava = (f"Doplň kalendár SPRÁVY z ForexFactory ({zmien} termínov: {popis or 'presuny'})\n\n"
                      "Termíny potvrdené týždenným exportom ForexFactory, ktoré v calendar.json chýbali alebo sa "
                      "presunuli; zapísal plugin hubu ff_calendar.")
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
