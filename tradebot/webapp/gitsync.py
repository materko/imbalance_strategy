"""Git synchronizácia dát testera — len `runs/` a `profiles/`, nič iné.

Tester klikne „Push": zmeny v histórii behov a vo vlastných profiloch sa commitnú,
spraví sa `pull --rebase` a `push`. Kód ani iné súbory sa nedotýkajú, takže si tester
nemôže omylom commitnúť rozpracovanú zmenu stratégie. Konflikt prakticky nevzniká
(každý beh je nový adresár), ale keby predsa, výstup gitu sa zobrazí celý.

Cieľom je vždy **`main`** (alebo to, čo je v `TRADEBOT_GIT_BRANCH`), nie vetva, na ktorej
klon práve stojí: keď webapp bežala z vývojárskeho worktree, história skončila na
vetve `claude/...` a v `main` po nej nebolo ani stopy. Ak by pritom mala vetva
commity mimo `runs/` a `profiles/`, Push to odmietne — kód testera do `main`
nepatrí, ten ide cez pull request.
"""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import subprocess
from pathlib import Path
from typing import Any

from .profiles import PROFILES_DIR
from .store import RUNS_DIR

REPO = Path(__file__).resolve().parents[2]


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
    dirs = [Path(RUNS_DIR), Path(PROFILES_DIR)]
    return [d.relative_to(REPO).as_posix() for d in dirs if d.exists()]


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


def _message(changed: list[str]) -> str:
    """Zhrnutie do commit správy: koľko behov a koľko profilov sa mení."""
    rel_profiles = Path(PROFILES_DIR).relative_to(REPO).as_posix()
    profiles = sum(1 for line in changed if rel_profiles in line.replace("\\", "/"))
    runs = len(changed) - profiles
    parts = []
    if runs:
        parts.append(f"{runs} {'beh' if runs == 1 else 'behy' if runs < 5 else 'behov'} backtestu")
    if profiles:
        parts.append(f"{profiles} {'profil' if profiles == 1 else 'profily' if profiles < 5 else 'profilov'}")
    return "Pridaj " + " a ".join(parts) + " z webapp"


def pull() -> dict[str, Any]:
    br = target()
    p = _git("pull", "--rebase", "--autostash", "origin", br)
    out = _out(p)
    if p.returncode != 0 and _auth_failed(out):
        out += chr(10) + AUTH_HELP
    return {"ok": p.returncode == 0, "output": out, **status()}


def push(message: str | None = None, author: str | None = None) -> dict[str, Any]:
    br = target()
    steps: list[subprocess.CompletedProcess] = []
    paths = _paths()
    changed = _git("status", "--porcelain", "--", *paths).stdout.splitlines() if paths else []
    if changed:
        steps.append(_git("add", "--", *paths))
        msg = message or _message(changed)
        args = ["commit", "-m", msg, "--", *paths]
        if author:
            args = ["-c", f"user.name={author}", *args]
        c = _git(*args)
        steps.append(c)
        if c.returncode != 0:
            return {"ok": False, "output": _out(*steps), **status()}
    p = _git("pull", "--rebase", "--autostash", "origin", br)
    steps.append(p)
    if p.returncode != 0:
        return {"ok": False, "output": _out(*steps), **status()}
    foreign = _foreign_commits(br)
    if foreign:
        note = (f"Push zrušený: vetva {branch()} má oproti origin/{br} commity mimo histórie "
                f"behov ({', '.join(foreign)}). Kód z testerského klonu do {br} neposielam "
                "— rieš to pull requestom.")
        return {"ok": False, "output": _out(*steps) + chr(10) + note, **status()}
    q = _git("push", "origin", f"HEAD:{br}")
    steps.append(q)
    out = _out(*steps)
    if q.returncode != 0 and _auth_failed(out):
        # commit ostáva lokálne — po prihlásení stačí kliknúť Push znova
        out += chr(10) + AUTH_HELP
    return {"ok": q.returncode == 0, "output": out, **status()}
