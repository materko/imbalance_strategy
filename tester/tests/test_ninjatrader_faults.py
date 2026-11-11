"""Poruchy brokera proti skutočnému `LiveInstance` adaptéra NinjaTradera (`tester.faultsim`).

Parita bar po bare overuje signály; tu sa overuje exekúcia: po odmietnutom orderi, stratenej správe,
výplni po zrušení, výpadku spojenia či páde platformy nesmie u brokera ostať pozícia bez stopu, order
bez pozície ani pozícia, o ktorej inštancia nevie. Model brokera: docs/SIMULATOR_PORUCH.md.
"""
from __future__ import annotations

import shutil
import sys

import pytest

from tester import faultsim

#: Limitný long 1 ks @100, SL 95, TP 110 na prvom živom bare.
ENTRY = {"bar": 1, "action": "entry", "id": "L1", "type": "limit", "entry": 100, "sl": 95, "tp": 110}
#: Bar, na ktorom engine vstup pošle, a jeho výplň.
OPEN = [{"do": "bar"}, {"do": "fill", "order": "L1"}]


@pytest.fixture(scope="module", autouse=True)
def _sim():
    if sys.platform != "win32" and shutil.which("mono") is None:
        pytest.skip("simulátor porúch potrebuje .NET Framework alebo Mono")
    try:
        faultsim.ensure_sim()
    except faultsim.BuildError as exc:
        pytest.skip(f"simulátor porúch sa nepreložil: {exc}")


def play(engine: list[dict], steps: list[dict]) -> dict:
    out = faultsim.run({"engine": engine, "steps": steps})
    assert out["error"] == "", out["error"]
    return out


def rule(on: str, match: str, then: str, times: int = 1) -> dict:
    return {"do": "rule", "on": on, "match": match, "then": then, "times": times}


def wait(seconds: int) -> dict:
    return {"do": "advance", "s": seconds}


def working(step: dict) -> list[str]:
    return sorted(w["name"] for w in step["working"])


def assert_clean(step: dict) -> None:
    """Svet sedí: žiadna pozícia bez stopu, žiadny order bez pozície, inštancia vie, čo drží, nič sa neruší."""
    assert not step["naked"], step
    assert not step["orphans"], step
    assert not step["unknown"], step
    assert step["dying"] == 0, step


def assert_flat(step: dict) -> None:
    assert_clean(step)
    assert step["position"] == 0 and step["working"] == [] and step["tracked"] == [], step


def logged(out: dict, text: str) -> bool:
    return any(text in line for line in out["log"])


# --------------------------------------------------------------------------- #
# bez poruchy: vstup, OCO výstupy, výplň TP
# --------------------------------------------------------------------------- #


def test_vstup_dostane_oco_vystupy_a_tp_poziciu_zavrie():
    out = play([ENTRY], [*OPEN, {"do": "bar", "c": 104}, {"do": "fill", "order": "L1:tp"}, wait(3)])
    opened = out["trace"][2]
    assert opened["position"] == 1 and working(opened) == ["L1:sl", "L1:tp"]
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])
    assert out["seen_position"] == [0.0, 1.0]   # engine vidí vlastnú pozíciu hneď na ďalšom bare


# --------------------------------------------------------------------------- #
# zrušenie vstupu proti jeho výplni (audit M-LIVE-1, M-LIVE-2)
# --------------------------------------------------------------------------- #


def test_vypln_po_zruseni_sa_prevezme_a_zavrie_trhom():
    out = play([ENTRY, {"bar": 2, "action": "cancel", "id": "L1"}],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, {"do": "fill", "order": "L1"}, wait(3)])
    assert out["trace"][3]["dying"] == 1 and out["trace"][3]["tracked"] == []   # engine má id voľné, broker order ešte drží
    assert faultsim.naked_steps(out) == []
    assert logged(out, "az po zruseni - poziciu zatvaram trhom")
    assert_flat(out["trace"][-1])


def test_stratene_zrusenie_sa_posle_znova():
    out = play([ENTRY, {"bar": 2, "action": "cancel", "id": "L1"}],
               [rule("cancel", "L1", "ignore"), {"do": "bar"}, {"do": "bar"}, wait(7)])
    assert out["requests"].count("cancel L1") == 1 and "cancel L1 -> ignore" in out["requests"]
    assert_flat(out["trace"][-1])


def test_odmietnute_zrusenie_nie_je_koniec_orderu():
    """Broker zrušenie odmietol a order stojí ďalej: inštancia ho nesmie prestať strážiť — jeho výplň by bola
    pozícia bez SL, o ktorej nikto nevie."""
    out = play([ENTRY, {"bar": 2, "action": "cancel", "id": "L1"}],
               [rule("cancel", "L1", "reject"), {"do": "bar"}, {"do": "bar"}, wait(2),
                rule("cancel", "L1", "hold"), wait(5), {"do": "fill", "order": "L1"}, wait(3)])
    assert out["trace"][4]["dying"] == 1 and working(out["trace"][4]) == ["L1"]
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


def test_vypln_bez_spravy_o_exekucii_sa_prevezme_z_orderu():
    out = play([ENTRY, {"bar": 2, "action": "cancel", "id": "L1"}],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, {"do": "fill", "order": "L1", "lose_exec": True}, wait(7)])
    assert out["trace"][4]["position"] == 1 and out["trace"][4]["unknown"]   # exekúcia neprišla: pozícia tu je, inštancia čaká
    assert_flat(out["trace"][-1])


def test_novy_vstup_s_tym_istym_id_pocka_na_zrusenie_stareho():
    out = play([ENTRY, dict(ENTRY, bar=2, entry=99)],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, wait(2), {"do": "release"}, wait(2)])
    for step in out["trace"]:
        assert working(step).count("L1") <= 1, step   # dva ordery s jedným id nesmú stáť naraz
    waiting = out["trace"][4]
    assert waiting["working"][0]["price"] == 100.0 and waiting["tracked"][0]["parked"]
    last = out["trace"][-1]
    assert last["working"][0]["price"] == 99.0 and not last["tracked"][0]["parked"]
    assert_clean(last)


def test_stary_vstup_sa_vyplni_pocas_nahrady_a_novy_ide_az_potom():
    out = play([ENTRY, dict(ENTRY, bar=2, entry=99)],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, {"do": "fill", "order": "L1"}, wait(3),
                {"do": "release"}, wait(3)])
    assert faultsim.naked_steps(out) == []
    last = out["trace"][-1]
    assert last["position"] == 0 and working(last) == ["L1"] and last["working"][0]["price"] == 99.0
    assert_clean(last)


def test_koniec_seansy_zavrie_aj_vstup_vyplneny_po_zruseni():
    out = play([ENTRY, {"bar": 2, "action": "close_session"}],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, {"do": "fill", "order": "L1"}, wait(3)])
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


def test_flatten_z_control_zavrie_poziciu_aj_cakajuci_vstup():
    out = play([ENTRY, dict(ENTRY, bar=2, id="L2", entry=98)],
               [*OPEN, {"do": "bar"}, {"do": "control", "mode": "flatten"}, wait(5)])
    assert out["trace"][3]["tracked"][1]["parked"]   # druhý vstup čaká, kým beží pozícia
    assert_flat(out["trace"][-1])


def test_flatten_a_vypln_cakajuceho_vstupu_po_zruseni():
    out = play([ENTRY], [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "control", "mode": "flatten"}, wait(3),
                         {"do": "fill", "order": "L1"}, wait(3)])
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


# --------------------------------------------------------------------------- #
# vstup, ktorý broker nevzal
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("then", ["reject", "throw"])
def test_odmietnuty_alebo_neodoslany_vstup_sa_nesleduje(then):
    out = play([ENTRY], [rule("submit", "L1", then), {"do": "bar"}, wait(2)])
    assert_flat(out["trace"][-1])
    assert logged(out, "ERROR: vstup L1")


def test_market_vstup_bez_vyplne_sa_pocita_ako_pozicia():
    """Engine nesmie poslať ďalší market vstup len preto, že výplň prvého ešte neprišla."""
    out = play([dict(ENTRY, type="market"), dict(ENTRY, bar=2, id="L2", type="market")],
               [rule("submit", "L1", "hold"), {"do": "bar"}, {"do": "bar"}, {"do": "fill", "order": "L1"}])
    assert out["seen_position"] == [0.0, 1.0]
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"]
    assert [t["parked"] for t in last["tracked"]] == [False, True]
    assert_clean(last)


# --------------------------------------------------------------------------- #
# pozícia bez stopu (audit N-LIVE-1, N-LIVE-11)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("then", ["reject", "throw"])
def test_sl_ktory_broker_nevzal_sa_polozi_znova(then):
    out = play([ENTRY], [rule("submit", "L1:sl", then), *OPEN, wait(4)])
    assert out["trace"][3]["naked"]   # okno bez stopu existuje - strážca ho zavrie do pár sekúnd
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"]
    assert_clean(last)


def test_sl_ktory_broker_neberie_vobec_konci_trhovym_vystupom():
    out = play([ENTRY], [rule("submit", "L1:sl", "reject", times=99), *OPEN, wait(20)])
    assert logged(out, "zatvaram trhom")
    assert_flat(out["trace"][-1])


def test_sl_zruseny_mimo_strategie_sa_polozi_znova():
    out = play([ENTRY], [*OPEN, {"do": "cancel_outside", "order": "L1:sl"}, wait(4)])
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"]
    assert_clean(last)


def test_odmietnuty_posun_trailingu_nezavrie_poziciu_a_skusi_sa_znova():
    out = play([dict(ENTRY, trail_act=2, trail_off=1)],
               [*OPEN, rule("change", "L1:sl", "reject"), {"do": "bar", "h": 104, "c": 104}, {"do": "bar", "h": 105, "c": 105}])
    stops = [next(w["price"] for w in step["working"] if w["name"] == "L1:sl") for step in out["trace"][2:] if step["working"]]
    assert stops[0] == 95.0 and stops[-2] == 95.0 and stops[-1] == 104.0   # prvý posun odmietnutý, druhý prešiel
    assert faultsim.naked_steps(out) == []
    assert out["trace"][-1]["position"] == 1


# --------------------------------------------------------------------------- #
# zatváranie trhom
# --------------------------------------------------------------------------- #


def test_odmietnuty_trhovy_vystup_ide_znova():
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("submit", "L1:tb_close", "reject"), *OPEN, {"do": "bar"}, wait(5)])
    assert_flat(out["trace"][-1])


def test_po_troch_odmietnutiach_stoja_medzi_pokusmi_sl_tp_znova():
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("submit", "L1:tb_close", "reject", times=3), *OPEN, {"do": "bar"}, wait(7), wait(13)])
    protected = out["trace"][5]
    assert protected["position"] == 1 and working(protected) == ["L1:sl", "L1:tp"] and not protected["naked"]
    assert_flat(out["trace"][-1])


def test_trhovy_vystup_po_nepotvrdenom_zruseni_nenecha_sl_tp_u_brokera():
    """Zrušenie SL/TP sa stratilo, po 10 s ide trhový výstup aj tak: SL/TP zavretej pozície nesmú u brokera ostať
    stáť — stop bez pozície by neskôr otvoril obchod, o ktorom nikto nevie."""
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("cancel", "L1:*", "ignore", times=4), *OPEN, {"do": "bar"}, wait(11), wait(6)])
    closed = out["trace"][5]
    assert closed["position"] == 0 and closed["dying"] == 2 and working(closed) == ["L1:sl", "L1:tp"]
    assert_flat(out["trace"][-1])


def test_vstup_hlasi_typ_orderu_a_ci_sa_sl_tp_poslali_brokerovi():
    out = play([ENTRY], [*OPEN, wait(1)])
    assert logged(out, "vstup L1 LONG Limit 100 vyplneny x1 @100 - SL 95 poslany brokerovi, TP 110 poslany brokerovi")


def test_sl_vyplneny_pocas_zatvarania_trhom_nema_co_zatvorit():
    """Engine chce zavrieť trhom, kým sa rušia SL/TP, broker vyplní SL — trhový výstup sa neposiela a hlási sa
    to ako „nemá čo zatvoriť“ (na MT5 to isté vracia broker ako 10036)."""
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("cancel", "L1:sl", "hold"), *OPEN, {"do": "bar"}, {"do": "fill", "order": "L1:sl"}, wait(5)])
    assert logged(out, "market close L1 (tb_close) nema co zatvorit - poziciu medzitym zavrel Stop loss @95")
    assert "submit L1:tb_close" not in " ".join(out["requests"])
    assert_flat(out["trace"][-1])


def test_vypln_osiroteneho_sl_sa_hned_zavrie():
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("cancel", "L1:*", "ignore", times=99), *OPEN, {"do": "bar"}, wait(15), {"do": "fill", "order": "L1:sl"}, wait(5)])
    assert logged(out, "vystup L1:sl uz zavretej pozicie sa vyplnil")
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


# --------------------------------------------------------------------------- #
# čiastočné výplne (audit M-LIVE-6)
# --------------------------------------------------------------------------- #


def test_dalsia_ciastocna_vypln_navysi_objem_vystupov():
    out = play([dict(ENTRY, qty=2)], [{"do": "bar"}, {"do": "fill", "order": "L1", "qty": 1}, {"do": "fill", "order": "L1", "qty": 1}])
    assert [w["qty"] for w in out["trace"][2]["working"] if ":" in w["name"]] == [1, 1]
    last = out["trace"][-1]
    assert last["position"] == 2 and [w["qty"] for w in last["working"]] == [2, 2]
    assert faultsim.naked_steps(out) == []


def test_po_zavreti_ciastocnej_pozicie_sa_zvysok_vstupu_zrusi():
    out = play([dict(ENTRY, qty=2)], [{"do": "bar"}, {"do": "fill", "order": "L1", "qty": 1}, {"do": "fill", "order": "L1:tp"}, wait(3)])
    assert_flat(out["trace"][-1])


def test_zvysok_vstupu_vyplneny_po_zavreti_pozicie_ide_von_trhom():
    out = play([dict(ENTRY, qty=2)],
               [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "fill", "order": "L1", "qty": 1}, {"do": "fill", "order": "L1:tp"},
                {"do": "fill", "order": "L1"}, wait(3)])
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


# --------------------------------------------------------------------------- #
# spojenie a pozícia účtu (audit N-LIVE-12)
# --------------------------------------------------------------------------- #


def test_vypadok_spojenia_nie_je_zavretie_mimo_strategie():
    """Účet po výpadku chvíľu pozície neukazuje: inštancia nesmie zapísať výstup a zrušiť SL/TP."""
    out = play([ENTRY], [*OPEN, wait(45), {"do": "disconnect"}, wait(20), {"do": "connect", "positions": False}, wait(20),
                         {"do": "positions"}, wait(30)])
    assert not logged(out, "zavreta mimo strategie")
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"] and last["tracked"][0]["open"] == 1
    assert_clean(last)


def test_zavretie_mimo_strategie_stiahne_sl_tp():
    out = play([ENTRY], [*OPEN, wait(45), {"do": "foreign", "side": "sell"}, wait(10)])
    assert logged(out, "zavreta mimo strategie")
    assert_flat(out["trace"][-1])


# --------------------------------------------------------------------------- #
# reštart s otvorenými obchodmi
# --------------------------------------------------------------------------- #


def test_po_pade_sa_pozicia_prevezme_a_engine_ju_zavrie():
    out = play([ENTRY, {"bar": 3, "action": "close", "id": "L1"}],
               [*OPEN, {"do": "crash"}, {"do": "start"}, {"do": "bar"}, {"do": "bar"}, wait(3)])
    restored = out["trace"][4]
    assert restored["tracked"][0]["open"] == 1 and working(restored) == ["L1:sl", "L1:tp"]
    assert faultsim.naked_steps(out) == []
    assert_flat(out["trace"][-1])


def test_vstup_vyplneny_pocas_vypadku_dostane_po_starte_vystupy():
    out = play([ENTRY], [{"do": "bar"}, wait(2), {"do": "crash"}, {"do": "fill", "order": "L1"}, {"do": "start"}, wait(5)])
    assert out["trace"][4]["naked"]   # kým platforma nebeží, pozíciu nemá kto strážiť
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"]
    assert_clean(last)


def test_vystup_vyplneny_pocas_vypadku_sa_po_starte_zapise():
    out = play([ENTRY], [*OPEN, wait(2), {"do": "crash"}, {"do": "fill", "order": "L1:sl"}, {"do": "start"}, wait(5)])
    assert_flat(out["trace"][-1])


def test_zatvaranie_prerusene_padom_sa_po_starte_dokonci():
    """Engine pozíciu zavrel, zrušenie SL/TP sa nepotvrdilo a platforma spadla: nový beh nesmie pozíciu prevziať
    ako bežnú (engine o nej po predhistórii nevie a znova ju nezavrie) — zatváranie dokončí (audit M-LIVE-9)."""
    out = play([ENTRY, {"bar": 2, "action": "close", "id": "L1"}],
               [rule("cancel", "L1:*", "ignore", times=2), *OPEN, {"do": "bar"}, wait(2), {"do": "crash"}, {"do": "start"}, wait(5)])
    assert out["trace"][5]["position"] == 1   # pred pádom trhový výstup ešte neodišiel
    assert logged(out, "zatvaranie pokracuje")
    assert_flat(out["trace"][-1])


def test_mrtvy_rad_barov_pri_pripojenom_ucte_restartuje_instanciu():
    """Účet je pripojený, ale bary 10 minút nechodia (mŕtvy BarsRequest po reconnecte): inštancia si vyžiada reštart,
    pozícia a jej SL/TP ostávajú u brokera a nový beh ich prevezme (zvyšok auditu N-LIVE-7)."""
    out = play([ENTRY], [*OPEN, wait(900), {"do": "stop", "reason": "feed_dead"}, {"do": "start"}, wait(5)])
    assert logged(out, "restartujem instanciu")
    assert out["trace"][3]["position"] == 1 and working(out["trace"][3]) == ["L1:sl", "L1:tp"]
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"] and last["tracked"][0]["open"] == 1
    assert_clean(last)


def test_vstup_vyplneny_po_zastaveni_instancie_sa_po_starte_prevezme():
    """Zastavenie ruší čakajúce vstupy a na potvrdenie nečaká; výplň, ktorá zrušenie predbehne, prevezme až ďalší
    štart (do tej doby pozíciu nemá kto strážiť — preto AddOn inštanciu po páde spúšťa znova)."""
    out = play([ENTRY], [rule("cancel", "L1", "hold"), {"do": "bar"}, {"do": "stop"}, {"do": "fill", "order": "L1"},
                         {"do": "start"}, wait(5)])
    last = out["trace"][-1]
    assert last["position"] == 1 and working(last) == ["L1:sl", "L1:tp"] and not last["naked"] and not last["unknown"]
