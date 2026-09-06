"""Git synchronizácia histórie behov — len adresár `runs/`, nič iné.

Tester klikne „Push": zmeny v `runs/` sa commitnú, spraví sa `pull --rebase`
a `push`. Kód ani iné súbory sa nedotýkajú, takže si tester nemôže omylom
commitnúť rozpracovanú zmenu stratégie. Konflikt v `runs/` prakticky nevzniká
(každý beh je nový adresár), ale keby predsa, výstup gitu sa zobrazí celý.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .store import RUNS_DIR

REPO = Path(__file__).resolve().parents[2]


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=check,
    )


def _rel_runs() -> str:
    return RUNS_DIR.relative_to(REPO).as_posix()


def branch() -> str:
    r = _git("branch", "--show-current")
    return r.stdout.strip() or "HEAD"


def user_name() -> str:
    r = _git("config", "user.name")
    return r.stdout.strip()


def status() -> dict[str, Any]:
    br = branch()
    changed = _git("status", "--porcelain", "--", _rel_runs()).stdout.splitlines()
    _git("fetch", "--quiet", "origin", br)
    ahead = behind = None
    rev = _git("rev-list", "--left-right", "--count", f"origin/{br}...HEAD")
    if rev.returncode == 0 and rev.stdout.strip():
        b, a = rev.stdout.split()
        ahead, behind = int(a), int(b)
    return {
        "branch": br,
        "uncommitted_runs": len(changed),
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


def pull() -> dict[str, Any]:
    br = branch()
    p = _git("pull", "--rebase", "--autostash", "origin", br)
    return {"ok": p.returncode == 0, "output": _out(p), **status()}


def push(message: str | None = None, author: str | None = None) -> dict[str, Any]:
    br = branch()
    steps: list[subprocess.CompletedProcess] = []
    changed = _git("status", "--porcelain", "--", _rel_runs()).stdout.splitlines()
    if changed:
        steps.append(_git("add", "--", _rel_runs()))
        n = len(changed)
        msg = message or f"Pridaj {n} {'beh' if n == 1 else 'behy' if n < 5 else 'behov'} backtestu z webapp"
        args = ["commit", "-m", msg, "--", _rel_runs()]
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
    q = _git("push", "origin", br)
    steps.append(q)
    return {"ok": q.returncode == 0, "output": _out(*steps), **status()}
