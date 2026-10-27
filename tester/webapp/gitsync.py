"""Git synchronizácia dát testera — `runs/`, `sweeps/`, `profiles/`, `analytics/`
a `archive/`, nič iné.

Tester klikne „Push": zmeny v histórii behov, vo výsledkoch mriežok a matíc, vo vlastných
profiloch, v uložených analytikách a v archíve behov (`cli archive`) sa commitnú, spraví sa `fetch` + `rebase` na `origin/<vetva>` a `push`. Kód ani
iné súbory sa nedotýkajú, takže si tester nemôže omylom commitnúť rozpracovanú zmenu
stratégie. Konflikt prakticky nevzniká (každý beh aj každá mriežka je nový súbor), ale keby
predsa, výstup gitu sa zobrazí celý.

Do gitu z histórie nejdú len kresby grafu (`chart.json.gz`, cache `runs/.charts/`) a dočasné
súbory rozbehnutých behov — to určuje `.gitignore` a nič iné. Keď git ignoruje v týchto
adresároch ešte niečo ďalšie (pravidlo v `.gitignore` je prísnejšie, než má byť), Push sa
**zastaví a povie to**: kedysi `tester/runs/` v `.gitignore` spôsobil, že Push behy ticho
vynechal a tester si myslel, že ich zdieľa.

Cieľom je vždy **`main`** (alebo to, čo je v `TRADEBOT_GIT_BRANCH`), nie vetva, na ktorej
klon práve stojí: keď webapp bežala z vývojárskeho worktree, história skončila na
vetve `claude/...` a v `main` po nej nebolo ani stopy. Ak by pritom mala vetva
commity mimo `runs/` a `profiles/`, Push to odmietne — kód testera do `main`
nepatrí, ten ide cez pull request.

Upravený profil Push pred commitom porovná s HEAD (`_restore_profiles`): hodnotu configu, ktorú
súbor stratil alebo vrátil na stav spred cudzieho commitu, doplní z HEAD a povie to. Profil
sa upravuje na mieste — keď ho niečo načíta, klon sa medzitým aktualizuje (Pull, agent hubu)
a potom ho to zapíše späť, nesie starý obsah; Push by ho inak ticho commitol a vrátil tak
novší commit (da77cb74c vyhodil `legacyPineSizing` z 11 profilov smernice).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tester.atomic import write_json_atomic
from tradebot.core.env import getenv
from tradebot.core.paths import ANALYTICS_DIR, ARCHIVE_DIR, REPO, SWEEPS_DIR
from .profiles import LEGACY_STRATEGY, PROFILES_DIR
from .store import RUNS_DIR


#: Git sa nesmie nikoho pýtať na heslo — webapp beží bez terminálu, takže by request
#: buď zamrzol, alebo (na macOS) spadol na „could not read Username: Device not
#: configured". Nech radšej hneď zlyhá a my povieme, čo s tým.
_NO_PROMPT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

#: Podľa čoho poznáme, že to nebola chyba gitu, ale chýbajúce prihlásenie.
_AUTH_MARKERS = (
    "could not read Username", "could not read Password", "Authentication failed",
    "Permission denied (publickey)", "Invalid username or token", "terminal prompts disabled",
)

AUTH_HELP = """
GitHub nepustil push: webapp beží bez terminálu, takže sa nemá koho spýtať na heslo.
Prihlásenie stačí uložiť raz, potom už Push funguje sám:

  macOS/Linux, cez GitHub CLI:   gh auth login   (a potom: gh auth setup-git)
  macOS, cez token:              git config --global credential.helper osxkeychain
                                 a raz spraviť `git push` v termináli — meno a Personal
                                 Access Token (Settings → Developer settings) sa uložia
  Windows:                       git config --global credential.helper manager

Overenie: v termináli v adresári repozitára `git push` musí prejsť bez pýtania sa.
""".strip()


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=check, env={**os.environ, **_NO_PROMPT_ENV},
    )


def _auth_failed(output: str) -> bool:
    return any(marker in output for marker in _AUTH_MARKERS)


def _paths() -> list[str]:
    """Adresáre, ktoré Push commituje — prázdny (neexistujúci) sa vynechá, git by naň nadával."""
    dirs = [Path(RUNS_DIR), Path(SWEEPS_DIR), Path(PROFILES_DIR), Path(ANALYTICS_DIR),
            Path(ARCHIVE_DIR)]
    return [d.relative_to(REPO).as_posix() for d in dirs if d.exists()]


#: Čo smie git v adresároch histórie ignorovať: kresby grafu (lokálna cache, prepočítajú sa)
#: a dočasné súbory rozbehnutých behov. Všetko ostatné ignorované je chyba `.gitignore`.
ALLOWED_IGNORED = ("/chart.json.gz", "/.charts/", "/.profiles/", "/.plans/", "/.sweeps/",
                   "/.index/", "/__pycache__/", ".tmp")


def ignored_history(paths: list[str] | None = None) -> list[str]:
    """Súbory histórie, ktoré git ignoruje, hoci by mali ísť do gitu."""
    paths = _paths() if paths is None else paths
    if not paths:
        return []
    r = _git("ls-files", "--others", "--ignored", "--exclude-standard", "--", *paths)
    if r.returncode != 0:
        return []
    return [f for f in r.stdout.splitlines()
            if f.strip() and not any(a in "/" + f.replace("\\", "/") for a in ALLOWED_IGNORED)]


def _ignored_note(files: list[str]) -> str:
    ukazka = "\n  ".join(files[:10]) + ("\n  …" if len(files) > 10 else "")
    return (f"Push zrušený: git ignoruje {len(files)} súborov histórie, ktoré majú ísť na GitHub "
            f"(behy, mriežky, profily alebo analytiky). Bez opravy by ich Push ticho vynechal:\n  "
            f"{ukazka}\nNájdi pravidlo príkazom `git check-ignore -v <súbor>` a oprav `.gitignore` "
            "(ignorovať sa smú len kresby grafu `chart.json.gz` a cache `tester/runs/.charts/`).")


def branch() -> str:
    """Vetva, na ktorej stojí klon (len informácia do hlavičky stránky)."""
    r = _git("branch", "--show-current")
    return r.stdout.strip() or "HEAD"


def target() -> str:
    """Vetva, do ktorej história behov patrí — `main`, ak sa nepovie inak."""
    return getenv("GIT_BRANCH", "").strip() or "main"


def _foreign_commits(br: str) -> list[str]:
    """Commity, ktoré sú na HEAD navyše oproti `origin/<br>` a siahajú mimo dát testera."""
    paths = tuple(_paths())
    if not paths:
        return []
    rev = _git("rev-list", f"origin/{br}..HEAD")
    if rev.returncode != 0:
        return []
    out = []
    for sha in rev.stdout.split():
        files = _git("show", "--name-only", "--pretty=format:", sha).stdout.split()
        if any(not f.startswith(paths) for f in files):
            out.append(sha[:7])
    return out


def user_name() -> str:
    r = _git("config", "user.name")
    return r.stdout.strip()


def status() -> dict[str, Any]:
    br = target()
    paths = _paths()
    changed = _git("status", "--porcelain", "--", *paths).stdout.splitlines() if paths else []
    _git("fetch", "--quiet", "origin", br)
    ahead = behind = None
    rev = _git("rev-list", "--left-right", "--count", f"origin/{br}...HEAD")
    if rev.returncode == 0 and rev.stdout.strip():
        b, a = rev.stdout.split()
        ahead, behind = int(a), int(b)
    return {
        "branch": branch(),
        "target": br,
        "ignored": ignored_history(paths),
        "uncommitted": len(changed),
        "changed": changed[:50],
        "ahead": ahead,
        "behind": behind,
        "remote": _git("remote", "get-url", "origin").stdout.strip(),
    }


def _out(*procs: subprocess.CompletedProcess) -> str:
    parts = []
    for p in procs:
        if p is None:
            continue
        parts.append("$ git " + " ".join(p.args[1:]))
        if p.stdout.strip():
            parts.append(p.stdout.rstrip())
        if p.stderr.strip():
            parts.append(p.stderr.rstrip())
    return "\n".join(parts)


def _plural(n: int, one: str, few: str, many: str) -> str:
    return f"{n} {one if n == 1 else few if n < 5 else many}"


def _message(changed: list[str]) -> str:
    """Zhrnutie do commit správy: koľko behov, mriežok, profilov a analytík sa pridáva."""
    rel = {name: Path(d).relative_to(REPO).as_posix() + "/" for name, d in (
        ("runs", RUNS_DIR), ("sweeps", SWEEPS_DIR), ("profiles", PROFILES_DIR),
        ("analytics", ANALYTICS_DIR), ("archive", ARCHIVE_DIR))}
    runs: set[str] = set()
    counts = {"sweeps": 0, "profiles": 0, "analytics": 0, "archive": 0}
    deleted = 0
    for line in changed:
        code, path = line[:2], line[3:].strip().strip('"').replace("\\", "/")
        if "D" in code:
            deleted += 1
            continue
        if path.startswith(rel["runs"]):
            runs.add(path[len(rel["runs"]):].split("/")[0])
        for name in counts:
            if path.startswith(rel[name]):
                counts[name] += 1
    parts = []
    if runs:
        parts.append(_plural(len(runs), "beh", "behy", "behov") + " backtestu")
    if counts["sweeps"]:
        parts.append(_plural(counts["sweeps"], "výsledok", "výsledky", "výsledkov") + " hľadania")
    if counts["profiles"]:
        parts.append(_plural(counts["profiles"], "profil", "profily", "profilov"))
    if counts["analytics"]:
        parts.append(_plural(counts["analytics"], "analytiku", "analytiky", "analytík"))
    if counts["archive"]:
        parts.append(_plural(counts["archive"], "súbor", "súbory", "súborov") + " archívu behov")
    text = ("Pridaj " + " a ".join(parts) + " z webapp") if parts else "Uprac históriu behov z webapp"
    if deleted:
        text += f" (odstránených súborov: {deleted})"
    return text


#: Koľko commitov profilu dozadu sa hľadá ten, ktorý hodnotu v HEAD nastavil.
_PROFILE_HISTORY = 30

_MISSING = object()


def _retired_fields(strategy: str) -> set[str]:
    """Zrušené polia stratégie — tie profil stratiť smie (webapp ich do nového profilu nedá)."""
    try:
        from tradebot.strategies import get_spec

        return set(get_spec(strategy).config_cls.RETIRED_FIELDS)
    except Exception:  # neznáma stratégia: Push kvôli tomu nepadne, len nič neodpustí
        return set()


def _json_at(rev: str, path: str) -> dict[str, Any] | None:
    r = _git("show", f"{rev}:{path}")
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _last_change(path: str, key: str, value: Any) -> tuple[str, str, Any] | None:
    """Commit, ktorý `key` v profile nastavil na `value` (stav v HEAD): (sha, autor, hodnota predtým)."""
    log = _git("log", f"-n{_PROFILE_HISTORY}", "--format=%H%x09%an", "--", path)
    if log.returncode != 0:
        return None
    for line in log.stdout.splitlines():
        sha, _, author = line.partition("\t")
        before = _json_at(f"{sha}^", path) or {}
        if before.get(key, _MISSING) != value:
            return sha, author, before.get(key, _MISSING)
    return None


def _insert_like(work: dict[str, Any], head: dict[str, Any], restored: dict[str, Any]) -> dict[str, Any]:
    """`work` s doplnenými kľúčmi — chýbajúci ide za kľúč, za ktorým je v HEAD, nech je diff len ten riadok."""
    out = dict(work)
    order = list(head)
    for key, value in restored.items():
        if key in out:
            out[key] = value
            continue
        keys = list(out)
        before = [k for k in order[:order.index(key)] if k in out]
        at = keys.index(before[-1]) + 1 if before else 0
        out = dict([*((k, out[k]) for k in keys[:at]), (key, value), *((k, out[k]) for k in keys[at:])])
    return out


def _restore_profiles(changed: list[str], me: str) -> list[str]:
    """Vráti do upravených profilov, čo z HEAD stratili, a zoznam opráv do výstupu Push.

    Kontrolujú sa hodnoty configu (kľúče bez podtržníka), nie metadáta: nový `_title` či `_comment`
    je legitímna úprava. Doplní sa kľúč, ktorý v súbore chýba (webapp zapisuje celý config, sama
    ho nevyhodí — okrem zrušených polí stratégie), a hodnota, ktorá sa rovná stavu spred commitu
    iného autora, než je `me`; vlastnú zmenu tester vrátiť smie.
    """
    prefix = Path(PROFILES_DIR).relative_to(REPO).as_posix() + "/"
    notes: list[str] = []
    for line in changed:
        code, path = line[:2], line[3:].strip().strip('"').replace("\\", "/")
        if "M" not in code or " -> " in path or not path.startswith(prefix) or not path.endswith(".json"):
            continue
        head = _json_at("HEAD", path)
        file = REPO / path
        try:
            text = file.read_text(encoding="utf-8")
            work = json.loads(text)
        except (OSError, json.JSONDecodeError):
            continue
        if head is None or not isinstance(work, dict):
            continue
        retired = _retired_fields(str(work.get("_strategy") or head.get("_strategy") or LEGACY_STRATEGY))
        restored: dict[str, Any] = {}
        for key, value in head.items():
            if key.startswith("_") or key in retired or work.get(key, _MISSING) == value:
                continue
            change = _last_change(path, key, value)
            od = f" (od {change[0][:7]}, {change[1]})" if change else ""
            if key not in work:
                restored[key] = value
                notes.append(f"{path}: {key} chýbal, doplnený {json.dumps(value, ensure_ascii=False)}{od}")
            elif change and change[1] != me and work[key] == change[2]:
                restored[key] = value
                notes.append(f"{path}: {key} vrátený na {json.dumps(work[key], ensure_ascii=False)}, "
                             f"ponechaný {json.dumps(value, ensure_ascii=False)}{od}")
        if restored:
            lines = text.split("\n")
            indent = len(lines[1]) - len(lines[1].lstrip(" ")) if len(lines) > 1 else None
            write_json_atomic(file, _insert_like(work, head, restored), indent=indent or None,
                              newline=text.endswith("\n"))
    return notes


def _restore_note(notes: list[str]) -> str:
    if not notes:
        return ""
    return ("Profily mali starší obsah než GitHub (prepísané z kópie spred aktualizácie klonu) — "
            "hodnoty z GitHubu sú doplnené späť:\n  " + "\n  ".join(notes) + "\n")


def _pull_rebase(br: str) -> list[subprocess.CompletedProcess]:
    """`fetch` + `rebase --autostash origin/<vetva>` namiesto `pull --rebase origin <vetva>`.

    `git pull` berie cieľ rebase z `.git/FETCH_HEAD`. Keď v tej istej chvíli beží iný `fetch` (`status()`
    z webapp, agent hubu, sledovanie zmien kódu), zapíšu do FETCH_HEAD dva riadky a pull padne
    s „fatal: Cannot rebase onto multiple branches“. Ref `origin/<vetva>` sa zapisuje so zámkom,
    takže rebase na neho súbeh nerozbije.
    """
    f = _git("fetch", "origin", br)
    if f.returncode != 0:
        return [f]
    return [f, _git("rebase", "--autostash", f"origin/{br}")]


def pull() -> dict[str, Any]:
    br = target()
    steps = _pull_rebase(br)
    out = _out(*steps)
    ok = steps[-1].returncode == 0
    if not ok and _auth_failed(out):
        out += chr(10) + AUTH_HELP
    return {"ok": ok, "output": out, **status()}


def push(message: str | None = None, author: str | None = None) -> dict[str, Any]:
    br = target()
    steps: list[subprocess.CompletedProcess] = []
    paths = _paths()
    ignorovane = ignored_history(paths)
    if ignorovane:
        return {"ok": False, "output": _ignored_note(ignorovane), **status()}
    changed = _git("status", "--porcelain", "--", *paths).stdout.splitlines() if paths else []
    oprava = _restore_note(_restore_profiles(changed, author or user_name()))

    def _res(ok: bool, out: str) -> dict[str, Any]:
        return {"ok": ok, "output": oprava + out, **status()}

    if changed:
        a = _git("add", "-A", "--", *paths)
        steps.append(a)
        if a.returncode != 0:
            return _res(False, _out(*steps))
        msg = message or _message(changed)
        args = ["commit", "-m", msg, "--", *paths]
        if author:
            args = ["-c", f"user.name={author}", *args]
        c = _git(*args)
        steps.append(c)
        if c.returncode != 0:
            return _res(False, _out(*steps))
        # Čo ostalo necommitnuté, by Push ticho nechal doma — to sa hlási, nie prehltne.
        ostalo = _git("status", "--porcelain", "--", *paths).stdout.splitlines()
        if ostalo:
            note = (f"Push zrušený: po commite ostalo necommitnutých {len(ostalo)} zmien v histórii:\n  "
                    + "\n  ".join(ostalo[:10]))
            return _res(False, _out(*steps) + chr(10) + note)
    steps += _pull_rebase(br)
    if steps[-1].returncode != 0:
        return _res(False, _out(*steps))
    foreign = _foreign_commits(br)
    if foreign:
        note = (f"Push zrušený: vetva {branch()} má oproti origin/{br} commity mimo histórie "
                f"behov ({', '.join(foreign)}). Kód z testerského klonu do {br} neposielam "
                "— rieš to pull requestom.")
        return _res(False, _out(*steps) + chr(10) + note)
    q = _git("push", "origin", f"HEAD:{br}")
    steps.append(q)
    out = _out(*steps)
    if q.returncode != 0 and _auth_failed(out):
        # commit ostáva lokálne — po prihlásení stačí kliknúť Push znova
        out += chr(10) + AUTH_HELP
    return _res(q.returncode == 0, out)
