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
            "fibomgcnet"]


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
