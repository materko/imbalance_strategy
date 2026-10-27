"""Push súborov živých dát do gitu z vlastného klonu pluginu — nie z klonu, z ktorého hub beží.

Kód hubu je plytký klon, ktorý `tester.hub.update` každých pár minút tvrdo prepíše na `origin/main` (a vo
verejnom repozitári je bez tokenu), takže commitovať doň nejde. Plugin si preto drží vlastný klon
`hub_data/plugins/livedata/repo`: plytký (`--depth 1`), partial (`--filter=blob:none`) a sparse len na
`data/live/` — pár megabajtov. Pred každým pushom ho prepíše na najnovší `origin/<vetva>`, nakopíruje
súbory, commitne a pushne; keď medzitým pushol niekto iný (non-fast-forward), skúsi to celé znova.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

__all__ = ["push_files", "PushError", "mask"]

#: Toľkokrát sa push zopakuje, keď ho predbehol iný commit.
ATTEMPTS = 3


class PushError(RuntimeError):
    """Git zlyhal (sieť, práva, konflikt); text je bez tokenu."""


def mask(text: str) -> str:
    """URL s tokenom (`https://x:TOKEN@github.com`) do logu a chýb bez tokenu."""
    return re.sub(r"(https?://)[^/@\s]+@", r"\1***@", str(text))


#: `GIT_SSH_COMMAND` pre push cez SSH (deploy kľúč); nastaví `push_files(ssh_key=…)`.
_ENV: dict[str, str] = {}


def ssh_command(key: Path, known_hosts: Path) -> str:
    """SSH len s deploy kľúčom pluginu; kľúč hostiteľa (github.com) sa uloží pri prvom spojení vedľa neho."""
    return (f'ssh -i "{Path(key).as_posix()}" -o IdentitiesOnly=yes -o BatchMode=yes '
            f'-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="{Path(known_hosts).as_posix()}"')


def _git(repo: Path, *args: str, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env={**os.environ, **_ENV} if _ENV else None)
    if check and r.returncode != 0:
        raise PushError(mask(f"git {args[0]}: {(r.stderr or r.stdout).strip()[:400]}"))
    return r


def _prepare(repo: Path, remote: str, sub: str) -> None:
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        _git(repo, "init", "-q")
        _git(repo, "remote", "add", "origin", remote)
    _git(repo, "remote", "set-url", "origin", remote)   # token sa mohol vymeniť
    _git(repo, "config", "remote.origin.promisor", "true")
    _git(repo, "config", "remote.origin.partialclonefilter", "blob:none")
    _git(repo, "config", "core.sparseCheckout", "true")
    info = repo / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "sparse-checkout").write_text(f"/{sub}/\n", encoding="utf-8")


def push_files(repo: Path, remote: str, branch: str, src_root: Path, rels: list[str], message: str,
               author: str, *, sub: str = "data/live", log: Callable[[str], None] | None = None,
               ssh_key: Path | None = None) -> str:
    """Skopíruje `src_root/<rel>` do `<klon>/<sub>/<rel>`, commitne a pushne na `branch`.
    `ssh_key` = deploy kľúč pre `remote` v tvare `git@github.com:…` (inak HTTPS s tokenom v URL).
    Vráti nový commit, alebo `""`, keď sa v gite nič nezmenilo. Chyba = `PushError`."""
    say = log or (lambda _s: None)
    repo = Path(repo)
    _ENV.clear()
    if ssh_key is not None:
        if not Path(ssh_key).is_file():
            raise PushError(f"deploy kľúč {Path(ssh_key).name} nie je")
        _ENV["GIT_SSH_COMMAND"] = ssh_command(Path(ssh_key), Path(ssh_key).with_name("known_hosts"))
    m = re.match(r"^\s*(.*?)\s*<([^>]+)>\s*$", author or "")
    name, email = (m.group(1) or "TradeBot hub", m.group(2)) if m else ("TradeBot hub", "hub@tradebot.local")
    _prepare(repo, remote, sub)
    for attempt in range(1, ATTEMPTS + 1):
        _git(repo, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", branch)
        _git(repo, "checkout", "-q", "-B", branch, "FETCH_HEAD")
        _git(repo, "reset", "-q", "--hard", "FETCH_HEAD")
        for rel in rels:
            dst = repo / sub / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(src_root) / rel, dst)
        _git(repo, "add", "--", *[f"{sub}/{rel}" for rel in rels])
        if _git(repo, "diff", "--cached", "--quiet", check=False).returncode == 0:
            say("git: nič nové")
            return ""
        _git(repo, "-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-q", "-m", message)
        r = _git(repo, "push", "-q", "origin", f"HEAD:{branch}", check=False)
        if r.returncode == 0:
            return _git(repo, "rev-parse", "HEAD").stdout.strip()
        out = (r.stderr or r.stdout)
        if attempt < ATTEMPTS and re.search(r"non-fast-forward|fetch first|rejected", out):
            say(f"git: push predbehol iný commit, skúšam znova ({attempt}/{ATTEMPTS})")
            continue
        raise PushError(mask(f"git push: {out.strip()[:400]}"))
    raise PushError("git push: predbehnutý aj po opakovaní")
