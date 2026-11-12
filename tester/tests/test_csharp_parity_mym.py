"""Stratégie na Micro Dow (MYM) s C# jadrom proti Python predlohe — bar po bare, na rovnosť (12. 11. 2026).

Kľúče `ibsentrymymnet`, `noamymnet`, `wprmymnet`, `sigmamymnet` sú tie isté C# enginy ako na NQ / ES / MGC s vlastným
kľúčom kvôli profilom a nasadeniu; test overí, že na dátach MYM dávajú presne to isté ako Python kópie (`…mym`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tester.compare import csharp_parity  # noqa: E402
from tradebot.strategies import STRATEGIES  # noqa: E402

#: Python kópia -> C# kľúč, testované okno (posledný rok, IBS EZ kvôli rýchlosti štvrťrok)
PAIRS = {
    "ibsentrymym": ("ibsentrymymnet", "2026-03-01", "2026-06-01"),
    "noamym": ("noamymnet", "2025-09-04", "2026-09-04"),
    "wprmym": ("wprmymnet", "2025-09-04", "2026-09-04"),
    "sigmamym": ("sigmamymnet", "2025-09-04", "2026-09-04"),
}


def _profiles(net: str) -> list[Path]:
    spec = STRATEGIES[net]
    return sorted(Path(spec.profile_dir).glob("*.json"))


@pytest.mark.parametrize("base,path", [(b, p) for b, (n, _f, _t) in PAIRS.items() for p in _profiles(n)],
                         ids=lambda v: v if isinstance(v, str) else v.stem)
def test_mym_parita(base, path, tmp_path):
    net, date_from, date_to = PAIRS[base]
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    data["_instrument"] = "mym_databento"
    profile = tmp_path / path.name
    profile.write_text(json.dumps(data), encoding="utf-8")
    tf = int(str(data.get("_timeframe", "5m")).rstrip("m"))
    try:
        res = csharp_parity.compare(base, net, str(profile), "mym", tf, date_from, date_to)
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 10, res["counts"]
