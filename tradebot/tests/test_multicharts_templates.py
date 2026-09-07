"""Šablóny pre PowerLanguage .NET Editor musia mať metódy študie PRIAMO v triede.

MultiCharts x Python kontroluje `Create`/`CalcBar` v triede zo vloženého kódu; zdedené
metódy nevidí a odmietne kompiláciu ("No required methods found").
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tradebot.strategies import STRATEGIES

REQUIRED = {"GetInputs", "GetInputValue", "SetInputValue", "Create", "StartCalc", "CalcBar", "StopCalc", "Destroy"}
TEMPLATES = Path("deploy/multicharts")


@pytest.mark.parametrize("spec", list(STRATEGIES.values()), ids=lambda s: s.key)
def test_sablona_ma_vsetky_metody_studie_v_triede(spec):
    src = (TEMPLATES / spec.multicharts_template).read_text(encoding="utf-8")
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1, "v šablóne má byť práve jedna trieda (MultiCharts ju hľadá podľa mena študie)"
    cls = classes[0]
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert REQUIRED <= methods, f"{spec.multicharts_template}: chýba {sorted(REQUIRED - methods)}"
    # ako šablóna bety: trieda bez rodiča a balík tradebot sa neimportuje na úrovni modulu
    assert cls.bases == [], "trieda študie nesmie mať rodiča (MultiCharts x Python ju inak neoverí)"
    top_imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any("tradebot" in ast.dump(n) for n in top_imports), "tradebot importuj až v metódach"


def test_sablona_ibs_sa_da_naimportovat_a_deleguje(monkeypatch):
    """Vykoná šablónu ako MultiCharts (exec) a overí, že metódy volajú balík."""
    import sys
    import types

    from tradebot.strategies.ibs.multicharts import IBSSignal

    clr = types.ModuleType("clr")
    clr.AddReference = lambda name: None
    for name in ("clr", "System", "System.Drawing", "PowerLanguage"):
        monkeypatch.setitem(sys.modules, name, clr if name == "clr" else types.ModuleType(name))
    src = (TEMPLATES / STRATEGIES["ibs"].multicharts_template).read_text(encoding="utf-8")
    ns: dict = {}
    exec(compile(src, "IBS_Signal.py", "exec"), ns)
    study = ns["IBS"]()
    assert study.GetInputs() == [] and study.GetInputValue("x") is None
    assert isinstance(study._sig(), IBSSignal) and study._sig() is study._sig()
    called = []
    monkeypatch.setattr(IBSSignal, "CalcBar", lambda self: called.append("CalcBar"))
    study.CalcBar()
    assert called == ["CalcBar"]
