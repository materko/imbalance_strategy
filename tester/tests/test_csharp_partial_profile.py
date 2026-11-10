"""Čiastočný profil v NinjaTraderi / MT5 obchoduje to isté, čo úplný (audit N-CS-1).

NT8 a MT5 čítajú profil zo súboru priamo; ručne upravený alebo starý profil nemá všetky kľúče, ktoré dá
`cfg.to_dict()`. C# obaly vstupov (filter trendu / volatility, potvrdenie, typ orderu, veľkosť pozície)
sa preto nesmú zapínať podľa *prítomnosti* kľúča, ale podľa hodnoty — chýbajúci kľúč = default stratégie,
presne ako v Pythone. Test postaví ten istý C# engine z čiastočného a z úplného configu a výstup musí byť
bar po bare rovnaký.
"""

from __future__ import annotations

import json

import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tradebot.adapters.csharp.bridge import open_transport  # noqa: E402
from tradebot.core.candles import resample_ohlcv  # noqa: E402
from tradebot.core.types import INSTRUMENTS  # noqa: E402
from tradebot.strategies import get_spec  # noqa: E402
from tester.tests.test_csharp_parity import _random_walk, _with_ts  # noqa: E402

MNQ = INSTRUMENTS["mnq_databento"]
_INST = json.dumps({"symbol": MNQ.symbol, "venue": MNQ.venue, "tick_size": MNQ.tick_size,
                    "point_value": MNQ.point_value, "qty_step": MNQ.qty_step, "min_qty": MNQ.min_qty,
                    "has_real_volume": MNQ.has_real_volume})
LOOSE = {"lookbackDays": 5, "checkEvery": 15, "maxTradesPerDay": 10}

CASES = {
    # filter trendu bez `trendTF` (default = TF grafu) - C# ho kedysi vynechal
    "noanet-filter_bez_tf": ("noanet", {**LOOSE, "trendFilter": "with", "trendEmaLen": 10}),
    # filter volatility bez kľúča `trendFilter`
    "noanet-volatilita_bez_trendu": ("noanet", {**LOOSE, "volFilter": "high", "volLookback": 30}),
    # pevný počet je pri NOA default (true) - riziko bez `fixedQty` nesmie zapnúť strop straty
    "noanet-riziko_bez_fixedqty": ("noanet", {**LOOSE, "riskDollar": 50.0}),
    # `riskDollar` chýba - default 100 $ zo stratégie, nie 0
    "vwapadxnet-riziko_default": ("vwapadxnet", {"adxMin": 5.0, "maxTrades": 5, "useTimeExit": False}),
}


@pytest.fixture(scope="module")
def bars():
    df = _with_ts(resample_ohlcv(_random_walk(20 * 1440), 5))
    return [(int(r.ts), (float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume)))
            for r in df.itertuples(index=False)]


@pytest.mark.parametrize("name", sorted(CASES))
def test_ciastocny_profil_ako_uplny(bars, name):
    key, partial = CASES[name]
    full = get_spec(key).config_cls.from_dict(dict(partial)).to_dict()
    a = open_transport(key, json.dumps(partial), _INST, 5)
    b = open_transport(key, json.dumps(full), _INST, 5)
    try:
        orders = 0
        for t, ohlcv in bars:
            oa = a.on_bar(t, ohlcv, None, 0.0, False, "")
            ob = b.on_bar(t, ohlcv, None, 0.0, False, "")
            assert oa == ob, (name, t)
            orders += len(oa.get("o") or oa.get("orders") or [])
        assert orders > 0, name   # inak by test nič nepovedal
    finally:
        a.close()
        b.close()


_CS_KEYS = ["ibsnet", "ibsentrynet", "ibsentryesnet", "noanet", "nyvaesnet", "orbnet", "tksnet", "vwapadxnet", "vwaporbnet",
            "fibomgcnet", "sdeurnet"]


def _enum_cases():
    for key in _CS_KEYS:
        for field, enum in sorted(get_spec(key).config_cls.ENUM_FIELDS.items()):
            yield key, field, [e.value for e in enum]


@pytest.mark.parametrize("key,field,values", list(_enum_cases()), ids=lambda v: v if isinstance(v, str) else "")
def test_neznama_hodnota_enumu_je_chyba(key, field, values):
    """Audit N-CS-2: neznáma hodnota enumu v profile (`"Limit"` namiesto `"limit"`) nesmie v NT8 / MT5 ticho
    obchodovať default — engine sa nepostaví, ako v Pythone (`ValueError`). Každá platná hodnota prejde."""
    from tradebot.adapters.csharp.bridge import BridgeError

    def opens(value) -> bool:
        try:
            open_transport(key, json.dumps({field: value}), _INST, 5).close()
            return True
        except (BridgeError, Exception):   # pythonnet hodí .NET výnimku ako Exception
            return False

    for v in values:
        assert opens(v), (key, field, v)
    assert not opens("Nezmysel"), (key, field)


def _cs_strategies() -> list[str]:
    from tradebot.adapters.csharp.engine import CSharpEngine
    from tradebot.strategies import STRATEGIES

    out = []
    for key, spec in sorted(STRATEGIES.items()):
        cfg = spec.config_cls()
        try:
            eng = spec.engine_factory(cfg, MNQ, 5)
        except Exception:  # noqa: BLE001 - stratégia, ktorej default s MNQ nejde, sem nepatrí
            continue
        if isinstance(eng, CSharpEngine):
            out.append(key)
            eng.close()
    return out


def test_neznamy_kluc_profilu_je_v_info_a_uplny_config_ziadny_nema(caplog):
    """N-CS-2: kľúč, ktorý C# nečíta (preklep v ručne upravenom profile NT8 / MT5), sa nesmie stratiť potichu —
    hostiteľ ho vráti v `Info()`. A naopak: úplný config z Pythonu nesmie mať v C# neznáme pole (zabudnutý prepis)."""
    from tradebot.adapters.csharp.engine import CSharpEngine

    t = open_transport("noanet", json.dumps({**LOOSE, "maxTradePerDay": 3, "_title": "x", "trendFilter": "off"}), _INST, 5)
    try:
        assert t.info["unknown_config"] == ["maxTradePerDay"]
    finally:
        t.close()

    keys = _cs_strategies()
    assert len(keys) >= 15
    for key in keys:
        spec = get_spec(key)
        with caplog.at_level("WARNING"):
            eng = CSharpEngine(key, spec.config_cls(), MNQ, 5)
        try:
            assert eng.unknown_config == [], key
        finally:
            eng.close()
    assert "nečíta" not in caplog.text

    class Preklep:
        def to_dict(self):
            return {**LOOSE, "maxTradePerDay": 3}

    with caplog.at_level("WARNING"):
        eng = CSharpEngine("noanet", Preklep(), MNQ, 5)
    eng.close()
    assert eng.unknown_config == ["maxTradePerDay"] and "maxTradePerDay" in caplog.text


def test_obal_trendu_pozna_rovnake_strategie_ako_python():
    """Python zapína filter trendu len configu s `trendFilter` aj `trendTF` (pole `trendFilter` bez `trendTF` je
    vlastný filter stratégie, dnes len Python stratégia `liquidity`), C# podľa hodnoty kľúča `trendFilter`.
    Pre profil, ktorý Python načíta, je to to isté, kým C# stratégia nemá `trendFilter` bez `trendTF`."""
    for key in _cs_strategies():
        cfg = get_spec(key).config_cls()
        assert hasattr(cfg, "trendFilter") == hasattr(cfg, "trendTF"), key


def test_stdio_a_inproc_davaju_to_iste_pre_kazdu_cs_strategiu(bars):
    """N-CS-6: stdio most (TradeBot.Host.exe) sa porovnával len pre `ibsnet` a `orbnet`. Tu každá C# stratégia
    s predvoleným configom: odpoveď hostiteľa na bar musí byť tá istá ako v procese (čísla idú ako bitový vzor)."""
    from tradebot.adapters.csharp.bridge import BridgeError, InprocTransport, StdioTransport

    try:
        InprocTransport("noanet", json.dumps(LOOSE), _INST, 5).close()
    except BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    for key in _cs_strategies():
        cfg = json.dumps(get_spec(key).config_cls().to_dict())
        a, b = InprocTransport(key, cfg, _INST, 5), StdioTransport(key, cfg, _INST, 5)
        try:
            assert a.info == b.info, key
            for t, ohlcv in bars[:1200]:
                assert a.on_bar(t, ohlcv, None, 0.0, False, "") == b.on_bar(t, ohlcv, None, 0.0, False, ""), (key, t)
            assert a.final_drawings(*bars[1199]) == b.final_drawings(*bars[1199]), key
            assert a.stats() == b.stats(), key
        finally:
            a.close()
            b.close()
