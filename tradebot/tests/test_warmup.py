"""Predhistória (`tradebot.core.warmup`): 300 barov grafu pre stratégiu a vlastná predhistória
indikátorov na vyššom TF.

Rozhodnutie 2026-09-17: predhistória grafu je taká, aká bola (Freqtrade `startup_candle_count`
300); stavová logika (dni S/R, predošlá seansa, zóny divergencie) ju nezväčšuje. Supertrend
a ADX na vlastnom TF (a vyššie TF divergencie) dostanú **svoje** bary pred prvým barom grafu
(`seed_engine`) — z dát pred behom, poskladané cez `tradebot.core.candles`, bez pohľadu dopredu.

Audit A8 platí ďalej: Freqtrade adaptér stavia skúšobný engine s TF behu, nie triedy
(Supertrend 5m na 5m grafe nesmie padnúť na „nie je násobkom 3m").
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from tradebot.core import Bar, load_profile
from tradebot.core.candles import resample_ohlcv
from tradebot.core.history import BarHistory
from tradebot.core.warmup import SEED_WEIGHT, Warmup, decay_bars, ema_bars, on_chart, rma_bars, seed_engine
from tradebot.strategies import get_spec

MIN = 60_000
HOUR = 60 * MIN

# --------------------------------------------------------------------------- #
# Vzorce
# --------------------------------------------------------------------------- #


def test_rekurzivne_priemery():
    assert decay_bars(0.1) == 29          # 0,9^29 = 4,7 % < 5 %, 0,9^28 = 5,2 %
    assert 0.9 ** 29 < SEED_WEIGHT < 0.9 ** 28
    assert rma_bars(10) == 39 and rma_bars(14) == 55
    assert ema_bars(26) == 65 and ema_bars(9) == 23
    assert decay_bars(0.5) == 5 and decay_bars(1.0) == 0


def test_seeded_polozka_nezvacsuje_predhistoriu_grafu():
    assert on_chart(40, 3, 3) == 40
    assert on_chart(40, 60, 3) == 41 * 20                     # len informácia do logu
    w = (Warmup(3).add("okno", 264)
         .add_seeded("Supertrend 10", 40, 60, lambda bars, partial: None))
    assert w.chart_bars == 264
    assert [n.name for n in w.seeds] == ["Supertrend 10"] and [n.name for n in w.chart_needs] == ["okno"]
    assert w.seed_span_ms == 2 * 41 * HOUR + 4 * 24 * HOUR       # rezerva na víkendy a diery
    assert "Supertrend 10 @60m: 40 vlastnych" in w.describe()


def test_atr_po_rozbehu_zabudne_na_zaciatok():
    """Dva ATR nad tými istými barmi, jeden začal o 200 barov neskôr: po `atr_warmup_bars`
    sa líšia najviac o `SEED_WEIGHT` z pôvodného rozdielu (plus zaokrúhlenie)."""
    rng = random.Random(7)
    bars, price = [], 100.0
    for i in range(400):
        move = rng.uniform(-1, 1) * (3.0 if i < 200 else 0.5)  # prudká zmena volatility
        o, price = price, price + move
        bars.append(Bar(time=i, open=o, high=max(o, price) + abs(move), low=min(o, price) - abs(move),
                        close=price, volume=1.0))
    full, late = BarHistory(maxlen=10, atr_len=14), BarHistory(maxlen=10, atr_len=14)
    for b in bars[:200]:
        full.append(b)
    need = late.atr_warmup_bars
    for b in bars[200:200 + 14]:
        full.append(b)
        late.append(b)
    start_diff = abs(full.atr - late.atr)
    for b in bars[200 + 14:200 + need]:
        full.append(b)
        late.append(b)
    assert abs(full.atr - late.atr) <= SEED_WEIGHT * start_diff * 1.2


# --------------------------------------------------------------------------- #
# Predhistória grafu: ako predtým, ≤ 300 pre default profily
# --------------------------------------------------------------------------- #


def _ibs_cfg(st_tf: str | None = "60", adx_tf: str | None = None):
    cfg, inst = load_profile(get_spec("ibs").default_profile, strategy="ibs")
    data = cfg.to_dict()
    data.update(tradeDirection="Indicator", indSupertrend=st_tf is not None,
                indAdx=adx_tf is not None)
    if st_tf is not None:
        data["stTimeframe"] = st_tf
    if adx_tf is not None:
        data["adxTimeframe"] = adx_tf
    return type(cfg).from_dict(data), inst


@pytest.mark.parametrize("key", ["ibs", "divergence", "gap", "orb", "range", "sdzone", "structure", "demo_breakout"])
@pytest.mark.parametrize("chart", [2, 3, 5, 15])
def test_predhistoria_grafu_je_maximum_potrieb_grafu(key, chart):
    spec = get_spec(key)
    cfg, inst = load_profile(spec.default_profile, strategy=key)
    try:
        engine = spec.engine_factory(cfg, inst, chart)
    except ValueError:
        pytest.skip("vyšší TF stratégie nie je násobkom grafu")
    needs = engine.warmup.chart_needs
    assert needs and engine.required_history == max(n.chart_bars(chart) for n in needs)
    assert all(n.bars > 0 for n in engine.warmup.needs)
    assert engine.required_history <= 300          # default profil sa zmestí do minima triedy


@pytest.mark.parametrize("chart", [2, 3, 5, 15])
def test_supertrend_a_adx_maju_vlastnu_predhistoriu(chart):
    from tradebot.strategies.ibs.engine import IBSEngine

    plain_cfg, inst = load_profile(get_spec("ibs").default_profile, strategy="ibs")
    cfg, _ = _ibs_cfg(st_tf="60", adx_tf="60")
    engine = IBSEngine(cfg, inst, chart)
    assert engine.required_history == IBSEngine(plain_cfg, inst, chart).required_history
    seeds = {n.name: (n.bars, n.tf_minutes) for n in engine.warmup.seeds}
    st_bars = rma_bars(cfg.stAtrPeriod) + 1                                    # Supertrend(10): 40
    adx_bars = 1 + rma_bars(cfg.adxDiLength) + rma_bars(cfg.adxSmoothing)     # 14/14: 111
    assert seeds == {f"Supertrend {cfg.stAtrPeriod}": (st_bars, 60),
                     f"ADX/DMI {cfg.adxDiLength}/{cfg.adxSmoothing}": (adx_bars, 60)}
    assert (st_bars, adx_bars) == (40, 111)


def test_divergencia_vyssie_tf_maju_vlastnu_predhistoriu():
    spec = get_spec("divergence")
    cfg, inst = load_profile(spec.default_profile, strategy="divergence")
    engine = spec.engine_factory(cfg, inst, 15)
    assert engine.required_history == int(cfg.maxBars) + int(cfg.prd) + 40
    seeds = {n.tf_minutes: n.bars for n in engine.warmup.seeds}
    assert set(seeds) == {int(cfg.htfMinutes), int(cfg.htf2Minutes)}
    assert seeds[int(cfg.htf2Minutes)] >= int(cfg.zoneMaxBars) + int(cfg.zonePrd2)


# --------------------------------------------------------------------------- #
# Freqtrade: startup_candle_count 300, TF behu (A8)
# --------------------------------------------------------------------------- #


def _ibs_strategy(tmp_path: Path, monkeypatch, run_tf: str | None, config_extra: dict | None = None,
                  **fields):
    pytest.importorskip("freqtrade")
    from freqtrade.enums import RunMode

    from tradebot.strategies.ibs.freqtrade import IBSImbalanceStrategy

    src = get_spec("ibs").profile_dir / f"{get_spec('ibs').default_profile}.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    data.update(tradeDirection="Indicator", **fields)
    path = tmp_path / "ind.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("TRADEBOT_PROFILE", str(path))
    config = {"timeframe": run_tf, "exchange": {"pair_whitelist": [], "name": "binance"},
              "runmode": RunMode.BACKTEST, "stake_currency": "USDT", "dry_run": True,
              "trading_mode": "futures", "margin_mode": "isolated", **(config_extra or {})}
    return IBSImbalanceStrategy(config)


def test_supertrend_5m_na_grafe_5m_nepadne(tmp_path, monkeypatch):
    """Reprodukcia z auditu: default triedy je 3m a 5m nie je jeho násobok."""
    s = _ibs_strategy(tmp_path, monkeypatch, "5m", indSupertrend=True, indAdx=False, stTimeframe="5")
    assert type(s).timeframe == "3m" and s.run_timeframe == "5m"
    assert s.startup_candle_count == 300


@pytest.mark.parametrize("run_tf", ["2m", "3m", "5m", "15m"])
def test_startup_300_aj_so_supertrendom_a_adx_60m(tmp_path, monkeypatch, run_tf):
    s = _ibs_strategy(tmp_path, monkeypatch, run_tf, indSupertrend=True, indAdx=True,
                      stTimeframe="60", adxTimeframe="60")
    assert s.startup_candle_count == 300
    runner = s._runner("BTC/USDT:USDT")
    assert runner.chart_tf_minutes == int(run_tf[:-1])
    assert runner.engine.required_history <= s.startup_candle_count


def test_bez_tf_v_configu_plati_tf_triedy(tmp_path, monkeypatch):
    s = _ibs_strategy(tmp_path, monkeypatch, None, indSupertrend=True, indAdx=False, stTimeframe="60")
    assert s.run_timeframe == "3m" and s.startup_candle_count == 300


# --------------------------------------------------------------------------- #
# Seeding: stav na prvom bare = stav po tých istých baroch naživo, bez pohľadu dopredu
# --------------------------------------------------------------------------- #

#: 2026-01-05 00:00 UTC (pondelok)
T_START = 1_767_571_200_000


def _m1(days: int, seed: int = 11, gap: tuple[int, int] | None = None):
    """1m sviečky s meniacou sa volatilitou; `gap` = (od minúty, počet) vynechaných minút."""
    import pandas as pd

    rng = random.Random(seed)
    rows, price = [], 50_000.0
    for i in range(days * 1440):
        if gap and gap[0] <= i < gap[0] + gap[1]:
            continue
        vol = 20.0 if (i // 4000) % 2 else 6.0
        o = price
        price = max(1000.0, o + rng.gauss(0.02, vol))
        h = max(o, price) + abs(rng.gauss(0, vol / 2))
        lo = min(o, price) - abs(rng.gauss(0, vol / 2))
        rows.append((T_START + i * MIN, o, h, lo, price, rng.uniform(1, 5)))
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df[["date", "open", "high", "low", "close", "volume"]]


def _chart_bars(m1, chart_tf: int) -> list[Bar]:
    from tradebot.adapters.multicharts.emulator import bars_from_frame

    return bars_from_frame(m1, chart_tf)


def _state(gate):
    """Stav brány, ktorý rozhoduje o smere, a rozpracovaný HTF bar."""
    out = {}
    if gate.st is not None:
        st = gate.st
        out["st"] = (st.trend, st.up, st.dn, st._rma, st._prev_close, tuple(st._tr_window), st.ready)
        a = gate._st_src.agg
        out["st_agg"] = (a._open_ts, a._o, a._h, a._l, a._c)
    if gate.dmi is not None:
        d = gate.dmi
        prev = d._prev
        # objem sa v DMI nepoužíva a jeho súčet sa v poslednom mieste líši podľa poradia sčítania
        out["dmi"] = (d.adx, d.plus, d.minus, d._tr.value, d._dx.value,
                      None if prev is None else (prev.time, prev.open, prev.high, prev.low, prev.close))
        a = gate._dmi_src.agg
        out["dmi_agg"] = (a._open_ts, a._o, a._h, a._l, a._c)
    out["states"] = gate.states
    return out


@pytest.fixture(scope="module")
def m1_long():
    # 12 dní 1m, s dvojhodinovou dierou v dátach (víkend/výpadok) uprostred
    return _m1(12, gap=(6 * 1440 + 300, 120))


@pytest.mark.parametrize("chart", [2, 3])
@pytest.mark.parametrize("which", ["st", "adx"])
def test_seeding_rovna_sa_behu_z_tych_istych_barov_aj_dlhemu_behu(m1_long, chart, which):
    from tradebot.strategies.ibs.engine import IBSEngine

    cfg, inst = _ibs_cfg(st_tf="60" if which == "st" else None, adx_tf="60" if which == "adx" else None)
    chart_bars = _chart_bars(m1_long, chart)
    # prvý bar behu uprostred hodiny: 9. deň 07:21 (2m: 07:20)
    first_ms = (T_START + 9 * 86_400_000 + 7 * HOUR + 21 * MIN) // (chart * MIN) * (chart * MIN)
    k = next(i for i, b in enumerate(chart_bars) if b.time == first_ms)

    seeded = IBSEngine(cfg, inst, chart)
    got = seed_engine(seeded, m1_long, first_ms)
    need = seeded.warmup.seeds[0]
    assert list(got.values()) == [need.bars] and need.bars == (40 if which == "st" else 111)
    ind = seeded.direction_gate.st if which == "st" else seeded.direction_gate.dmi
    assert ind.bars == need.bars and ind.warmed

    # (a) presne: brána, ktorá naživo prešla tými istými barmi grafu (od začiatku seed okna)
    same = IBSEngine(cfg, inst, chart).direction_gate
    hourly = resample_ohlcv(m1_long, 60)
    hourly_ms = (hourly["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
    closed = [t for t in hourly_ms if t < first_ms // HOUR * HOUR]
    seed_from = closed[-need.bars]                  # diera v dátach: periódy bez baru sa nepočítajú
    for b in chart_bars[:k]:
        if b.time >= seed_from:
            same.on_bar(b)
    # (b) dlhý beh od začiatku dát (9 dní pred behom)
    long = IBSEngine(cfg, inst, chart).direction_gate
    for b in chart_bars[:k]:
        long.on_bar(b)

    gate = seeded.direction_gate
    for g in (gate, same, long):
        for b in chart_bars[k:k + 30]:        # prvý bar behu a pol hodiny ďalej (uzavrie HTF bar)
            g.on_bar(b)
    assert _state(gate) == _state(same)
    assert gate.states is not None and gate.states == long.states
    ls = _state(long)
    if which == "st":
        assert gate.st.trend == long.st.trend
        assert gate.st.line == pytest.approx(long.st.line, rel=2e-3)
        assert gate.st._rma == pytest.approx(long.st._rma, rel=SEED_WEIGHT)
        assert _state(gate)["st_agg"] == ls["st_agg"]
    else:
        assert gate.dmi.state(cfg.adxThreshold) == long.dmi.state(cfg.adxThreshold)
        assert gate.dmi.adx == pytest.approx(long.dmi.adx, rel=0.05)
        assert _state(gate)["dmi_agg"] == ls["dmi_agg"]


def test_seeding_bez_pohladu_dopredu(m1_long):
    """Dáta od prvého baru ďalej (aj rozpracovaná hodina po ňom) stav po seedingu nemenia."""
    from tradebot.strategies.ibs.engine import IBSEngine

    cfg, inst = _ibs_cfg(st_tf="60", adx_tf="60")
    first_ms = T_START + 9 * 86_400_000 + 7 * HOUR + 21 * MIN
    a = IBSEngine(cfg, inst, 3)
    seed_engine(a, m1_long, first_ms)

    changed = m1_long.copy()
    ms = changed["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000
    after = ms >= first_ms
    assert after.any() and (~after).any()
    for col in ("open", "high", "low", "close"):
        changed.loc[after, col] = changed.loc[after, col] * 1.5 + 777.0
    b = IBSEngine(cfg, inst, 3)
    seed_engine(b, changed, first_ms)
    assert _state(a.direction_gate) == _state(b.direction_gate)

    # kontrola testu: zmena PRED prvým barom stav zmení
    before = (ms < first_ms) & (ms >= first_ms - 3 * HOUR)
    changed.loc[before, "close"] = changed.loc[before, "close"] + 500.0
    c = IBSEngine(cfg, inst, 3)
    seed_engine(c, changed, first_ms)
    assert _state(c.direction_gate) != _state(a.direction_gate)


def test_seeding_len_pred_prvym_barom(m1_long):
    from tradebot.strategies.ibs.engine import IBSEngine

    cfg, inst = _ibs_cfg(st_tf="60")
    engine = IBSEngine(cfg, inst, 3)
    engine.on_bar(_chart_bars(m1_long.iloc[:3], 3)[0])
    with pytest.raises(RuntimeError, match="pred prvým barom"):
        seed_engine(engine, m1_long, T_START + 9 * 86_400_000)


def test_bez_dat_pred_behom_sa_rozbieha(m1_long):
    """Začiatok archívu: indikátor nemá svoje bary, brána nepovolí smer, kým ich nenazbiera."""
    from tradebot.core.types import Direction
    from tradebot.strategies.ibs.engine import IBSEngine

    cfg, inst = _ibs_cfg(st_tf="60")
    engine = IBSEngine(cfg, inst, 3)
    assert seed_engine(engine, m1_long, T_START) == {f"Supertrend {cfg.stAtrPeriod}": 0}
    gate = engine.direction_gate
    bars = _chart_bars(m1_long, 3)
    for b in bars[: 20 * 39]:                         # 39 hodín: ATR už je, ale nie je ustálený
        gate.on_bar(b)
    assert gate.st.ready and not gate.st.warmed
    assert not gate.allowed(Direction.LONG) and "SA ROZBIEHA" in gate.describe()
    for b in bars[20 * 39: 20 * 41]:
        gate.on_bar(b)
    assert gate.st.warmed and gate.states is not None


def test_divergencia_seeding_rovna_sa_behu_z_tych_istych_barov():
    spec = get_spec("divergence")
    cfg, inst = load_profile(spec.default_profile, strategy="divergence")
    m15 = resample_ohlcv(_m1(60, seed=3), 15)
    chart = _chart_bars(m15, 15)
    first_ms = T_START + 55 * 86_400_000 + 13 * HOUR + 30 * MIN
    k = next(i for i, b in enumerate(chart) if b.time == first_ms)

    seeded = spec.engine_factory(cfg, inst, 15)
    got = seed_engine(seeded, m15, first_ms)
    assert all(got[n.name] == n.bars for n in seeded.warmup.seeds)

    ref = spec.engine_factory(cfg, inst, 15)
    for htf, twin in ((seeded.htf1, ref.htf1), (seeded.htf2, ref.htf2)):
        ms = htf.agg.ms
        start = first_ms // ms * ms - htf.warmup_bars * ms     # 15m dáta bez dier
        for b in chart[:k + 20]:
            if b.time >= start:
                twin.push(b)
        for b in chart[k:k + 20]:
            htf.push(b)
        assert (htf.st.trend, htf.st.line, htf.bull, htf.bear, list(htf.window)) == \
               (twin.st.trend, twin.st.line, twin.bull, twin.bear, list(twin.window))
        assert (htf.agg._open_ts, htf.agg._c) == (twin.agg._open_ts, twin.agg._c)


# --------------------------------------------------------------------------- #
# Emulátor MultiCharts a Freqtrade: ten istý stav na prvom bare
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("chart", [2, 3])
def test_emulator_a_freqtrade_rovnaky_stav_na_prvom_bare(tmp_path, monkeypatch, m1_long, chart):
    pytest.importorskip("freqtrade")
    from freqtrade.data.history import get_datahandler
    from freqtrade.enums import CandleType

    from tradebot.adapters.multicharts.emulator import emulate

    pair = "BTC/USDT:USDT"
    tf = f"{chart}m"
    first_ms = (T_START + 9 * 86_400_000 + 7 * HOUR + 21 * MIN) // (chart * MIN) * (chart * MIN)
    step = chart * MIN

    # emulátor: 1m dáta celé, beh od first_ms (jeden bar)
    cfg, inst = _ibs_cfg(st_tf="60", adx_tf="60")
    _, mc = emulate(cfg, inst, m1_long, chart, from_ms=first_ms, to_ms=first_ms + step)

    # Freqtrade: TF behu na disku (z 1m cez candles.py), DataFrame behu začína first_ms
    datadir = tmp_path / "data"
    (datadir / "futures").mkdir(parents=True)
    handler = get_datahandler(datadir, "feather")
    handler.ohlcv_store(pair, tf, data=resample_ohlcv(m1_long, chart), candle_type=CandleType.FUTURES)
    s = _ibs_strategy(tmp_path, monkeypatch, tf,
                      config_extra={"datadir": str(datadir), "dataformat_ohlcv": "feather",
                                    "candle_type_def": CandleType.FUTURES},
                      indSupertrend=True, indAdx=True, stTimeframe="60", adxTimeframe="60")
    ft_df = resample_ohlcv(m1_long, chart)
    ms = ft_df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000
    ft_df = ft_df[(ms >= first_ms) & (ms < first_ms + step)].reset_index(drop=True)
    s.dp = None                                   # Freqtrade ho dosadí až pri štarte botu
    s.populate_indicators(ft_df, {"pair": pair})
    ft = s._runners[pair]

    assert ft.last_ts == mc.last_ts == first_ms
    ft_state, mc_state = _state(ft.engine.direction_gate), _state(mc.engine.direction_gate)
    assert ft_state == mc_state
    assert ft.engine.direction_gate.st.warmed and ft.engine.direction_gate.dmi.warmed
    assert ft_state["states"] is not None
