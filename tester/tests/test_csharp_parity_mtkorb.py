"""MTK ORB s C# jadrom (`mtkorbnet`) proti Python predlohe (`mtkorb`, logika `orb15`) — bar po bare, na rovnosť.

Prešlé profily `PRESIEL_SMERNICAMI_MTK_ORB_MGC_*` (stop order na hranici OR, len prvý prieraz v smere gapu) aj predloha
ORB 15/5 bez rozšírení (vstup trhom po zavretí za OR, bias predošlého dňa).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tester.compare import csharp_parity  # noqa: E402
from tradebot.core.paths import PROFILES_DIR, STRATEGIES_DIR  # noqa: E402

PROFILES = sorted(PROFILES_DIR.glob("PRESIEL_SMERNICAMI_MTK_ORB_MGC_*.json"))
SRC = STRATEGIES_DIR / "mtkorb" / "configs" / "mgc_databento_5m.json"
VARIANTS = {"predloha_orb15": {"gapFilter": 0, "maxOrWidthMult": 0.0, "firstBreakOnly": False, "entryAtLevel": False,
                               "useDailyBias": True, "maxTradesPerDay": 2, "useWickFilter": True},
            "trhom_v_smere_gapu": {"entryAtLevel": False}}


def _plain(path: Path, tmp_path: Path, extra: dict | None = None) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    data["_instrument"] = "mgc_databento"
    data.update(extra or {})
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def _run(profile: Path, tf: int, date_from: str, date_to: str) -> dict:
    try:
        return csharp_parity.compare("mtkorb", "mtkorbnet", str(profile), "mgc", tf, date_from, date_to)
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")


@pytest.mark.parametrize("path", [SRC, *PROFILES], ids=lambda p: p.stem)
def test_mtkorb_profily(path, tmp_path):
    tf = int(str(json.loads(path.read_text())["_timeframe"]).rstrip("m"))
    res = _run(_plain(path, tmp_path), tf, "2024-09-04", "2026-09-04")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 50, res["counts"]


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_mtkorb_varianty(name, tmp_path):
    res = _run(_plain(SRC, tmp_path, VARIANTS[name]), 5, "2025-09-04", "2026-09-04")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 20, res["counts"]
