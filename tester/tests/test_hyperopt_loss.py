"""Loss funkcia z plánu — kritérium rozhoduje, čo je „lepšie".

Bez kritéria sa optimum nedá určiť: „najvyšší winrate pri drawdowne do 15 %" a „najvyšší
zisk pri tom istom limite" majú iného víťaza. Testy strážia, že každé kritérium radí
podľa svojho čísla a že mantinely (počet obchodov, strop na drawdown) nepustia dopredu
konfiguráciu, ktorá ich nedrží.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("freqtrade")
pd = pytest.importorskip("pandas")

from tradebot.adapters.freqtrade import hyperplan as hp
from tradebot.core.paths import REPO

sys.path.insert(0, str(REPO / "deploy" / "freqtrade" / "user_data" / "hyperopts"))
from TradebotPlanLoss import TradebotPlanLoss  # noqa: E402

ZACIATOK = datetime(2025, 9, 4)
KONIEC = ZACIATOK + timedelta(days=365)
KAPITAL = 10_000.0


def obchody(pnl: list[float], *, cena: float = 100.0, mnozstvo: float = 1.0):
    """Výsledok behu v tvare, aký loss funkcia dostáva od Freqtradu."""
    return pd.DataFrame({
        "profit_abs": pnl,
        "is_short": [False] * len(pnl),
        "open_rate": [cena] * len(pnl),
        "close_rate": [cena + p / mnozstvo for p in pnl],
        "amount": [mnozstvo] * len(pnl),
    })


def loss(results, plan: hp.Plan | None, monkeypatch) -> float:
    monkeypatch.setattr(hp, "_CACHE", {})
    monkeypatch.setattr("TradebotPlanLoss.plan_from_env", lambda: plan)
    return TradebotPlanLoss.hyperopt_loss_function(
        results=results, trade_count=len(results), min_date=ZACIATOK, max_date=KONIEC,
        starting_balance=KAPITAL,
    )


def plan(**over) -> hp.Plan:
    data = {"strategy": "ibs", "knobs": {"rrRatio": {"low": 2, "high": 6}}}
    data.update(over)
    return hp.Plan.from_dict(data)


# --------------------------------------------------------------------------- #
# kritériá
# --------------------------------------------------------------------------- #


def test_winrate_radi_podla_podielu_ziskovych(monkeypatch):
    p = plan(goal="winrate", min_trades=60)
    lepsi = obchody([10.0] * 70 + [-10.0] * 30)      # 70 %
    horsi = obchody([10.0] * 50 + [-10.0] * 50)      # 50 %

    assert loss(lepsi, p, monkeypatch) == pytest.approx(-70.0)
    assert loss(lepsi, p, monkeypatch) < loss(horsi, p, monkeypatch)


def test_zisk_neriesi_winrate(monkeypatch):
    """Kritérium „zisk" má dať prednosť menej presnej, ale výnosnejšej konfigurácii."""
    p = plan(goal="profit", min_trades=60)
    malo_ale_velke = obchody([100.0] * 30 + [-10.0] * 70)   # winrate 30 %, +2300
    casto_ale_male = obchody([5.0] * 70 + [-5.0] * 30)      # winrate 70 %, +200

    assert loss(malo_ale_velke, p, monkeypatch) < loss(casto_ale_male, p, monkeypatch)


def test_drawdown_sa_minimalizuje(monkeypatch):
    p = plan(goal="drawdown", min_trades=60)
    plynuly = obchody([10.0] * 100)
    s_prepadom = obchody([10.0] * 50 + [-100.0] * 20 + [10.0] * 30)

    assert loss(plynuly, p, monkeypatch) < loss(s_prepadom, p, monkeypatch)


def test_break_even_je_predvolene_kriterium_a_neriesi_velkost_pozicie(monkeypatch):
    """To isté číslo pri polovičnom objeme je lepšia konfigurácia — v čistom PnL to nevidno."""
    p = plan(min_trades=60)
    assert p.goal == "break_even"

    velky_objem = obchody([10.0] * 100, cena=100.0, mnozstvo=10.0)
    maly_objem = obchody([10.0] * 100, cena=100.0, mnozstvo=1.0)

    assert loss(maly_objem, p, monkeypatch) < loss(velky_objem, p, monkeypatch)


# --------------------------------------------------------------------------- #
# mantinely
# --------------------------------------------------------------------------- #


def test_malo_obchodov_nikdy_neprebije_slusne_obchodujucu_epochu(monkeypatch):
    """Regresia z merania: Calmar vyhlásil za víťaza epochu so 7 obchodmi a +17 %."""
    p = plan(goal="profit", min_trades=60)
    sedem_skvelych = obchody([500.0] * 7)
    stovka_slusnych = obchody([10.0] * 100)

    assert loss(sedem_skvelych, p, monkeypatch) > loss(stovka_slusnych, p, monkeypatch)
    assert loss(sedem_skvelych, p, monkeypatch) > 1000.0


def test_penalizacia_za_malo_obchodov_rastie_so_vzdialenostou(monkeypatch):
    """Plochá stena je pre optimalizátor slepá — nevidí, ktorým smerom ísť."""
    p = plan(min_trades=60)
    assert loss(obchody([10.0] * 40), p, monkeypatch) < loss(obchody([10.0] * 10), p, monkeypatch)


def test_limit_na_obchody_sa_prepocita_na_dlzku_okna(monkeypatch):
    """60 obchodov za rok je 15 za kvartál — inak by krátke okno neprešlo nikdy."""
    p = plan(min_trades=60)
    monkeypatch.setattr(hp, "_CACHE", {})
    monkeypatch.setattr("TradebotPlanLoss.plan_from_env", lambda: p)
    kvartal = TradebotPlanLoss.hyperopt_loss_function(
        results=obchody([10.0] * 20), trade_count=20, min_date=ZACIATOK,
        max_date=ZACIATOK + timedelta(days=90), starting_balance=KAPITAL,
    )
    assert kvartal < 0                              # 20 obchodov za kvartál limit spĺňa


def test_prekroceny_drawdown_padne_za_epochu_v_limite(monkeypatch):
    p = plan(goal="profit", max_dd=10.0, min_trades=60)
    v_limite = obchody([10.0] * 100)                            # bez prepadu
    mimo = obchody([100.0] * 60 + [-300.0] * 20 + [100.0] * 20)  # vyšší zisk, hlboký prepad

    assert loss(mimo, p, monkeypatch) > loss(v_limite, p, monkeypatch)
    assert loss(mimo, p, monkeypatch) > 1000.0


def test_bez_planu_beh_nespadne(monkeypatch):
    """Loss sa dá spustiť aj ručne bez `TRADEBOT_HYPEROPT_PLAN` — vtedy platí break-even."""
    assert loss(obchody([10.0] * 100), None, monkeypatch) < 0
