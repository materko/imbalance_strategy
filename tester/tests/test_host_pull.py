"""docker/host-pull.sh nad skutočnými git repami: obnova po prerušenom checkoute (srvnas 20.–23. 11. 2026).

Prerušený checkout na JuiceFS nechal index na starom HEAD, strom napoly nový (nové súbory
netrackované) a osirelý MERGE_AUTOSTASH; každý ďalší `pull` potom padal. Tu sa ten stav poskladá
ručne a skript ho musí sám obnoviť, nestratiť lokálne zmeny a vrátiť 0 len pri HEAD == origin/main.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tradebot.core import paths

SKRIPT = paths.REPO / "docker" / "host-pull.sh"


def _sh() -> str | None:
    sh = shutil.which("sh")
    if sh is None and os.name == "nt" and (g := shutil.which("git")):
        kand = Path(g).resolve().parents[1] / "usr" / "bin" / "sh.exe"      # Git for Windows
        sh = str(kand) if kand.exists() else None
    return sh


SH = _sh()
pytestmark = pytest.mark.skipif(SH is None or shutil.which("git") is None, reason="chýba sh alebo git")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "core.autocrlf=false", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()


def zapis(koren: Path, rel: str, text: str) -> None:
    p = koren / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def commit(koren: Path, subory: dict[str, str], sprava: str) -> str:
    for rel, text in subory.items():
        zapis(koren, rel, text)
    git(koren, "add", "-A")
    git(koren, "commit", "-qm", sprava)
    return git(koren, "rev-parse", "HEAD")


def nastav(koren: Path, identita: bool = True) -> None:
    git(koren, "config", "core.autocrlf", "false")
    if identita:
        git(koren, "config", "user.email", "t@t")
        git(koren, "config", "user.name", "t")


def spusti(klon: Path) -> tuple[int, str, list[str]]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", HOME=str(klon.parent / "home"))   # bez identity zo stroja
    env["PATH"] = str(Path(SH).parent) + os.pathsep + env.get("PATH", "")    # Windows: find/sort z Gitu
    (klon.parent / "home").mkdir(exist_ok=True)
    p = subprocess.run([SH, SKRIPT.as_posix(), klon.as_posix()], capture_output=True, text=True,
                       encoding="utf-8", env=env)
    vysledok = (klon / "tester" / "hub_pull_result").read_text(encoding="utf-8")
    assert "\r" not in vysledok
    riadky = vysledok.splitlines()
    assert int(riadky[1]) == p.returncode
    return p.returncode, "\n".join(riadky[2:]), riadky


GITIGNORE = "tester/hub_pull_request*\ntester/hub_pull_result*\ntester/hub_pull_conflicts/\n"


@pytest.fixture
def repa(tmp_path: Path):
    """origin (bare), autor (pushuje ako webapp), agent (klon, ktorý pulluje host-pull.sh)."""
    origin, autor, agent = tmp_path / "origin.git", tmp_path / "autor", tmp_path / "agent"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(autor))
    nastav(autor)
    commit(autor, {".gitignore": GITIGNORE, "tester/.keep": "", "kod.py": "x = 1\n", "lokalny.txt": "a\n",
                   "poznamky.txt": "p\n"}, "základ")
    git(autor, "push", "-q", "origin", "main")
    git(tmp_path, "clone", "-q", str(origin), str(agent))
    nastav(agent, identita=False)       # ako morky na srvnas: stash musí prejsť aj bez identity
    return autor, agent


def nove_behy(autor: Path, n: int = 30) -> dict[str, str]:
    behy = {f"tester/runs/b{i:03d}/run.json": f'{{"i": {i}}}\n' for i in range(n)}
    behy["kod.py"] = "x = 2\n"
    commit(autor, behy, "Pridaj behy z webapp")
    git(autor, "push", "-q", "origin", "main")
    return behy


def test_obnova_po_prerusenom_checkoute(repa):
    autor, agent = repa
    stary = git(agent, "rev-parse", "HEAD")
    behy = nove_behy(autor)
    novy = git(autor, "rev-parse", "HEAD")
    git(agent, "fetch", "-q", "origin")

    # osirelý MERGE_AUTOSTASH: lokálna zmena poznamky.txt, ktorú pull odložil a už nevrátil
    zapis(agent, "poznamky.txt", "p\nlokálne\n")
    autostash = git(agent, "stash", "create")
    git(agent, "checkout", "-q", "--", "poznamky.txt")
    gd = agent / ".git"
    (gd / "MERGE_AUTOSTASH").write_text(autostash + "\n")
    (gd / "AUTO_MERGE").write_text(git(agent, "rev-parse", "HEAD^{tree}") + "\n")
    zamok = gd / "index.lock"
    zamok.write_text("")
    stare = time.time() - 3600
    os.utime(zamok, (stare, stare))
    # polovičný checkout: časť nových behov už v strome (netrackované, zhodné), kod.py už nový
    for rel in list(behy)[:20]:
        zapis(agent, rel, behy[rel])
    zapis(agent, "tester/runs/b025/run.json", '{"i": "iný obsah"}\n')     # kolízia, ale odlišná
    # a skutočná lokálna zmena trackovaného súboru, ktorá musí prežiť
    zapis(agent, "lokalny.txt", "a\nmoja zmena\n")
    assert git(agent, "rev-parse", "HEAD") == stary

    kod, vystup, _ = spusti(agent)
    assert kod == 0, vystup
    assert git(agent, "rev-parse", "HEAD") == novy
    assert (agent / "lokalny.txt").read_text(encoding="utf-8") == "a\nmoja zmena\n"
    assert (agent / "poznamky.txt").read_text(encoding="utf-8") == "p\nlokálne\n"         # autostash vrátený
    assert (agent / "kod.py").read_text(encoding="utf-8") == "x = 2\n"
    assert (agent / "tester/runs/b025/run.json").read_text(encoding="utf-8") == behy["tester/runs/b025/run.json"]
    zaloha = list((agent / "tester" / "hub_pull_conflicts").glob("*/tester/runs/b025/run.json"))
    assert len(zaloha) == 1 and "iný obsah" in zaloha[0].read_text(encoding="utf-8")
    for f in ("MERGE_AUTOSTASH", "AUTO_MERGE", "index.lock"):
        assert not (gd / f).exists(), f
    assert git(agent, "stash", "list") == ""
    assert "zhodné s origin/main: 20" in vystup and "Updating files" not in vystup
    assert {r.strip() for r in git(agent, "status", "--porcelain", "-uall").splitlines()} == {"M lokalny.txt", "M poznamky.txt"}

    kod, vystup, _ = spusti(agent)          # ďalší beh: nič na práci, rc 0
    assert kod == 0 and "už aktuálne" in vystup, vystup
    assert (agent / "lokalny.txt").read_text(encoding="utf-8") == "a\nmoja zmena\n"


def test_konflikt_stashu_necha_stash_a_cisty_strom(repa):
    autor, agent = repa
    zapis(agent, "kod.py", "x = 99\n")      # lokálne mení ten istý riadok ako origin
    nove_behy(autor)
    novy = git(autor, "rev-parse", "HEAD")
    kod, vystup, _ = spusti(agent)
    assert kod == 3, vystup                 # HEAD == origin/main, ale zmeny sa nevrátili
    assert git(agent, "rev-parse", "HEAD") == novy
    assert (agent / "kod.py").read_text(encoding="utf-8") == "x = 2\n"
    assert "stash@{0}" in vystup and git(agent, "stash", "list").count("host-pull") == 1
    assert git(agent, "status", "--porcelain", "--untracked-files=no") == ""
    kod, vystup, _ = spusti(agent)
    assert kod == 0 and "ostáva 1 odložených" in vystup, vystup


def test_lokalne_commity_sa_neprepisu(repa):
    autor, agent = repa
    nastav(agent)
    lokalny = commit(agent, {"lokalny.txt": "a\ncommit\n"}, "lokálny commit")
    kod, vystup, _ = spusti(agent)          # origin sa nepohol: HEAD je pred ním
    assert kod == 1 and "nepushnuté" in vystup, vystup
    assert git(agent, "rev-parse", "HEAD") == lokalny

    nove_behy(autor)
    novy = git(autor, "rev-parse", "HEAD")
    kod, vystup, _ = spusti(agent)          # rozišli sa: rebase, lokálny commit ostáva navrchu
    assert kod == 1, vystup
    assert git(agent, "rev-parse", "HEAD~1") == novy
    assert (agent / "lokalny.txt").read_text(encoding="utf-8") == "a\ncommit\n"


def test_cerstvy_zamok_necha_klon_tak(repa):
    autor, agent = repa
    nove_behy(autor)
    stary = git(agent, "rev-parse", "HEAD")
    (agent / ".git" / "index.lock").write_text("")
    kod, vystup, _ = spusti(agent)
    assert kod == 1 and "beží iný git" in vystup
    assert git(agent, "rev-parse", "HEAD") == stary
