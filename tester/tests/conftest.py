"""Spoločné nastavenie testov testera."""

import pytest


@pytest.fixture(autouse=True)
def _webapp_bez_vyberu(monkeypatch):
    """Testy webapp počítajú so všetkými stratégiami registry — výber `tester/webapp_vyber.json` (čo webapp
    ukazuje na Mac mini) sa v nich nepoužije; samotný výber má vlastný test (test_webapp_vyber.py)."""
    from tester.webapp import vyber

    monkeypatch.setattr(vyber, "WEBAPP_SELECTION", vyber.WEBAPP_SELECTION.with_name("_neexistuje_vyber.json"))
    monkeypatch.setattr(vyber, "_cache", None)
