"""Stratégia tržnej štruktúry: engine na syntetických baroch.

Najdôležitejší test celého súboru je `test_swing_sa_nepouzije_skor_nez_je_potvrdeny`
a jeho dvojička s invariantom. Swing sa dá potvrdiť až `swingRight` barov po tom, čo
nastal; keby ho engine použil skôr — na vstup, na SL alebo len na kresbu —, bol by to
pohľad dopredu, ktorý v backteste vyzerá ako edge a v ostrom behu neexistuje. Bez týchto
dvoch testov je všetko ostatné v tomto súbore bezcenné.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tradebot.adapters.freqtrade import EngineRunner
from tradebot.core import BTCUSDT_BINANCE, Bar, DrawKind, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType, TradeDirection
from tradebot.strategies.structure import (
    EntryMode,
    ExitMode,
    SlMode,
    StructureConfig,
    StructureEngine,
)

T0 = 1_756_684_800_000
MIN5 = 300_000
INST = BTCUSDT_BINANCE

#: Malý ATR, aby bol nenulový skôr než na 14. bare — testy sú krátke.
BASE = dict(swingLeft=2, swingRight=2, atrLen=5)


# --------------------------------------------------------------------------- #
# generátor barov
# --------------------------------------------------------------------------- #


def _bar(i: int, open_: float, close: float) -> Bar:
    """Bar s knôtom v smere pohybu — vďaka tomu sú high aj low v nohe striktne monotónne
    a swing je práve na obratovom bare, bez plató a bez dohadov."""
    if close >= open_:
        high, low = close + 0.5, open_ - 0.1
    else:
        high, low = open_ + 0.1, close - 0.5
    return Bar(time=T0 + i * MIN5, open=open_, high=high, low=low, close=close, volume=10.0)


def zigzag(pivots: list[float], per_leg: int = 6) -> list[Bar]:
    """Bary, ktoré prechádzajú danými úrovňami; obrat je vždy na poslednom bare nohy."""
    bars: list[Bar] = []
    price = pivots[0]
    for target in pivots[1:]:
        step = (target - price) / per_leg
        for _ in range(per_leg):
            nxt = price + step
            bars.append(_bar(len(bars), price, nxt))
            price = nxt
    return bars


#: Scenár, na ktorom stoja testy udalostí. Vychádza z neho:
#:   idx  5 swing high 112 (potvrdený 7),  idx 11 swing low 96 (potvrdený 13)
#:   idx 16 BOS nahor (neutrál -> bullish), idx 17 swing high 120 (potvrdený 19)
#:   idx 22 CHoCH nadol (bullish -> bearish), idx 23 swing low 90 (potvrdený 25)
#:   idx 29 CHoCH nahor (bearish -> bullish)
SCENAR = [100.0, 112.0, 96.0, 120.0, 90.0, 125.0, 110.0]
BOS_UP, CHOCH_DOWN, CHOCH_UP = 16, 22, 29

#: Úzky cikcak: nohy po ~1,6 bodu pri ATR ~0,7, teda pod 3 ATR — čistý šum.
TESNY = [100.0, 100.6, 100.0, 100.6, 100.0, 100.6]


def run(cfg: StructureConfig, bars: list[Bar], ctx_for=None) -> list:
    """Prehrá bary a vráti zoznam `EngineOutput` — jeden na bar."""
    engine = StructureEngine(cfg, INST, 5)
    outs = []
    for i, bar in enumerate(bars):
        ctx = ctx_for(i) if ctx_for else MarketContext(in_trade_window=True)
        outs.append(engine.on_bar(bar, None, ctx))
    return outs


def entries(outs: list) -> dict[int, object]:
    """`index baru -> OrderIntent` pre vstupy."""
    out: dict[int, object] = {}
    for i, o in enumerate(outs):
        for intent in o.orders:
            if intent.action is OrderAction.ENTRY:
                out[i] = intent
    return out


def events(outs: list) -> dict[int, str]:
    """`index baru -> "BOS" | "CHoCH"` z nakreslených štítkov."""
    out: dict[int, str] = {}
    for i, o in enumerate(outs):
        for d in o.drawings:
            if getattr(d, "kind", None) in (DrawKind.ST_BOS, DrawKind.ST_CHOCH):
                out[i] = "CHoCH" if d.kind is DrawKind.ST_CHOCH else "BOS"
    return out


# --------------------------------------------------------------------------- #
# 1. základ
# --------------------------------------------------------------------------- #


def test_defaulty_platia_a_required_history_pokryva_swing_aj_atr():
    cfg = StructureConfig()
    assert cfg.entryMode is EntryMode.CHOCH and cfg.exitMode is ExitMode.RR
    assert cfg.slMode is SlMode.SWING and cfg.slBuffer.unit == "atr" and cfg.minSwingSize.unit == "atr"
    assert cfg.useSession is False  # okno je tvrdenie, ktoré treba najprv zmerať
    engine = StructureEngine(cfg, INST, 5)
    assert engine.required_history >= cfg.swingLeft + cfg.swingRight + 1 + cfg.atrLen


def test_nulove_obchodne_okno_je_chyba_configu():
    from tradebot.core.config import ConfigError

    with pytest.raises(ConfigError, match="nulovú dĺžku"):
        StructureConfig(useSession=True, sessionStartH=9, sessionEndH=9)
    StructureConfig(useSession=False, sessionStartH=9, sessionEndH=9)  # vypnuté = nikomu nevadí


# --------------------------------------------------------------------------- #
# 2. potvrdenie swingu — bod 9 zadania
# --------------------------------------------------------------------------- #


def test_swing_sa_nepouzije_skor_nez_je_potvrdeny():
    """Swing high nastane a hneď potom cena spadne. Engine o ňom nesmie vedieť skôr
    než `swingRight` barov po ňom — ani na kresbu, ani na úroveň, z ktorej rozhoduje."""
    cfg = StructureConfig(swingLeft=2, swingRight=3, atrLen=5)
    bars = zigzag([100.0, 112.0, 80.0], per_leg=6)  # vrchol na idx 5, potom prepad
    engine = StructureEngine(cfg, INST, 5)

    vrchol = bars[5]
    assert vrchol.high == max(b.high for b in bars[:9])  # naozaj je to swing high

    for i, bar in enumerate(bars):
        out = engine.on_bar(bar, None, MarketContext(in_trade_window=True))
        nakreslene = [d for d in out.drawings if getattr(d, "kind", None) is DrawKind.ST_SWING_HIGH]
        if i < 5 + cfg.swingRight:
            assert not nakreslene, f"bar {i}: swing nakreslený skôr, než bol potvrdený"
            assert engine._sw_high != vrchol.high, f"bar {i}: swing použitý ako úroveň skôr, než bol potvrdený"
        elif i == 5 + cfg.swingRight:
            assert len(nakreslene) == 1 and nakreslene[0].y == vrchol.high
            assert nakreslene[0].x_ms == vrchol.time, "značka patrí na bar swingu, nie na bar potvrdenia"
            assert engine._sw_high == vrchol.high


@pytest.mark.parametrize("right", [2, 3, 5, 8])
def test_invariant_ziadna_uroven_ani_kresba_mladsia_nez_potvrdenie(right):
    """To isté ako vyššie, ale ako invariant cez celý beh a pre viac nastavení.

    Na každom bare musí platiť: úroveň, z ktorej engine rozhoduje, aj každá značka
    swingu patrí baru, ktorý je aspoň `swingRight` barov starý.
    """
    cfg = StructureConfig(swingLeft=3, swingRight=right, atrLen=5)
    bars = zigzag(SCENAR + [140.0, 70.0, 130.0], per_leg=7)
    engine = StructureEngine(cfg, INST, 5)
    for i, bar in enumerate(bars):
        out = engine.on_bar(bar, None, MarketContext(in_trade_window=True))
        najmladsi_povoleny = bars[max(0, i - right)].time
        for d in out.drawings:
            if getattr(d, "kind", None) in (DrawKind.ST_SWING_HIGH, DrawKind.ST_SWING_LOW):
                assert d.x_ms <= najmladsi_povoleny, f"bar {i}: kresba swingu z budúcnosti"
        for ts in (engine._sw_high_ts, engine._sw_low_ts):
            if ts:
                assert ts <= najmladsi_povoleny, f"bar {i}: úroveň z nepotvrdeného swingu"


# --------------------------------------------------------------------------- #
# 3. stav štruktúry a udalosti
# --------------------------------------------------------------------------- #


def test_bos_a_choch_nastanu_na_zatvoreni_baru_a_otocia_stav():
    outs = run(StructureConfig(**BASE), zigzag(SCENAR))
    assert events(outs) == {BOS_UP: "BOS", CHOCH_DOWN: "CHoCH", CHOCH_UP: "CHoCH"}


def test_prerazena_uroven_je_spotrebovana_a_udalost_sa_neopakuje():
    """Bez spotrebovania úrovne by BOS „nastával" na každom ďalšom bare nad ňou."""
    outs = run(StructureConfig(**BASE), zigzag(SCENAR))
    assert BOS_UP in events(outs) and BOS_UP + 1 not in events(outs)


def test_dotyk_knotom_nestaci_rozhoduje_zatvorenie():
    """Bar, ktorý swing high preráža knôtom a zavrie sa pod ním, udalosť nespustí."""
    bars = zigzag([100.0, 112.0, 104.0], per_leg=6)  # swing high 112 potvrdený na idx 7
    # idx 12: knôt vysoko nad 112, close pod ním
    bars.append(Bar(time=T0 + 12 * MIN5, open=104.0, high=120.0, low=103.0, close=110.0, volume=10.0))
    bars.append(Bar(time=T0 + 13 * MIN5, open=110.0, high=114.0, low=109.0, close=113.5, volume=10.0))
    outs = run(StructureConfig(**BASE), bars)
    assert 12 not in events(outs), "knôt cez úroveň nesmie spustiť udalosť"
    assert events(outs).get(13) == "BOS", "až zatvorenie nad úrovňou je prielom"


def _swingy(outs: list) -> int:
    return sum(1 for o in outs for d in o.drawings
               if getattr(d, "kind", None) in (DrawKind.ST_SWING_HIGH, DrawKind.ST_SWING_LOW))


def test_maly_swing_sa_ignoruje_ako_sum():
    """`minSwingSize` meria dĺžku nohy voči poslednému prijatému swingu.

    Na úzkom cikcaku (noha ~1,6 bodu, ATR ~0,7) filter 3 ATR neprepustí ani jednu nohu
    a stratégia nemá čo prerážať — presne to sa od filtra šumu čaká.
    """
    tesny = zigzag(TESNY)
    bez_filtra = run(StructureConfig(**BASE), tesny)
    s_filtrom = run(StructureConfig(**BASE, minSwingSize=3.0), tesny)
    assert _swingy(bez_filtra) >= 4
    assert _swingy(s_filtrom) == 1, "prvý swing referenciu nemá, každý ďalší už áno"
    assert not events(s_filtrom), "bez úrovní niet čo prerážať"


def test_filter_sumu_je_symetricky():
    """Keby sa swing high meral len proti poslednému LOW, v šume by sa neprijalo žiadne
    low, referencia by ostala prázdna a všetky high by prešli — a stratégia by
    obchodovala len jednu stranu."""
    tesny = zigzag(TESNY)
    outs = run(StructureConfig(**BASE, minSwingSize=3.0), tesny)
    druhy = {getattr(d, "kind", None) for o in outs for d in o.drawings}
    assert not (DrawKind.ST_SWING_HIGH in druhy and DrawKind.ST_SWING_LOW in druhy)


# --------------------------------------------------------------------------- #
# 4. tri varianty vstupu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode,ocakavane", [
    (EntryMode.BOS, {BOS_UP: Direction.LONG}),
    (EntryMode.CHOCH, {CHOCH_DOWN: Direction.SHORT, CHOCH_UP: Direction.LONG}),
    (EntryMode.SWEEP, {CHOCH_DOWN: Direction.LONG, CHOCH_UP: Direction.SHORT}),
])
def test_variant_vstupu_urcuje_ktora_udalost_a_ktory_smer(mode, ocakavane):
    """`sweep` je zámerne PROTI CHoCH: CHoCH nadol znamená long."""
    outs = run(StructureConfig(**BASE, entryMode=mode), zigzag(SCENAR))
    assert {i: e.direction for i, e in entries(outs).items()} == ocakavane
    for intent in entries(outs).values():
        assert intent.order_type is OrderType.MARKET and intent.plan.qty > 0


def test_smer_obchodov_filtruje_vstupy():
    cfg = dict(BASE, entryMode=EntryMode.CHOCH)
    long_only = entries(run(StructureConfig(**cfg, tradeDirection=TradeDirection.LONG_ONLY), zigzag(SCENAR)))
    short_only = entries(run(StructureConfig(**cfg, tradeDirection=TradeDirection.SHORT_ONLY), zigzag(SCENAR)))
    assert [e.direction for e in long_only.values()] == [Direction.LONG]
    assert [e.direction for e in short_only.values()] == [Direction.SHORT]


def test_obchodne_okno_obmedzi_len_vstupy_nie_strukturu():
    bars = zigzag(SCENAR)
    hodina = datetime.fromtimestamp(bars[CHOCH_DOWN].time / 1000, tz=timezone.utc).hour
    cfg = dict(BASE, entryMode=EntryMode.CHOCH, useSession=True)
    mimo = run(StructureConfig(**cfg, sessionStartH=(hodina + 2) % 24, sessionEndH=(hodina + 3) % 24), bars)
    vnutri = run(StructureConfig(**cfg, sessionStartH=hodina, sessionEndH=(hodina + 1) % 24), bars)
    assert CHOCH_DOWN not in entries(mimo) and CHOCH_DOWN in entries(vnutri)
    assert events(mimo) == events(vnutri), "štruktúra sa počíta stále, okno obmedzuje len vstup"


# --------------------------------------------------------------------------- #
# 5. stop loss
# --------------------------------------------------------------------------- #


def test_stop_je_za_poslednym_potvrdenym_swingom_plus_rezerva():
    outs = run(StructureConfig(**BASE, entryMode=EntryMode.CHOCH), zigzag(SCENAR))
    plan = entries(outs)[CHOCH_DOWN].plan
    assert plan.direction is Direction.SHORT
    # posledný potvrdený swing high je 120 (idx 17, potvrdený na idx 19)
    assert plan.stop_loss > 120.0, "stop musí byť ZA swingom, nie na ňom"
    assert plan.stop_loss - 120.0 < 5.0, "rezerva je 0,1 ATR, nie nový obchod"


def test_pri_sweep_vstupe_ide_stop_za_extrem_signalneho_baru():
    """Swing v protismere je pri sweepe už prekonaný — stop za ním by ležal na zlej
    strane vstupu a plán by bol nezmysel."""
    bars = zigzag(SCENAR)
    outs = run(StructureConfig(**BASE, entryMode=EntryMode.SWEEP), bars)
    plan = entries(outs)[CHOCH_DOWN].plan
    signal = bars[CHOCH_DOWN]
    assert plan.direction is Direction.LONG and plan.entry == signal.close
    assert plan.stop_loss < signal.low <= plan.entry
    assert plan.sl_distance > 0


def test_slmode_atr_pocita_stop_z_atr_a_neriesi_swingy():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.CHOCH, slMode=SlMode.ATR, slAtrMult=2.0)
    plan = entries(run(cfg, zigzag(SCENAR)))[CHOCH_DOWN].plan
    assert plan.stop_loss > plan.entry and plan.sl_distance == pytest.approx(plan.stop_loss - plan.entry)
    assert plan.sl_distance < 120.0 - plan.entry, "ATR stop je bližšie než swing na 120"


def test_take_profit_je_nasobok_rizika_pri_exitmode_rr():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, rrRatio=3.0)
    plan = entries(run(cfg, zigzag(SCENAR)))[CHOCH_DOWN].plan
    assert plan.take_profit - plan.entry == pytest.approx(plan.sl_distance * 3.0, rel=1e-6)


# --------------------------------------------------------------------------- #
# 6. kresby s plánom obchodu
# --------------------------------------------------------------------------- #


def test_boxy_nesu_plan_obchodu_a_paruju_sa_casom_baru_signalu():
    bars = zigzag(SCENAR)
    outs = run(StructureConfig(**BASE, entryMode=EntryMode.SWEEP), bars)
    plan = entries(outs)[CHOCH_DOWN].plan
    boxy = {d.kind: d for d in outs[CHOCH_DOWN].drawings
            if getattr(d, "kind", None) in (DrawKind.TP_BOX, DrawKind.SL_BOX)}
    assert set(boxy) == {DrawKind.TP_BOX, DrawKind.SL_BOX}
    for box in boxy.values():
        assert box.x1_ms == bars[CHOCH_DOWN].time and box.x2_ms > box.x1_ms
        assert box.y2 <= plan.entry <= box.y1
    assert boxy[DrawKind.TP_BOX].y1 == plan.take_profit
    assert boxy[DrawKind.SL_BOX].y2 == plan.stop_loss


def test_v_rezime_structure_sa_tp_box_nekresli():
    """Obchod tam pevný cieľ nemá; nakreslený backstop by analytike nahlásil
    plánovaný RR, ktorý neexistuje."""
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, exitMode=ExitMode.STRUCTURE)
    outs = run(cfg, zigzag(SCENAR))
    kinds = {getattr(d, "kind", None) for d in outs[CHOCH_DOWN].drawings}
    assert DrawKind.SL_BOX in kinds and DrawKind.TP_BOX not in kinds


def test_uroven_konci_na_bare_ktory_ju_prerazil():
    outs = run(StructureConfig(**BASE), zigzag(SCENAR))
    from tradebot.core.drawing import DrawUpdate

    updaty = [d for d in outs[BOS_UP].drawings if isinstance(d, DrawUpdate)]
    assert [u.field for u in updaty] == ["x2_ms"]
    assert updaty[0].value == zigzag(SCENAR)[BOS_UP].time


def test_vypnuta_vizualizacia_nekresli_strukturu_ale_obchody_ano():
    outs = run(StructureConfig(**BASE, entryMode=EntryMode.CHOCH, showStructure=False), zigzag(SCENAR))
    struktura = {DrawKind.ST_SWING_HIGH, DrawKind.ST_SWING_LOW, DrawKind.ST_LEVEL,
                 DrawKind.ST_BOS, DrawKind.ST_CHOCH}
    assert not [d for o in outs for d in o.drawings if getattr(d, "kind", None) in struktura]
    assert [d for d in outs[CHOCH_DOWN].drawings if getattr(d, "kind", None) is DrawKind.SL_BOX]


# --------------------------------------------------------------------------- #
# 7. nová rodina výstupov: štruktúra a čas
# --------------------------------------------------------------------------- #


def _drzana_pozicia(od: int, smer: float):
    """Kontext, v ktorom obchod od baru `od` beží — ako keby ho adaptér naozaj otvoril."""
    def ctx(i: int) -> MarketContext:
        drzi = i > od
        return MarketContext(in_trade_window=True, position_size=smer if drzi else 0.0,
                             open_order_ids=frozenset({f"struct:{od}"}) if drzi else frozenset())
    return ctx


def test_exitmode_structure_zavrie_obchod_na_dalsej_udalosti_v_smere_obchodu():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, exitMode=ExitMode.STRUCTURE)
    outs = run(cfg, zigzag(SCENAR), ctx_for=_drzana_pozicia(CHOCH_DOWN, +1.0))
    zavrete = [i for i, o in enumerate(outs) if o.close_session]
    assert zavrete == [CHOCH_UP], "long sa zavrie až na udalosti NAHOR, nie na ktorejkoľvek"
    close_orders = [o for o in outs[CHOCH_UP].orders if o.action is OrderAction.CLOSE]
    assert [o.order_id for o in close_orders] == [f"struct:{CHOCH_DOWN}"]


def test_exitmode_rr_na_strukturnej_udalosti_nezatvara():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, exitMode=ExitMode.RR)
    outs = run(cfg, zigzag(SCENAR), ctx_for=_drzana_pozicia(CHOCH_DOWN, +1.0))
    assert not [o for o in outs if o.close_session]


def test_maxbars_zavrie_obchod_po_danom_pocte_barov_od_signalu():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, maxBars=3)
    outs = run(cfg, zigzag(SCENAR), ctx_for=_drzana_pozicia(CHOCH_DOWN, +1.0))
    zavrete = [i for i, o in enumerate(outs) if o.close_session]
    assert zavrete and zavrete[0] == CHOCH_DOWN + 3
    assert StructureConfig(**BASE).maxBars == 0  # default: bez časového limitu


def test_maxbars_nula_je_bez_limitu():
    cfg = StructureConfig(**BASE, entryMode=EntryMode.SWEEP, maxBars=0)
    outs = run(cfg, zigzag(SCENAR), ctx_for=_drzana_pozicia(CHOCH_DOWN, +1.0))
    assert not [o for o in outs if o.close_session]


def test_dalsi_vstup_az_ked_je_engine_flat():
    """Kým beží obchod, nová udalosť nový order neurobí — pozíciu pozná adaptér."""
    cfg = StructureConfig(**BASE, entryMode=EntryMode.CHOCH)
    outs = run(cfg, zigzag(SCENAR), ctx_for=_drzana_pozicia(CHOCH_DOWN, -1.0))
    assert list(entries(outs)) == [CHOCH_DOWN]


# --------------------------------------------------------------------------- #
# 8. generický runner
# --------------------------------------------------------------------------- #


def test_genericky_runner_prehra_strategiu_bez_htf():
    runner = EngineRunner(StructureConfig(**BASE, entryMode=EntryMode.SWEEP), INST, 5)
    assert runner.spec.key == "structure" and runner.htf is None
    rows = [runner.process(bar, runner.window_for(bar.time)) for bar in zigzag(SCENAR)]
    signal = rows[CHOCH_DOWN]
    assert signal.enter_long == 1 and signal.in_trade_window is True
    assert signal.stop_loss < signal.entry < signal.take_profit
    assert runner.signal_at(T0 + CHOCH_DOWN * MIN5) is signal
