"""Základná analytika stratégie — a hlavne to, čo z čísel smie a nesmie vyvodiť.

Batéria sama nič nepočíta: skladá hotové merania (charakter, skupiny, náhoda, Monte
Carlo) do jedného dokumentu. Rizikom je preto **verdikt** — veta „v čom je dobrá" alebo
„kde má chyby", ktorá by sa dostala do dokumentu bez čísla za sebou, alebo naopak
chýbala, keď na ňu čísla ukazujú. Presne to tu testujeme; matematiku strážia testy
jednotlivých modulov.
"""

from __future__ import annotations

import pytest

from tester import checkup as ck
from tradebot.strategies import STRATEGIES


def okno(timerange: str, *, pnl=1.0, trades=40, be=0.08, dd=5.0, status="done",
         run_id="20260101-000000-aaaaaa") -> dict:
    """Záznam behu tak, ako ho ukladá `RunStore` — len polia, ktoré batéria číta."""
    return {
        "id": run_id, "status": status,
        "settings": {"timerange": timerange, "strategy": "ibs"},
        "result": {"trades": trades, "pnl_pct": pnl, "break_even_pct": be,
                   "max_drawdown_pct": dd, "winrate": 35.0, "profit_factor": 1.2},
    }


def bootstrap(*, p_above_fee=0.97, dd_median=10.0, dd_p95=18.0, p_ruin=0.0) -> dict:
    """Monte Carlo v tvare, aký vracia `montecarlo.analyze()` — len čítané polia."""
    return {
        "block": 10, "iterations": 10_000, "ci": 90.0,
        "break_even": {"observed": 0.09, "median": 0.089, "lo": 0.04, "hi": 0.14,
                       "p_above_fee": p_above_fee},
        "account": {"start": 10_000.0, "p_ruin": p_ruin, "advice": None,
                    "drawdown_pct": {"median": dd_median, "p95": dd_p95, "max": dd_p95 * 2},
                    "losing_streak": {"median": 9.0, "p95": 13.0}},
    }


def nahoda(sigma: float) -> dict:
    """Výsledok testu proti náhode v tvare, aký vracia `nulltest.Result.to_dict()`."""
    return {"sigma": sigma, "observed": 0.09, "mean": 0.0, "sd": 0.03, "percentile": 99.0,
            "null_note": "vstupy kedykoľvek v okne", "verdict": f"{sigma} sigma"}


def riadky(*zaznamy: dict) -> list[dict]:
    """Behy ako riadky tabuľky — v tomto tvare ich má batéria vo `windows`."""
    return ck.window_rows(list(zaznamy))


def report(**zmeny) -> dict:
    """Hotová batéria s rozumnými číslami; test si prepíše len to, čo skúma."""
    zaklad = {
        "strategy": "ibs", "title": "IBS", "pair": "BTC/USDT:USDT", "timeframe": "3m",
        "engine": "freqtrade", "profile": "", "fee_pct": 0.05, "account": 10000.0,
        "windows": riadky(*(okno(w) for w in ck.REFERENCE_WINDOWS)),
        "years_positive": 5, "years_done": 5, "trades": 200, "break_even_pct": 0.09,
        "character": {"title": "Prerazenie (breakout)", "confidence": "dobrá",
                      "exits": {"stop_loss": 42.0}},
        "analytics": {"headline": "Najhoršia skupina je 'do 0,3 %'.", "tunable": ["minSlDistance"],
                      "splits": [{"title": "Vzdialenosť stopu", "param": "minSlDistance",
                                  "best_impact": 0.04,
                                  "buckets": [{"label": "do 0,3 %", "trades": 50, "share_pct": 25.0,
                                               "winrate": 20.0, "break_even_pct": -0.04,
                                               "without_pct": 0.13, "impact": 0.04}]}]},
        "null": {"anytime": nahoda(3.0), "session": nahoda(2.8)},
        "montecarlo": bootstrap(),
    }
    zaklad.update(zmeny)
    return zaklad


def texty(vety: list[str]) -> str:
    return " | ".join(vety)


# --------------------------------------------------------------------------- #
# okná: znamienko po rokoch, nie súčet
# --------------------------------------------------------------------------- #


def test_vsetky_okna_v_pluse_su_silna_stranka():
    silne, slabe = ck.verdicts(report())
    assert "5 z 5" in texty(silne)
    assert "v strate" not in texty(slabe)


def test_stratove_okno_sa_vymenuje_menom():
    """Súčet môže byť kladný a stratégia napriek tomu dva roky prerábala — to musí byť vidieť."""
    okna = [okno(w) for w in ck.REFERENCE_WINDOWS]
    okna[1]["result"]["pnl_pct"] = -4.0
    silne, slabe = ck.verdicts(report(windows=riadky(*okna), years_positive=4, years_done=5))
    assert ck.REFERENCE_WINDOWS[1] in texty(slabe)
    assert "5 z 5" not in texty(silne)


def test_nedobehnute_okno_je_chyba_nie_ticho():
    okna = [okno(w) for w in ck.REFERENCE_WINDOWS]
    okna[0] = okno(ck.REFERENCE_WINDOWS[0], status="failed")
    _, slabe = ck.verdicts(report(windows=riadky(*okna), years_positive=4, years_done=4))
    assert "nedobehlo" in texty(slabe)


# --------------------------------------------------------------------------- #
# edge oproti poplatku
# --------------------------------------------------------------------------- #


def test_break_even_pod_poplatkom_je_chyba_aj_ked_pnl_svieti():
    _, slabe = ck.verdicts(report(break_even_pct=0.03))
    assert "pod poplatkom" in texty(slabe)


def test_maly_pocet_obchodov_znehodnoti_vsetko_ostatne():
    silne, slabe = ck.verdicts(report(trades=12))
    assert "anekdota" in texty(slabe)
    assert "na štatistiku dosť" not in texty(silne)


def test_edge_len_v_case_seansy_sa_povie_nahlas():
    """Keď je stratégia lepšia než náhoda kedykoľvek, ale nie než náhoda v tých istých
    hodinách, jej edge je v tom, KEDY obchoduje — a to sa dá mať aj bez nej."""
    _, slabe = ck.verdicts(report(null={"anytime": nahoda(3.0), "session": nahoda(0.5)}))
    assert "KEDY obchoduje" in texty(slabe)


def test_neodlisitelna_od_nahody_nie_je_silna_stranka():
    silne, slabe = ck.verdicts(report(null={"anytime": nahoda(0.2), "session": nahoda(0.1)}))
    assert "odlíšiteľná od náhody" not in texty(silne)
    assert "sigma" in texty(slabe)


def test_co_sa_nedalo_zmerat_sa_nehodnoti():
    """Chýbajúca hodnota nie je ani plus, ani mínus — inak by dokument tvrdil viac, než vie."""
    silne, slabe = ck.verdicts(report(null={}, montecarlo=None, character={}, analytics={}))
    assert "sigma" not in texty(silne) + texty(slabe)
    assert "drawdown" not in texty(silne) + texty(slabe)


# --------------------------------------------------------------------------- #
# účet a skupiny obchodov
# --------------------------------------------------------------------------- #


def test_hlboky_drawdown_je_chyba_aj_pri_ziskovej_strategii():
    silne, slabe = ck.verdicts(report(montecarlo=bootstrap(p_above_fee=0.99, dd_median=15.0,
                                                          dd_p95=38.0)))
    assert "drawdown" in texty(slabe) and "38" in texty(slabe)
    assert "drawdown drží" not in texty(silne)


def test_vystup_na_case_je_nastavenie_seansy_nie_vlastnost_vstupu():
    char = {"title": "Prerazenie (breakout)", "confidence": "dobrá",
            "exits": {"session_end": 24.0, "stop_loss": 40.0}}
    _, slabe = ck.verdicts(report(character=char))
    assert "na čase" in texty(slabe)


def test_ked_nic_nevycnieva_nie_je_co_filtrovat():
    splits = [{"title": "Smer", "param": "tradeDirection", "best_impact": 0.001,
               "buckets": [{"label": "long", "trades": 100, "share_pct": 50.0}]}]
    silne, _ = ck.verdicts(report(analytics={"splits": splits}))
    assert "niet čo filtrovať" in texty(silne)


def test_najhorsia_skupina_nesie_aj_parameter_ktory_ju_riadi():
    _, slabe = ck.verdicts(report())
    assert "minSlDistance" in texty(slabe)


# --------------------------------------------------------------------------- #
# výstupy
# --------------------------------------------------------------------------- #


def test_dokument_ma_vsetky_sekcie_a_prikaz_na_zopakovanie():
    md = ck.markdown(report(strengths=["dobrá vec"], weaknesses=["zlá vec"]),
                     command="python -m tester.webapp.cli checkup --strategy ibs")
    for nadpis in ("# Základná analytika", "## V čom je dobrá", "## Kde má chyby",
                   "## Päť referenčných okien", "## Charakter", "## Čo tu nie je"):
        assert nadpis in md
    assert "cli checkup --strategy ibs" in md
    assert "dobrá vec" in md and "zlá vec" in md


def test_dlhe_rozdelenie_sa_v_dokumente_skrati_na_okraje():
    """22 mesiacov v tabuľke nikto nečíta; zaujímavé sú najhoršie a najlepšie skupiny."""
    skupiny = [{"label": f"m{i}", "trades": 100, "share_pct": 4.5, "winrate": 30.0,
                "break_even_pct": i / 1000, "without_pct": 0.0, "impact": 0.0}
               for i in range(22)]
    md = ck.markdown(report(analytics={"headline": "x", "splits": [
        {"title": "Mesiac", "param": None, "best_impact": 0.02, "buckets": skupiny}]}))
    assert "| … |" in md
    assert "| m0 |" in md and "| m21 |" in md and "| m10 |" not in md


def test_tabulka_okien_uvedie_id_behu_nech_sa_da_otvorit():
    md = ck.markdown(report(strengths=[], weaknesses=[]))
    assert "20260101-000000-aaaaaa" in md


def test_bez_obchodov_je_dokument_o_tom_ze_nie_su_obchody():
    vysledok = ck.measure([okno(ck.REFERENCE_WINDOWS[0], trades=0)], [],
                          strategy="ibs", pair="BTC/USDT:USDT", timeframe="3m")
    assert vysledok["trades"] == 0 and vysledok["strengths"] == []
    assert "Žiadne obchody" in texty(vysledok["weaknesses"])
    assert vysledok["character"] is None


def test_dokument_patri_k_strategii_nie_do_spolocneho_adresara():
    cesta = ck.doc_path("demo_breakout")
    assert cesta.name == ck.DOC_NAME
    assert cesta.parent.parent.name == "demo_breakout"


# --------------------------------------------------------------------------- #
# posudok od AI
# --------------------------------------------------------------------------- #


def test_bez_posudku_dokument_ziada_odpovede_na_sest_otazok():
    md = ck.markdown(report(strengths=[], weaknesses=[]))
    assert "## Posudok (AI)" in md and ck.POSUDOK_PLACEHOLDER in md
    for otazka in ck.POSUDOK_OTAZKY:
        assert otazka.split("**")[1] in md


def test_napisany_posudok_prezije_prepocet():
    """Čísla sa prepočítavajú, posudok sa nepíše znova — musí prejsť z predošlej verzie."""
    prvy = ck.markdown(report(strengths=[], weaknesses=[]))
    hotovy = prvy.replace(ck.POSUDOK_PLACEHOLDER, "Na krypto sa hodí, na forex nie.")
    telo, odtlacok = ck.extract_posudok(hotovy)
    assert telo == "Na krypto sa hodí, na forex nie."

    druhy = ck.markdown(report(strengths=[], weaknesses=[]), posudok=telo, posudok_stamp=odtlacok)
    assert "Na krypto sa hodí, na forex nie." in druhy
    assert "starší než čísla" not in druhy


def test_posudok_k_inym_cislam_sa_oznaci_za_stary():
    """Posudok je text o konkrétnej vzorke; po prepočte na iných dátach to musí byť vidieť."""
    md = ck.markdown(report(trades=999), posudok="Toto platilo vlani.", posudok_stamp="deadbeef")
    assert "starší než čísla" in md and "Toto platilo vlani." in md


def test_placeholder_sa_neberie_ako_napisany_posudok():
    """Inak by dokument tvrdil, že posudok má, hoci v ňom je len výzva ho napísať."""
    telo, odtlacok = ck.extract_posudok(ck.markdown(report(strengths=[], weaknesses=[])))
    assert telo == "" and odtlacok == ""


def test_odtlacok_sa_meni_s_cislami_nie_s_textom():
    zaklad = report()
    assert ck.fingerprint(zaklad) == ck.fingerprint(report(strengths=["ine vety"]))
    assert ck.fingerprint(zaklad) != ck.fingerprint(report(trades=201))


# --------------------------------------------------------------------------- #
# každá stratégia v registry
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", sorted(STRATEGIES))
def test_kazda_strategia_ma_analytiku_a_posudok(key):
    """Stratégia bez odpovede na otázku „čo to vlastne je" nie je hotová (docs/STRATEGIE.md).

    Kód, ktorý beží, hovorí len to, že beží. Preto je dokument s analytikou a posudkom
    súčasťou balíka stratégie a jeho absencia je chyba tu, nie prekvapenie o pol roka.
    """
    cesta = ck.doc_path(key)
    assert cesta.exists(), (f"{key}: chýba {cesta} — spusti "
                            f"`python -m tester.webapp.cli checkup --strategy {key} …`")
    telo, _ = ck.extract_posudok(cesta.read_text(encoding="utf-8"))
    assert telo.strip(), (f"{key}: analytika je bez posudku od AI. Prečítaj {cesta.name}, "
                          "odpovedz na šesť otázok a zapíš odpoveď medzi značky POSUDOK.")
