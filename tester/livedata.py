"""Živé dáta: sviečky a skutočné obchody zo stratégií, ktoré bežali naživo (NinjaTrader, MT5).

Zdroj je sklad live telemetrie (`LiveStore`, docs/LIVE.md) — na hube `live.sqlite`, vo webapp jej zrkadlo.
Export ho prepisuje do stromu v tvare `data_live/` — **oddelene** od stiahnutých dát (`data/`, `data_archive/`),
ktoré sa tým nikdy nezmenia:

* ``candles/<platforma>/<symbol>/<tf>-<YYYY-MM>.feather`` — 1m z udalostí ``m1`` (adaptér ich posiela
  nezávisle od TF grafu) a TF grafu z ``bar``. Stĺpce ako vo Freqtrade (`date` UTC, OHLCV). Viac inštancií
  na tom istom symbole sa zlúči podľa času; čo už v súbore je, vyhráva (bar po reštarte sa zopakuje),
* ``trades/<inštancia>/<YYYY-MM>.feather`` — obchody u brokera z ``fill`` spárované podľa id orderu (to isté,
  čo karta Live diverzifikácia, `tester.dashboard.live`) s profilom behu; mesiac podľa zatvorenia,
* ``instances/<inštancia>.json`` — platforma, účet, symbol, TF, stratégia, behy (od–do, profil) a config
  každého profilu (z ``hello``), aby sa živé obdobie dalo neskôr prepočítať simuláciou (`tester.livesim`).

Kto čo drží:

* **hub** (plugin `livedata`, `tester/hub/plugins/livedata`) exportuje `live.sqlite` do svojho adresára
  a **uzavreté mesiace raz za mesiac pushne do gitu** (`LIVE_DATA` = `data_live/` v repozitári),
* **webapp** číta `data_live/` z gitu a to, čo hub ešte nepushol, si od neho stiahne (`sync_hub`) do
  `LIVE_DATA_HUB` (gitignored). Čítanie (`instances`, `trades`, `load_candles`) dá oba korene dokopy;
  súbor z hubu má prednosť. Bez hubu webapp do `LIVE_DATA_HUB` exportuje vlastné zrkadlo.

Behy zo Strategy Testera / Analyzera (``hello.tester``) sa vynechajú — nie sú to živé dáta. Súbor sa zapíše,
len keď sa jeho obsah zmenil.

    python -m tester.livedata export --root <adresár>   # sklad / zrkadlo -> strom data_live
    python -m tester.livedata sync                      # z hubu, čo ešte nie je v gite
    python -m tester.livedata status                    # čo je k dispozícii (git + hub)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tradebot.core.env import getenv
from tradebot.core.paths import LIVE_DATA, LIVE_DATA_CURSOR, LIVE_DATA_HUB, LIVE_MIRROR

__all__ = ["export", "enabled", "load_candles", "candle_range", "instances", "instance", "trades",
           "file_index", "file_month", "sync_hub", "EXPORT_SECONDS", "OHLCV", "HUB_FILES"]

#: Hub exportuje a webapp sa s hubom zosúlaďuje najviac raz za toľko sekúnd.
EXPORT_SECONDS = 300
#: Súbory pluginu `livedata` na hube, ktoré ešte nie sú v gite (`GET` = zoznam, `/<cesta>` = súbor).
HUB_FILES = "/api/plugins/livedata/files"
OHLCV = ("open", "high", "low", "close", "volume")
#: Koľko udalostí sviečok sa zo skladu číta naraz.
_BATCH = 200_000
_BAD = re.compile(r"[^A-Za-z0-9._-]")
_MONTH = re.compile(r"(\d{4}-\d{2})\.feather$")
_TOPS = ("candles", "trades", "instances")


def enabled() -> bool:
    """Webapp bez hubu exportuje vlastné zrkadlo do `LIVE_DATA_HUB`; `TRADEBOT_LIVE_EXPORT=0` to vypne."""
    return str(getenv("LIVE_EXPORT") or "1").strip().lower() not in ("0", "false", "no", "off")


def _safe(text: Any) -> str:
    return _BAD.sub("-", str(text or "")) or "-"


def _iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ms(iso: str) -> float:
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000


def _month(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m")


def _tf_name(minutes: int) -> str:
    return f"{int(minutes)}m"


def _root(root: Path | str | None) -> Path:
    """Koreň na zápis — predvolene `LIVE_DATA_HUB` (čítaný pri volaní, testy ho presmerujú)."""
    return Path(root) if root is not None else Path(LIVE_DATA_HUB)


def _roots(root: Path | str | None) -> list[Path]:
    """Korene na čítanie: zadaný, inak git (`LIVE_DATA`) a za ním to, čo je len na hube (`LIVE_DATA_HUB`)."""
    return [Path(root)] if root is not None else [Path(LIVE_DATA), Path(LIVE_DATA_HUB)]


def symbol_dir(platform: str, symbol: str, root: Path | str) -> Path:
    return Path(root) / "candles" / _safe(platform) / _safe(symbol)


# --------------------------------------------------------------------------- #
# zápis
# --------------------------------------------------------------------------- #


def _write_json(path: Path, data: Any) -> bool:
    text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)
    return True


def _write_frame(path: Path, df) -> bool:
    """Feather len pri zmene obsahu (porovnanie rámcov, nie bajtov — tie isté dáta = ten istý súbor)."""
    import pandas as pd

    df = df.reset_index(drop=True)
    if path.exists():
        try:
            old = pd.read_feather(path)
            if old.shape == df.shape and list(old.columns) == list(df.columns) and old.equals(df):
                return False
        except Exception:  # noqa: BLE001 - rozbitý súbor sa prepíše
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_feather(tmp, compression="lz4")
    tmp.replace(path)
    return True


def _merge_candles(path: Path, rows: list[tuple[int, float, float, float, float, float]]) -> int:
    """Pridá bary do mesačného súboru; čo už v ňom je, ostáva. Vráti počet nových barov."""
    import pandas as pd

    new = pd.DataFrame(rows, columns=["ms", *OHLCV])
    new = new.drop_duplicates("ms", keep="first")
    new["date"] = pd.to_datetime(new.pop("ms"), unit="ms", utc=True)
    new = new[["date", *OHLCV]]
    if path.exists():
        old = pd.read_feather(path)
        fresh = new[~new["date"].isin(old["date"])]
        if fresh.empty:
            return 0
        df = pd.concat([old, fresh], ignore_index=True)
    else:
        fresh, df = new, new
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    for col in OHLCV:
        df[col] = df[col].astype("float64")
    _write_frame(path, df)
    return len(fresh)


def _load_cursor(path: Path, mirror: Path) -> int:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict) or data.get("mirror") != str(Path(mirror).resolve()):
        return 0
    return max(0, int(data.get("cursor") or 0))


def _save_cursor(path: Path, mirror: Path, cursor: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"mirror": str(Path(mirror).resolve()), "cursor": int(cursor)}), encoding="utf-8")
    tmp.replace(path)


def _sessions(db: sqlite3.Connection) -> dict[str, dict[str, dict[str, Any]]]:
    """inštancia → session → {start, end, first_bar, last_bar, profile, tester, config}."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for inst, ses, body in db.execute("SELECT instance, session, body FROM events WHERE kind = 'hello' ORDER BY id"):
        h = json.loads(body)
        s = out.setdefault(inst, {}).setdefault(ses, {"session": ses, "start": int(h["t"]), "profile": "",
                                                       "tester": False, "config": {}})
        s["start"] = min(s["start"], int(h["t"]))
        s["profile"] = str(h.get("profile") or s["profile"])
        s["tester"] = bool(h.get("tester")) or s["tester"]
        s["config"] = h.get("config") or s["config"]
        s["instrument"] = h.get("instrument") or s.get("instrument")
    for inst, ses, t_max, b_min, b_max in db.execute(
            "SELECT instance, session, MAX(t), MIN(CASE WHEN kind = 'bar' THEN bt END), "
            "MAX(CASE WHEN kind = 'bar' THEN bt END) FROM events GROUP BY instance, session"):
        s = out.setdefault(inst, {}).setdefault(ses, {"session": ses, "start": int(t_max or 0), "profile": "",
                                                       "tester": False, "config": {}})
        s.update(end=int(t_max or 0), first_bar=b_min, last_bar=b_max)
    for inst, ses, body in db.execute("SELECT instance, session, body FROM events WHERE kind = 'control' ORDER BY id"):
        c = json.loads(body)
        s = out.get(inst, {}).get(ses)
        if s is not None and c.get("profile"):
            s["profile"] = str(c["profile"])
    return out


def _export_candles(db: sqlite3.Connection, root: Path, cursor: int,
                    insts: dict[str, dict[str, Any]], tester_sessions: set[tuple[str, str]]) -> tuple[int, int, set[str]]:
    """Sviečky za kurzorom → mesačné súbory. Vráti (nový kurzor, nových barov, zmenené súbory)."""
    added, files = 0, set()
    while True:
        rows = db.execute(
            "SELECT id, instance, session, kind, body FROM events WHERE id > ? AND kind IN ('m1', 'bar') "
            "ORDER BY id LIMIT ?", (cursor, _BATCH)).fetchall()
        if not rows:
            break
        groups: dict[Path, list[tuple[int, float, float, float, float, float]]] = {}
        for rid, inst, ses, kind, body in rows:
            cursor = max(cursor, int(rid))
            meta = insts.get(inst)
            if meta is None or (inst, ses) in tester_sessions:
                continue
            ev = json.loads(body)
            bt = int(ev["bt"])
            tf = 1 if kind == "m1" else int(meta["tf"] or 0)
            if tf <= 0:
                continue
            path = symbol_dir(meta["platform"], meta["symbol"], root) / f"{_tf_name(tf)}-{_month(bt)}.feather"
            groups.setdefault(path, []).append((bt, float(ev["o"]), float(ev["h"]), float(ev["l"]), float(ev["c"]),
                                                float(ev.get("v") or 0.0)))
        for path, bars in groups.items():
            n = _merge_candles(path, bars)
            if n:
                added += n
                files.add(str(path))
        if len(rows) < _BATCH:
            break
    return cursor, added, files


def _trade_frame(trades: list[dict[str, Any]], sessions: list[dict[str, Any]]):
    import pandas as pd

    def profile_at(iso: str) -> str:
        ms = _ms(iso)
        best = ""
        for s in sessions:
            if s["start"] <= ms + 60_000:
                best = s["profile"]
        return best

    cols = ["id", "open", "close", "dir", "qty", "entry", "exit", "sl", "tp", "sd", "pts", "pnl", "r", "reason",
            "signal", "sent", "plan", "order_type", "profile"]
    rows = [{**{c: t.get(c) for c in cols}, "profile": profile_at(t["open"])} for t in trades]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("open", "close", "signal", "sent"):
        df[c] = pd.to_datetime(df[c], utc=True)
    for c in ("qty", "entry", "exit", "sl", "tp", "sd", "pts", "pnl", "r", "plan"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    for c in ("id", "dir", "reason", "order_type", "profile"):
        df[c] = df[c].fillna("").astype(str)
    return df


def _export_trades(root: Path, inst_id: str, live_trades: list[dict[str, Any]], sessions: list[dict[str, Any]]) -> int:
    """Obchody inštancie po mesiacoch zatvorenia: to, čo už v súbore je, + nové zo skladu (kľúč id + otvorenie;
    novší výpočet vyhrá). Sklad sa môže vymeniť alebo prečistiť — staré obchody ostanú. Vráti počet obchodov
    v zmenených súboroch."""
    import pandas as pd

    tester = [(s["start"], s.get("end") or s["start"]) for s in sessions if s.get("tester")]
    keep = [t for t in live_trades if t.get("close") and not any(a <= _ms(t["open"]) <= b for a, b in tester)]
    if not keep:
        return 0
    new = _trade_frame(keep, [s for s in sessions if not s.get("tester")])
    written = 0
    for month, part in new.groupby(new["close"].dt.strftime("%Y-%m")):
        path = Path(root) / "trades" / _safe(inst_id) / f"{month}.feather"
        if path.exists():
            old = pd.read_feather(path)
            key_new = set(zip(part["id"], part["open"]))
            old = old[[k not in key_new for k in zip(old["id"], old["open"])]]
            part = pd.concat([old, part], ignore_index=True) if len(old) else part
        part = part.sort_values(["open", "id"], kind="stable").reset_index(drop=True)
        if _write_frame(path, part):
            written += len(part)
    return written


def export(mirror: Path | str = LIVE_MIRROR, root: Path | str | None = None, cursor_path: Path | str = LIVE_DATA_CURSOR,
           *, now_ms: int | None = None) -> dict[str, Any]:
    """Sklad telemetrie (`mirror` — zrkadlo webapp alebo `live.sqlite` hubu) → strom `root` (predvolene
    `LIVE_DATA_HUB`). Sviečky prírastkovo za kurzorom, obchody a inštancie celé (sú malé)."""
    import time

    from tester.dashboard.live import _instance, base_strategy, setting_id

    mirror, root = Path(mirror), _root(root)
    out: dict[str, Any] = {"candles": 0, "files": [], "trades": 0, "instances": 0}
    if not mirror.exists():
        out["error"] = f"sklad telemetrie {mirror} nie je"
        return out
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    db = sqlite3.connect(f"file:{mirror}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        insts = {r["id"]: dict(r) for r in db.execute("SELECT * FROM instances")}
        sessions = _sessions(db)
        tester_sessions = {(i, s) for i, ss in sessions.items() for s, v in ss.items() if v.get("tester")}
        cursor = _load_cursor(Path(cursor_path), mirror)
        top = db.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]
        if cursor > top:      # sklad je nový (menší) — od začiatku, duplicity sa zahodia
            cursor = 0
        cursor, added, files = _export_candles(db, root, cursor, insts, tester_sessions)
        out["candles"], out["files"] = added, sorted(files)
        for iid, inst in sorted(insts.items()):
            if not inst.get("strategy"):
                continue
            ses = sorted(sessions.get(iid, {}).values(), key=lambda s: s["start"])
            if ses and all(s.get("tester") for s in ses):
                continue
            live = _instance(db, inst, now_ms)
            out["trades"] += _export_trades(root, iid, live["trades"], ses)
            configs: dict[str, Any] = {}
            for s in ses:
                if not s.get("tester"):
                    configs[Path(str(s["profile"]).replace("\\", "/")).stem or "-"] = s["config"]
            hello = json.loads(inst["hello"] or "{}")
            data = {
                "id": iid, "platform": inst["platform"], "account": inst["account"], "symbol": inst["symbol"],
                "tf": int(inst["tf"] or 0), "engine": inst["strategy"], "strategy": base_strategy(inst["strategy"]),
                "profile": Path(str(inst["profile"] or "").replace("\\", "/")).stem,
                "setting": setting_id(inst["strategy"], inst["profile"]),
                "instrument": hello.get("instrument") or {}, "point_value": live.get("point_value"),
                "sessions": [{"session": s["session"], "start": _iso(s["start"]), "end": _iso(s.get("end")),
                              "first_bar": _iso(s.get("first_bar")), "last_bar": _iso(s.get("last_bar")),
                              "profile": Path(str(s["profile"]).replace("\\", "/")).stem}
                             for s in ses if not s.get("tester")],
                "configs": configs,
            }
            # behy, ktoré zo skladu vypadli, ostanú
            data = _merge_instance(_read_instance(root, iid), data)
            if _write_json(root / "instances" / f"{_safe(iid)}.json", data):
                out["instances"] += 1
        _save_cursor(Path(cursor_path), mirror, cursor)
    finally:
        db.close()
    return out


# --------------------------------------------------------------------------- #
# čítanie (git + hub)
# --------------------------------------------------------------------------- #


def _read_instance(root: Path, inst_id: str) -> dict[str, Any] | None:
    try:
        return json.loads((Path(root) / "instances" / f"{_safe(inst_id)}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _merge_instance(a: dict[str, Any] | None, b: dict[str, Any]) -> dict[str, Any]:
    """Tá istá inštancia staršia (`a`, git) a novšia (`b`, hub): novší popis, behy a configy zjednotené."""
    if not a:
        return b
    known = {s["session"] for s in b.get("sessions") or []}
    sessions = [s for s in a.get("sessions") or [] if s["session"] not in known] + list(b.get("sessions") or [])
    return {**a, **b, "sessions": sorted(sessions, key=lambda s: s.get("start") or ""),
            "configs": {**(a.get("configs") or {}), **(b.get("configs") or {})}}


def instances(root: Path | str | None = None) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for r in _roots(root):
        for p in sorted((r / "instances").glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            by_id[d["id"]] = _merge_instance(by_id.get(d["id"]), d)
    return [by_id[k] for k in sorted(by_id)]


def instance(inst_id: str, root: Path | str | None = None) -> dict[str, Any] | None:
    out = None
    for r in _roots(root):
        d = _read_instance(r, inst_id)
        if d is not None:
            out = _merge_instance(out, d)
    return out


def trades(inst_id: str, root: Path | str | None = None) -> list[dict[str, Any]]:
    """Obchody inštancie zo všetkých mesiacov a koreňov (časy ISO UTC, chýbajúce čísla `None`); ten istý
    obchod (id + otvorenie) z hubu prebije git."""
    import pandas as pd

    frames = [pd.read_feather(p) for r in _roots(root) for p in sorted((r / "trades" / _safe(inst_id)).glob("*.feather"))]
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True).drop_duplicates(["id", "open"], keep="last")
    df = df.sort_values(["open", "id"], kind="stable")
    out = []
    for rec in df.to_dict("records"):
        row = {}
        for k, v in rec.items():
            if isinstance(v, pd.Timestamp):
                row[k] = None if pd.isna(v) else v.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif isinstance(v, float) and v != v:
                row[k] = None
            else:
                row[k] = v
        out.append(row)
    return out


def load_candles(platform: str, symbol: str, tf: str = "1m", root: Path | str | None = None, *,
                 start_ms: int | None = None, end_ms: int | None = None):
    """Živé sviečky symbolu (`date` UTC, OHLCV) v rozsahu [start, end) z gitu aj z hubu (ten istý bar z hubu
    vyhrá); prázdny rámec, keď nie sú."""
    import pandas as pd

    frames = []
    for r in _roots(root):
        for p in sorted(symbol_dir(platform, symbol, r).glob(f"{tf}-*.feather")):
            month = p.stem.rsplit("-", 2)
            if start_ms is not None or end_ms is not None:
                first = datetime.strptime(f"{month[-2]}-{month[-1]}", "%Y-%m").replace(tzinfo=timezone.utc)
                nxt = datetime(first.year + first.month // 12, first.month % 12 + 1, 1, tzinfo=timezone.utc)
                if end_ms is not None and first.timestamp() * 1000 >= end_ms:
                    continue
                if start_ms is not None and nxt.timestamp() * 1000 <= start_ms:
                    continue
            frames.append(pd.read_feather(p))
    if not frames:
        return pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns, UTC]"),
                             **{c: pd.Series([], dtype="float64") for c in OHLCV}})
    df = pd.concat(frames, ignore_index=True).drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    if start_ms is not None:
        df = df[df["date"] >= pd.Timestamp(start_ms, unit="ms", tz="UTC")]
    if end_ms is not None:
        df = df[df["date"] < pd.Timestamp(end_ms, unit="ms", tz="UTC")]
    return df.reset_index(drop=True)


def candle_range(platform: str, symbol: str, tf: str = "1m", root: Path | str | None = None) -> tuple[str, str, int] | None:
    """(prvý, posledný, počet) živých sviečok TF symbolu, alebo `None`."""
    df = load_candles(platform, symbol, tf, root)
    if df.empty:
        return None
    return (df["date"].iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"), df["date"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ"), len(df))


# --------------------------------------------------------------------------- #
# súbory: index (hub, git) a zosúladenie webapp s hubom
# --------------------------------------------------------------------------- #


def file_month(rel: str) -> str | None:
    """Mesiac súboru stromu (`candles/…/1m-2026-10.feather`, `trades/…/2026-10.feather`); `instances/*.json` = None."""
    m = _MONTH.search(str(rel))
    return m.group(1) if m else None


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(rel: str) -> bool:
    """Relatívna cesta vnútri stromu (`candles/…`, `trades/…`, `instances/…`), bez `..` a koreňov."""
    rel = str(rel)
    parts = rel.split("/")
    return parts[0] in _TOPS and len(parts) > 1 and all(x not in ("", ".", "..") for x in parts) \
        and "\\" not in rel and ":" not in rel


def file_index(root: Path | str) -> list[dict[str, Any]]:
    """Všetky súbory stromu: `{"path" (relatívna, /), "size", "sha", "month"}`."""
    root = Path(root)
    out = []
    for top in _TOPS:
        for p in sorted((root / top).rglob("*")):
            if not p.is_file() or p.name.endswith(".tmp"):
                continue
            rel = p.relative_to(root).as_posix()
            out.append({"path": rel, "size": p.stat().st_size, "sha": file_sha(p), "month": file_month(rel)})
    return out


def sync_hub(http: Any, cache: Path | str | None = None, repo: Path | str | None = None) -> dict[str, Any]:
    """Stiahne z hubu súbory, ktoré ešte nie sú v gite (`HUB_FILES`), do `cache` (`LIVE_DATA_HUB`).

    Súbor sa stiahne, keď v cache nie je alebo má iný obsah (sha). Súbor, ktorý hub už neponúka (pushol ho),
    sa z cache zmaže až vtedy, keď ho má git (`repo`, `LIVE_DATA`) s rovnakým obsahom — inak by medzi pushom
    hubu a Pull vo webapp chýbal."""
    from urllib.parse import quote

    cache = Path(cache) if cache is not None else Path(LIVE_DATA_HUB)
    repo = Path(repo) if repo is not None else Path(LIVE_DATA)
    listing = http.get(HUB_FILES)
    files = listing.get("files") if isinstance(listing, dict) else None
    if not isinstance(files, list):
        raise ValueError("hub neposlal zoznam živých dát (beží na ňom plugin livedata?)")
    offered = {str(f.get("path") or ""): str(f.get("sha") or "") for f in files if safe_rel(str(f.get("path") or ""))}
    downloaded = removed = 0
    for rel, sha in offered.items():
        dst = cache / rel
        if dst.exists() and file_sha(dst) == sha:
            continue
        data = http.get_bytes(f"{HUB_FILES}/{quote(rel)}")
        if sha and hashlib.sha256(data).hexdigest() != sha:
            continue   # súbor sa medzitým na hube zmenil — ďalšie kolo
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dst)
        downloaded += 1
    for f in file_index(cache):
        if f["path"] in offered:
            continue
        in_git = repo / f["path"]
        if in_git.exists() and file_sha(in_git) == f["sha"]:
            (cache / f["path"]).unlink()
            removed += 1
    return {"files": len(offered), "downloaded": downloaded, "removed": removed}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _status(root: Path | None) -> None:
    for inst in instances(root):
        n = len(trades(inst["id"], root))
        tfs = []
        for tf in ("1m", _tf_name(inst["tf"])):
            r = candle_range(inst["platform"], inst["symbol"], tf, root)
            if r:
                tfs.append(f"{tf} {r[0][:16]}–{r[1][:16]} ({r[2]})")
        print(f"{inst['id']}: {n} obch., profil {inst['profile']}; " + ("; ".join(dict.fromkeys(tfs)) or "bez sviečok"))


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.livedata", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="sklad live telemetrie -> strom data_live")
    e.add_argument("--mirror", default=str(LIVE_MIRROR), help="zrkadlo webapp alebo live.sqlite hubu")
    e.add_argument("--root", default=str(LIVE_DATA_HUB), help="kam (predvolene tester/live/data_live_hub)")
    sub.add_parser("sync", help="z hubu (tester/agent.json), čo ešte nie je v gite")
    s = sub.add_parser("status", help="čo je k dispozícii (git + hub, alebo len --root)")
    s.add_argument("--root", default=None)
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "export":
        res = export(args.mirror, args.root)
        print(f"sviečok +{res['candles']} ({len(res['files'])} súborov), obchodov {res['trades']}, "
              f"inštancií {res['instances']}" + (f" — {res['error']}" if res.get("error") else ""))
        return 1 if res.get("error") else 0
    if args.cmd == "sync":
        from tester.hub import config as hub_config
        from tester.hub.client import HubHttp

        cfg = hub_config.load()
        if cfg is None:
            print("hub nie je nastavený (tester/agent.json)")
            return 1
        res = sync_hub(HubHttp(cfg.hub_url, cfg.token, timeout=60.0))
        print(f"hub ponúka {res['files']} súborov mimo gitu, stiahnutých {res['downloaded']}, zmazaných {res['removed']}")
        return 0
    _status(Path(args.root) if args.root else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
