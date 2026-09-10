"""Hyperopt priestor z plánu — čo tester navolí, to Freqtrade ladí.

Priestor je normálne časť kódu stratégie: Freqtrade si po triede prejde atribúty a hľadá
v nich `*Parameter` objekty. Tester kód nepíše, takže plán tie objekty dorobí pri importe
triedy. Testy strážia obe strany toho mostu — že sa plán prečíta a odmietne nezmysly,
a že Freqtrade v hotovej triede naozaj nájde presne to, čo je v pláne.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("freqtrade")

from tradebot.adapters.freqtrade import hyperplan as hp
from tradebot.core.types import SizeSpec
from tradebot.strategies import get_spec

IBS = get_spec("ibs")


def plan(**over) -> hp.Plan:
    data = {"strategy": "ibs", "knobs": {"rrRatio": {"low": 2, "high": 6}}}
    data.update(over)
    return hp.Plan.from_dict(data)


# --------------------------------------------------------------------------- #
# typ a rozsah sa berú z configu, nie z vlastnej tabuľky
# --------------------------------------------------------------------------- #


def test_typ_a_rozsah_pochadzaju_z_configu_strategie():
    """Keby si priestor držal vlastnú tabuľku typov, rozišla by sa s tým, čo config prijme."""
    assert hp.knob_kind("rrRatio", IBS) == ("float", {"low": 0.5, "high": 10.0})
    assert hp.knob_kind("slLookback", IBS) == ("int", {"low": 1, "high": 100})
    kind, info = hp.knob_kind("tradeDirection", IBS)
    assert kind == "enum" and info["choices"] == ["Both", "Long only", "Short only"]
    kind, info = hp.knob_kind("minSlDistance", IBS)
    assert kind == "size" and info["unit"] == "pct"
    assert hp.knob_kind("enableTrailing", IBS)[0] == "bool"


def test_neznamy_parameter_a_neladitelny_typ_sa_ohlasia():
    with pytest.raises(ValueError, match="nepozná"):
        hp.knob_kind("nieco", IBS)


def test_zoznam_laditelnych_obsahuje_cisla_prepinace_aj_enumy():
    laditelne = set(hp.tunable(IBS))
    assert {"rrRatio", "slLookback", "tradeDirection", "enableTrailing"} <= laditelne
    # Parametre lámuce paritu sa NEodfiltrujú — tester ich smie ladiť, keď o to stojí.
    assert "legacyPineSizing" in laditelne


# --------------------------------------------------------------------------- #
# čo je generické a čo patrí stratégii
# --------------------------------------------------------------------------- #


def test_genericka_cast_nepozna_ziadnu_strategiu_menom():
    """Pravidlo repozitára: adaptéry poznajú stratégie len cez `StrategySpec`.

    Keby sa do priestoru dostal `if strategy == "ibs"`, pridanie stratégie by znamenalo
    zmenu v adaptéri — a presne to registry existuje, aby netreba bolo.
    """
    zdroj = Path(hp.__file__).read_text(encoding="utf-8")
    from tradebot.strategies import STRATEGIES

    for key in STRATEGIES:
        if key == "ibs":
            continue          # "ibs" je legitímny default `Plan.strategy`
        assert key not in zdroj, f"{key} sa v hyperplan.py nemá objaviť"
    for meno in ("IBSConfig", "IBSImbalanceStrategy", "IBSHyperopt", "ibs_cfg"):
        assert meno not in zdroj, f"{meno} sa v hyperplan.py nemá objaviť"


def test_vedomosti_o_ladeni_si_generik_vyzdvihne_z_registry():
    from tradebot.strategies.hyperopt import StrategyHyperopt

    from tradebot.strategies.ibs.hyperopt import IBSHyperopt

    from dataclasses import replace

    assert hp.knowledge(IBS) is IBSHyperopt
    assert hp.knowledge(get_spec("demo_breakout")).SUGGESTED   # aj ukážka niečo odporúča
    # Stratégia bez vlastnej triedy sa ladiť dá tiež — dostane základ, nie výnimku.
    assert hp.knowledge(replace(IBS, hyperopt_cls=None)) is StrategyHyperopt


def test_odporucania_su_platny_plan():
    """Čo stratégia odporučí, musí ísť rovno použiť — inak je to len komentár."""
    p = hp.Plan.from_dict({"strategy": "ibs", "knobs": hp.knowledge(IBS).suggested_plan()})
    assert {k.name for k in p.knobs} == set(IBS.hyperopt_cls.SUGGESTED)
    hodnoty = hp.parameters(p)
    assert len(hodnoty) == len(p.knobs)


def test_vazby_medzi_parametrami_riesi_strategia():
    """Hyperopt vzťah „koniec okna za začiatkom" vyjadriť nevie — vyberá každý zvlášť.

    Bez opravy by polovica kombinácií dávala okno nulovej dĺžky, teda vetvu priestoru
    bez jediného obchodu, v ktorej optimalizátor blúdi naslepo.
    """
    p = plan(knobs={"sess2TradeStartH": {"low": 6, "high": 15},
                    "sess2TradeEndH": {"low": 6, "high": 23}})
    s = FakeStrategy({"hp_sess2TradeStartH": 14.0, "hp_sess2TradeEndH": 9.0})

    hp.apply(s, p)

    assert s.tb_cfg.sess2TradeStartH == 14
    assert s.tb_cfg.sess2TradeEndH == 15          # posunuté za začiatok


def test_strategia_bez_vazieb_config_nemeni():
    from tradebot.strategies.hyperopt import StrategyHyperopt

    cfg = IBS.config_cls()
    povodny = cfg.to_dict()
    StrategyHyperopt.constrain(cfg)
    assert cfg.to_dict() == povodny


# --------------------------------------------------------------------------- #
# plán
# --------------------------------------------------------------------------- #


def test_vynechany_rozsah_znamena_cely_pine_rozsah():
    knob = plan(knobs={"slLookback": {}}).knobs[0]
    assert (knob.low, knob.high) == (1.0, 100.0)


def test_rozsah_mimo_pine_sa_odmietne():
    for zle, hlaska in (({"low": 0.1, "high": 6}, "pod Pine"), ({"low": 2, "high": 40}, "nad Pine")):
        with pytest.raises(ValueError, match=hlaska):
            plan(knobs={"rrRatio": zle})


def test_prevrateny_rozsah_a_prazdny_plan_su_chyba():
    with pytest.raises(ValueError, match="pod hornou"):
        plan(knobs={"rrRatio": {"low": 6, "high": 2}})
    with pytest.raises(ValueError, match="knobs"):
        plan(knobs={})


def test_enum_berie_zoznam_moznosti_a_kontroluje_ho():
    knob = plan(knobs={"tradeDirection": {"choices": ["Long only", "Both"]}}).knobs[0]
    assert knob.choices == ("Long only", "Both")
    with pytest.raises(ValueError, match="neznáme hodnoty"):
        plan(knobs={"tradeDirection": {"choices": ["Nieco"]}})
    with pytest.raises(ValueError, match="aspoň dve"):
        plan(knobs={"tradeDirection": {"choices": ["Both"]}})


def test_prepinac_bez_zoznamu_znamena_vypnute_aj_zapnute():
    assert plan(knobs={"enableTrailing": {}}).knobs[0].choices == (False, True)


def test_velkostne_pole_si_drzi_jednotku():
    """Ladí sa číslo, nie jednotka — 0,25 v `pct` je iná vec než 0,25 v `atr`."""
    knob = plan(knobs={"minSlDistance": {"low": 0.1, "high": 0.5}}).knobs[0]
    assert knob.unit == "pct"                      # default jednotka poľa z configu
    knob = plan(knobs={"minSlDistance": {"low": 0.1, "high": 0.5, "unit": "atr"}}).knobs[0]
    assert knob.unit == "atr"


def test_plan_prezije_zapis_a_nacitanie(tmp_path: Path):
    povodny = plan(goal="winrate", max_dd=15.0, min_trades=20,
                   knobs={"rrRatio": {"low": 2, "high": 6, "step": 0.5},
                          "tradeDirection": {"choices": ["Long only", "Both"]}})
    cesta = povodny.save(tmp_path / "plan.json")
    znovu = hp.Plan.load(cesta)

    assert znovu == povodny
    assert json.loads(cesta.read_text(encoding="utf-8"))["goal"] == "winrate"


def test_plan_z_prostredia_sa_cita_raz(tmp_path: Path, monkeypatch):
    cesta = plan().save(tmp_path / "plan.json")
    monkeypatch.setattr(hp, "_CACHE", {})
    monkeypatch.setenv("TRADEBOT_HYPEROPT_PLAN", str(cesta))

    prvy = hp.plan_from_env()
    cesta.write_text("{}", encoding="utf-8")       # rozbité, ale už je v cache
    assert hp.plan_from_env() is prvy

    monkeypatch.delenv("TRADEBOT_HYPEROPT_PLAN")
    assert hp.plan_from_env() is None


# --------------------------------------------------------------------------- #
# priestor pre Freqtrade
# --------------------------------------------------------------------------- #


def test_kazdy_typ_dostane_svoj_parameter():
    from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter

    p = hp.parameters(plan(knobs={
        "rrRatio": {"low": 2, "high": 6, "step": 0.5},
        "slLookback": {"low": 5, "high": 40},
        "tradeDirection": {"choices": ["Long only", "Both"]},
    }))
    assert isinstance(p["hp_rrRatio"], DecimalParameter)
    assert isinstance(p["hp_slLookback"], IntParameter)
    assert isinstance(p["hp_tradeDirection"], CategoricalParameter)
    assert all(par.space == hp.SPACE for par in p.values())


def test_krok_urcuje_presnost_nie_mriezku():
    """`DecimalParameter` inú mriežku než desatinné miesta nevie — kto chce dané hodnoty, má sweep."""
    assert hp.parameters(plan(knobs={"rrRatio": {"low": 2, "high": 6, "step": 0.5}}))["hp_rrRatio"].decimals == 1
    assert hp.parameters(plan(knobs={"rrRatio": {"low": 2, "high": 6, "step": 0.01}}))["hp_rrRatio"].decimals == 2
    assert hp.parameters(plan(knobs={"rrRatio": {"low": 2, "high": 6}}))["hp_rrRatio"].decimals == 2


def test_freqtrade_najde_v_triede_presne_priestor_planu(tmp_path: Path, monkeypatch):
    """To podstatné: parameter prilepený pri importe je pre Freqtrade nerozoznateľný.

    A musí byť vo vlastnom priestore `plan`, nie v `buy`/`sell` — inak by `--spaces plan`
    ladil aj to, čo je napísané v stratégii, a tester by menil, o čom nevie.
    """
    from freqtrade.strategy.hyper import detect_all_parameters

    from tradebot.adapters.freqtrade.base import TradebotStrategyBase

    p = plan(knobs={"rrRatio": {"low": 2, "high": 6}, "slLookback": {"low": 5, "high": 40}})
    monkeypatch.setattr(hp, "_CACHE", {})
    monkeypatch.setenv("TRADEBOT_HYPEROPT_PLAN", str(p.save(tmp_path / "plan.json")))

    class Pokus(TradebotStrategyBase):
        STRATEGY_KEY = "ibs"

    priestory = detect_all_parameters(Pokus)
    assert sorted(priestory[hp.SPACE]) == ["hp_rrRatio", "hp_slLookback"]


def test_plan_inej_strategie_sa_na_triedu_nedostane(tmp_path: Path, monkeypatch):
    from tradebot.adapters.freqtrade.base import TradebotStrategyBase

    p = hp.Plan.from_dict({"strategy": "ibs", "knobs": {"rrRatio": {"low": 2, "high": 6}}})
    monkeypatch.setattr(hp, "_CACHE", {})
    monkeypatch.setenv("TRADEBOT_HYPEROPT_PLAN", str(p.save(tmp_path / "plan.json")))

    class Cudzia(TradebotStrategyBase):
        STRATEGY_KEY = "demo_breakout"

    assert [a for a in dir(Cudzia) if a.startswith(hp.ATTR_PREFIX)] == []


# --------------------------------------------------------------------------- #
# hodnoty epochy do configu
# --------------------------------------------------------------------------- #


class FakeParam:
    def __init__(self, value):
        self.value = value


class FakeStrategy:
    """Toľko zo stratégie, koľko `apply` potrebuje."""

    def __init__(self, hodnoty: dict):
        self.tb_cfg = IBS.config_cls()
        for attr, value in hodnoty.items():
            setattr(self, attr, FakeParam(value))


def test_hodnoty_epochy_idu_do_configu_v_spravnom_type():
    p = plan(knobs={"rrRatio": {"low": 2, "high": 6}, "slLookback": {"low": 5, "high": 40},
                    "minSlDistance": {"low": 0.1, "high": 0.5, "unit": "pct"},
                    "tradeDirection": {"choices": ["Long only", "Both"]}})
    s = FakeStrategy({"hp_rrRatio": 4.5, "hp_slLookback": 12.0,
                      "hp_minSlDistance": 0.25, "hp_tradeDirection": "Long only"})

    hp.apply(s, p)

    assert s.tb_cfg.rrRatio == pytest.approx(4.5)
    assert s.tb_cfg.slLookback == 12 and isinstance(s.tb_cfg.slLookback, int)
    assert s.tb_cfg.minSlDistance == SizeSpec(value=0.25, unit="pct")
    assert s.tb_cfg.tradeDirection.value == "Long only"
