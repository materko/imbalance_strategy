"""Plugin `livedata` (docs/DATA.md §D): živé dáta stratégií drží hub a uzavreté mesiace raz za mesiac pushne do gitu.

Každý tick (`interval`) prepíše sklad telemetrie hubu (`live.sqlite`) do stromu `data/live/` vo svojom
adresári (`tester.livedata.export`: mesačné feather sviečok a obchodov, popis inštancií). Webapp si cez
`GET /api/plugins/livedata/files` stiahne to, čo **ešte nie je v gite** (súbor, ktorého obsah sa líši od
naposledy pushnutého) — bežiaci mesiac a mesiac, ktorý čaká na push.

Push: od `push_day`. dňa mesiaca (UTC) idú súbory **uzavretých** mesiacov (a popisy inštancií) z vlastného
klonu pluginu (`gitpush`) na `branch`. Neskoro doručené dáta za už pushnutý mesiac (agent bol offline) sa
pushnú pri ďalšom kole znova — commit vznikne len pri zmene obsahu.

`hub_data/plugins/livedata/config.json` (všetko voliteľné):

    {"remote": "git@github.com:materko/imbalance_strategy.git", "ssh_key": "deploy_key",
     "branch": "main", "push_day": 2, "author": "TradeBot hub <hub@tradebot.local>", "push": true}

`ssh_key` = deploy kľúč repozitára s právom zápisu (súbor v adresári pluginu, `known_hosts` vedľa neho); bez neho
`remote` ako HTTPS s tokenom (`https://x-access-token:<token>@github.com/…`). `remote` môže prísť aj z env
`TRADEBOT_LIVEDATA_REMOTE`; bez neho plugin dáta drží a ponúka, ale nepushuje.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.env import getenv
from tradebot.core.paths import HUB_LIVE_DB

from ..base import HubPlugin, read_json, write_json
from . import gitpush

#: Po zlyhanom pushe sa ďalší pokus robí najskôr o toľko sekúnd.
RETRY_SECONDS = 3600.0
#: Push zlyháva dlhšie ako toto = strážca to ohlási.
PROBLEM_AFTER = 86_400.0


def _month_now(now: float) -> tuple[str, str, int]:
    """(bežiaci mesiac, predošlý mesiac, deň v mesiaci) v UTC."""
    d = datetime.fromtimestamp(now, tz=timezone.utc)
    prev = f"{d.year - 1}-12" if d.month == 1 else f"{d.year}-{d.month - 1:02d}"
    return f"{d.year}-{d.month:02d}", prev, d.day


class LiveData(HubPlugin):
    title = "Živé dáta (data/live)"
    interval = 300.0
    max_tick = 1800.0   # prvý export veľkého skladu a push trvajú

    def setup(self, ctx) -> None:
        super().setup(ctx)
        self._state_mtime: float | None = -1.0   # ≠ None (súbor ešte nie je) — prvé načítanie prebehne vždy
        self.pushed: dict[str, str] = {}
        self._reload_state()
        self.push_tried = 0.0
        self.last_export: dict[str, Any] = {}
        self._sha: dict[str, tuple[int, int, str]] = {}   # cesta -> (veľkosť, mtime_ns, sha)
        self.index: list[dict[str, Any]] = []

    # -- cesty a config ------------------------------------------------------- #

    @property
    def root(self) -> Path:
        return self.ctx.path("data_live")

    def settings(self) -> dict[str, Any]:
        c = self.ctx.config()
        remote = str(c.get("remote") or getenv("LIVEDATA_REMOTE") or "")
        key = str(c.get("ssh_key") or "")
        return {"remote": remote, "push": bool(c.get("push", True)) and bool(remote),
                "ssh_key": (Path(key) if Path(key).is_absolute() else self.ctx.path(key)) if key else None,
                "branch": str(c.get("branch") or "main"), "push_day": max(1, min(28, int(c.get("push_day") or 2))),
                "author": str(c.get("author") or "TradeBot hub <hub@tradebot.local>"),
                "source": Path(str(c.get("source") or HUB_LIVE_DB))}

    def _reload_state(self) -> None:
        """Stav zo `state.json`, keď sa súbor zmenil (píše ho aj `plugin livedata --push` z príkazového riadka)."""
        path = self.ctx.path("state.json")
        try:
            mtime: float | None = path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime == self._state_mtime:
            return
        self._state_mtime = mtime
        st = read_json(path, {}) or {}
        self.pushed = dict(st.get("pushed") or {})
        self.last_push = float(st.get("last_push") or 0.0)
        self.last_commit = str(st.get("last_commit") or "")
        self.push_error = str(st.get("push_error") or "")
        self.push_error_since = float(st.get("push_error_since") or 0.0)

    def _save(self) -> None:
        path = self.ctx.path("state.json")
        write_json(path, {"pushed": self.pushed, "last_push": self.last_push, "last_commit": self.last_commit,
                          "push_error": self.push_error, "push_error_since": self.push_error_since})
        try:
            self._state_mtime = path.stat().st_mtime
        except OSError:
            pass

    # -- index ---------------------------------------------------------------- #

    def refresh_index(self) -> list[dict[str, Any]]:
        """Súbory stromu so sha; sha sa prepočíta len pri zmene veľkosti či času súboru."""
        from tester import livedata

        out = []
        for top in ("candles", "trades", "instances"):
            for p in sorted((self.root / top).rglob("*")):
                if not p.is_file() or p.name.endswith(".tmp"):
                    continue
                rel = p.relative_to(self.root).as_posix()
                st = p.stat()
                cached = self._sha.get(rel)
                if cached is None or cached[:2] != (st.st_size, st.st_mtime_ns):
                    cached = (st.st_size, st.st_mtime_ns, livedata.file_sha(p))
                    self._sha[rel] = cached
                out.append({"path": rel, "size": st.st_size, "sha": cached[2], "month": livedata.file_month(rel)})
        self.index = out
        return out

    def due(self, now: float, *, force: bool = False) -> list[dict[str, Any]]:
        """Súbory na push: uzavreté mesiace (predošlý až od `push_day`, `force` hneď) s obsahom iným než v gite,
        a k nim zmenené popisy inštancií."""
        cur, prev, day = _month_now(now)
        push_day = self.settings()["push_day"]
        months = [f for f in self.index if f["month"] and f["month"] < cur
                  and (f["month"] < prev or force or day >= push_day) and self.pushed.get(f["path"]) != f["sha"]]
        if not months:
            return []
        insts = [f for f in self.index if f["month"] is None and self.pushed.get(f["path"]) != f["sha"]]
        return months + insts

    # -- práca ---------------------------------------------------------------- #

    def export(self) -> dict[str, Any]:
        from tester import livedata

        self.last_export = livedata.export(self.settings()["source"], self.root, self.ctx.path("cursor.json"))
        self.last_export["at"] = self.ctx.clock()
        return self.last_export

    def push(self, now: float, *, force: bool = False) -> str:
        """Push uzavretých mesiacov; vráti commit (`""` = nebolo čo). Chyba = `gitpush.PushError`."""
        cfg = self.settings()
        files = self.due(now, force=force)
        if not files:
            self._clear_error()   # nič nečaká (napr. pushol to ručný push) — stará chyba už neplatí
            return ""
        if not cfg["remote"]:
            raise gitpush.PushError("push nie je nastavený (config remote / TRADEBOT_LIVEDATA_REMOTE)")
        months = sorted({f["month"] for f in files if f["month"]})
        kinds = sorted({"sviečky" if f["path"].startswith("candles/") else "obchody" for f in files if f["month"]})
        n = len(files)
        word = "súbor" if n == 1 else "súbory" if n < 5 else "súborov"
        msg = (f"Pridaj živé dáta za {', '.join(months)} z hubu ({n} {word}: {', '.join(kinds)}), "
               f"aby boli uzavreté mesiace stratégií naživo v gite oddelene od stiahnutých dát")
        commit = gitpush.push_files(self.ctx.path("repo"), cfg["remote"], cfg["branch"], self.root,
                                    [f["path"] for f in files], msg, cfg["author"], log=self.ctx.log.info,
                                    ssh_key=cfg["ssh_key"])
        for f in files:
            self.pushed[f["path"]] = f["sha"]
        self.last_push = now
        if commit:
            self.last_commit = commit
            self.ctx.event("livedata_push", commit=commit[:10], months=months, files=len(files))
        self.push_error, self.push_error_since = "", 0.0
        self._save()
        return commit

    def _clear_error(self) -> None:
        if self.push_error:
            self.push_error, self.push_error_since = "", 0.0
            self._save()

    def tick(self) -> None:
        self._reload_state()   # `plugin livedata --push` z príkazového riadka mohol pushnúť medzitým
        self.export()
        self.refresh_index()
        now = self.ctx.clock()
        cfg = self.settings()
        if not self.due(now):
            self._clear_error()
            return
        if not cfg["push"] or now - self.push_tried < RETRY_SECONDS:
            return
        self.push_tried = now
        try:
            self.push(now)
            self.push_error, self.push_error_since = "", 0.0
        except gitpush.PushError as exc:
            if not self.push_error:
                self.push_error_since = now
            self.push_error = str(exc)
        self._save()

    # -- čo vidí svet ---------------------------------------------------------- #

    def files(self) -> list[dict[str, Any]]:
        """Pre webapp: súbory, ktorých obsah v gite ešte nie je."""
        if not self.index and self.root.exists():
            self.refresh_index()
        return [f for f in self.index if self.pushed.get(f["path"]) != f["sha"]]

    def files_root(self) -> Path:
        return self.root

    def status(self) -> dict[str, Any]:
        now = self.ctx.clock()
        cfg = self.settings()
        pending = sorted({f["month"] for f in self.files() if f["month"]})
        out = {"push": cfg["push"], "branch": cfg["branch"], "push_day": cfg["push_day"],
               "pending_months": pending, "offered": len(self.files()),
               "last_push": self.last_push or None, "last_commit": self.last_commit[:10] or None,
               "last_export": self.last_export or None, "push_error": self.push_error or None,
               "problem": None}
        if self.push_error and now - self.push_error_since > PROBLEM_AFTER:
            out["problem"] = f"živé dáta sa nedajú pushnúť do gitu: {self.push_error}"
        return out

    def cli(self, argv: list[str]) -> int:
        ap = argparse.ArgumentParser(prog="python -m tester.hub plugin livedata",
                                     description="živé dáta hubu: export, čo čaká na push, push uzavretých mesiacov")
        ap.add_argument("--export", action="store_true", help="exportovať live.sqlite hneď")
        ap.add_argument("--push", action="store_true", help="pushnúť uzavreté mesiace hneď (aj pred push_day)")
        args = ap.parse_args(argv)
        if args.export or not self.root.exists():
            r = self.export()
            print(f"export: sviečok +{r.get('candles', 0)}, obchodov {r.get('trades', 0)}, inštancií {r.get('instances', 0)}"
                  + (f" — {r['error']}" if r.get("error") else ""))
        self.refresh_index()
        now = time.time()
        if args.push:
            try:
                c = self.push(now, force=True)
                print(f"push: {c[:10] if c else 'nič nové'}")
            except gitpush.PushError as exc:
                print(f"push zlyhal: {exc}")
                return 1
        s = self.status()
        print(f"push {'zapnutý' if s['push'] else 'VYPNUTÝ (bez remote)'} na {s['branch']} od {s['push_day']}. dňa; "
              f"mimo gitu {s['offered']} súborov, mesiace {', '.join(s['pending_months']) or '—'}; "
              f"posledný commit {s['last_commit'] or '—'}" + (f"; CHYBA {s['push_error']}" if s["push_error"] else ""))
        due = self.due(now)
        if due:
            print(f"na push čaká {len(due)} súborov: {', '.join(sorted({f['month'] for f in due if f['month']}))}")
        return 0
