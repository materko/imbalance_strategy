"""Verzia kódu repozitára bez závislosti na `tester` — krátky commit HEAD (`git rev-parse --short`).

Používajú ju inštalátory adaptérov (`installed.json` vedľa nainštalovaného kódu platformy,
docs/LIVE.md fáza 2c); hub a agent majú vlastné `tester.hub.gitcode`, ktoré vracia to isté.
"""

from __future__ import annotations

import subprocess

from .paths import REPO

__all__ = ["repo_version"]


def repo_version() -> str:
    """Krátky commit HEAD tohto klonu; prázdny reťazec mimo gitu alebo bez `git`."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""
