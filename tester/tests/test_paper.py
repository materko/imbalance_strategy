"""Meranie, ktoré sa napíše samo — testy nad umelou históriou.

Nejde o to, či sú čísla pekné, ale či dokument **nezamlčí**, čo sa nespočítalo: sekcia,
na ktorú behy nestačili, musí skončiť v zozname „na čo behy nestačili“ a nesmie sa
dostať do tabuľky verdiktov, kde by vyzerala ako zistenie.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("numpy")

from tester import paper as pp

ZACIATOK = datetime(2024, 1, 1, tzinfo=timezone.utc)


def obchod(i: int, *, vyhra: bool = True) -> dict:
    cas = ZACIATOK + timedelta(hours=4 * i)
    close = 101.0 if vyhra else 99.0
    return {"open_date": cas.isoformat(), "close_date": (cas + timedelta(hours=2)).isoformat(),
            "open_rate": 100.0, "close_rate": close, "amount": 1.0, "is_short": False,
            "profit_abs": 1.0 if vyhra else -1.0, "exit_reason": "roi" if vyhra else "stop_loss"}


def beh(run_id: str, okno: str, *, pair: str = "TEST/USD", obchodov: int = 30,
        break_even: float = 0.1, note: str = "") -> dict:
    return {"id": run_id, "status": "done", "note": note,
            "settings": {"pair": pair, "timeframe": "3m", "timerange": okno,
                         "strategy": "ibs", "wallet": 10000.0, "fee": 0.0005},
            "result": {"trades": obchodov, "winrate": 40.0, "pnl_pct": 5.0,
                       "break_even_pct": break_even, "max_drawdown_pct": 8.0}}


class FakeStore:
    """Sklad, ktorý vracia to, čo mu dáme — bez diskov a bez sviečok."""

    def __init__(self, records, per_run=None):
        self._records = list(records)
        # Každý beh má vlastný úsek kalendára: rovnaké obchody v dvoch behoch by
        # `analytics.dedupe` správne zlial (prekrývajúce sa okná), a to tu netestujeme.
        self._trades = per_run or {r["id"]: [obchod(i + 1000 * k, vyhra=i % 3 != 2) for i in range(30)]
                                   for k, r in enumerate(records)}

    def all(self):
        return list(self._records)

    def get(self, run_id):
        return next((r for r in self._records if r["id"] == run_id), None)

    def trades(self, run_id):
        return list(self._trades.get(run_id, []))

    def chart(self, run_id):
        return None


# --------------------------------------------------------------------------- #
# drobnosti, na ktorých stojí čitateľnosť
# --------------------------------------------------------------------------- #


def test_skratka_reze_na_hranici_slova():
    """Useknuté slovo vyzerá ako chyba, nie ako skratka."""
    dlhy = "Najhorsia skupina je 'do 0.4811' vlastnosti 'Kde v rozsahu, v smere obchodu'"
    out = pp._skratka(dlhy, 60)

    assert len(out) <= 61
    assert out.endswith("…")
    assert not out[:-1].endswith(" ")
    assert dlhy.startswith(out[:-1].rstrip("…,;: "))


def test_kratky_text_sa_nemeni():
    assert pp._skratka("DRZI") == "DRZI"


def test_tabulka_ma_hlavicku_aj_oddelovac():
    t = pp._tabulka(["a", "b"], [[1, 2], [3, 4]]).split("\n")

    assert t[0] == "| a | b |"
    assert t[1] == "|---|---|"
    assert t[2] == "| 1 | 2 |"


# --------------------------------------------------------------------------- #
# sekcia po oknách — konvencia repozitára
# --------------------------------------------------------------------------- #


def test_referencne_okna_idu_v_poradi_a_pocita_sa_znamienko():
    from tester.hyperopt import REFERENCE_WINDOWS

    zaznamy = [beh(f"r{i}", w, break_even=0.1 if i < 4 else -0.05)
               for i, w in enumerate(REFERENCE_WINDOWS)]
    s = pp._po_oknach(zaznamy)

    assert "kladné v 4 z 5 okien" in s.verdict
    poradie = [r for r in s.body.split("\n") if r.startswith("| 20")]
    assert [p.split(" | ")[0].lstrip("| ") for p in poradie] == list(REFERENCE_WINDOWS)


def test_chybajuce_referencne_okno_sa_povie_nahlas():
    from tester.hyperopt import REFERENCE_WINDOWS

    s = pp._po_oknach([beh("r0", REFERENCE_WINDOWS[0])])

    assert "Chýbajú referenčné okná" in s.body
    for w in REFERENCE_WINDOWS[1:]:
        assert w in s.body


def test_z_viacerych_behov_v_okne_ide_do_riadku_ten_s_najviac_obchodmi():
    """Dva behy v jednom okne sú alternatívy; zmiešať ich do riadku by bola chyba."""
    okno = "20250904-20260904"
    s = pp._po_oknach([beh("maly", okno, obchodov=5, break_even=-0.2),
                       beh("velky", okno, obchodov=40, break_even=0.3)])

    assert "`velky` (+1)" in s.body
    assert "kladné v 1 z 1 okien" in s.verdict


def test_bez_okna_je_to_medzera_nie_prazdna_sekcia():
    zaznam = beh("r0", "")
    zaznam["settings"]["timerange"] = None
    s = pp._po_oknach([zaznam])

    assert s.gap
    assert not s.body


# --------------------------------------------------------------------------- #
# celý dokument
# --------------------------------------------------------------------------- #


@pytest.fixture
def doc():
    from tester.hyperopt import REFERENCE_WINDOWS

    zaznamy = [beh(f"r{i}", w) for i, w in enumerate(REFERENCE_WINDOWS)]
    store = FakeStore(zaznamy)
    return pp.build(zaznamy, store, strategy="ibs", title="Skúška",
                    command="python -m tester.webapp.cli paper --runs r0")


def test_dokument_ma_nadpis_prikaz_a_zoznam_behov(doc):
    text = pp.render(doc)

    assert text.startswith("# Skúška — ")
    assert "python -m tester.webapp.cli paper --runs r0" in text
    for r in doc.runs:
        assert f"`{r['id']}`" in text


def test_zaver_ostava_prazdny(doc):
    """Vygenerovaná záverečná veta by vyzerala ako zistenie, a nie je."""
    text = pp.render(doc)

    assert "## Záver" in text
    assert "Nechávam ju prázdnu zámerne" in text


def test_limity_su_v_kazdom_dokumente(doc):
    text = pp.render(doc)

    assert "## Čo tento dokument nehovorí" in text
    assert "Je to história, nie budúcnosť" in text
    assert "Preoptimalizovanie sa z týchto čísel nezistí" in text


def test_sekcia_bez_dat_ide_medzi_medzery_a_nie_do_verdiktov(doc):
    """Toto je celý zmysel dokumentu: čo sa nespočítalo, nesmie vyzerať ako zistenie."""
    doc.sections = [pp.Section("Hotová", "telo", verdict="DRZI"),
                    pp.Section("Nespočítaná", "", gap="chýbajú sviečky")]
    text = pp.render(doc)

    zhrnutie = text.split("## Zhrnutie testov")[1].split("##")[0]
    assert "DRZI" in zhrnutie
    assert "Nespočítaná" not in zhrnutie
    assert "## Na čo behy nestačili" in text
    assert "chýbajú sviečky" in text


def test_bez_medzier_sa_sekcia_o_medzerach_nepise(doc):
    doc.sections = [pp.Section("Hotová", "telo", verdict="DRZI")]

    assert "## Na čo behy nestačili" not in pp.render(doc)


def test_nulltest_bez_sviecok_je_medzera_a_nie_pad(doc):
    """Sviečky vo fake sklade nie sú — sekcia to musí prežiť."""
    nahoda = next(s for s in doc.sections if "náhody" in s.title)

    assert nahoda.gap
    assert not nahoda.verdict


def test_matica_z_prazdnej_historie_je_medzera_s_prikazom(doc):
    matica = next(s for s in doc.sections if "iných trhoch" in s.title)

    assert matica.gap
    assert "cli matrix" in matica.gap


# --------------------------------------------------------------------------- #
# hranice
# --------------------------------------------------------------------------- #


def test_bez_dobehnutych_behov_to_povie(doc):
    with pytest.raises(ValueError, match="dobehnuté"):
        pp.build([], FakeStore([]), strategy="ibs")


def test_behy_bez_obchodov_su_chyba_nie_prazdny_dokument():
    zaznam = beh("r0", "20250904-20260904")
    store = FakeStore([zaznam], per_run={"r0": []})

    with pytest.raises(ValueError, match="obchody"):
        pp.build([zaznam], store, strategy="ibs")


def test_nazov_suboru_nesie_strategiu_trh_a_datum(doc):
    from datetime import date

    meno = pp.filename(doc).name

    assert meno.startswith("MERANIE_ibs_testusd_")
    assert date.today().isoformat() in meno
    assert meno.endswith(".md")


def test_vlastny_nazov_ma_prednost(doc):
    assert pp.filename(doc, "REZIM_skuska").name == "REZIM_skuska.md"
    assert pp.filename(doc, "REZIM_skuska.md").name == "REZIM_skuska.md"


def test_viac_trhov_ma_v_nazve_viac_trhov():
    zaznamy = [beh("r0", "20240904-20250904"),
               beh("r1", "20250904-20260904", pair="TEST2/USD")]
    d = pp.build(zaznamy, FakeStore(zaznamy), strategy="ibs")

    assert "viac_trhov" in pp.filename(d).name


# --------------------------------------------------------------------------- #
# jeden merací engine
# --------------------------------------------------------------------------- #


def test_meria_sa_bateriou_checkupu_a_nie_vlastnym_poradim(monkeypatch):
    """Keby si meranie počítalo vlastné poradie, dva dokumenty o tej istej stratégii
    by sa nedali porovnať — a to je presne to, čo majú riešiť."""
    from tester import checkup as ck

    volania = []
    povodne = ck.measure

    def sleduj(records, trades, **kw):
        volania.append((len(records), len(trades), kw.get("strategy")))
        return povodne(records, trades, **kw)

    monkeypatch.setattr(ck, "measure", sleduj)
    zaznamy = [beh("r0", "20240904-20250904"), beh("r1", "20250904-20260904")]
    pp.build(zaznamy, FakeStore(zaznamy), strategy="ibs")

    assert volania == [(2, 60, "ibs")]


def test_posudok_baterie_ide_do_dokumentu(doc):
    """Silné stránky a chyby sú tie isté vety, aké má stratégia vo svojej ANALYTIKA.md."""
    doc.strengths = ["Break-even drží nad poplatkom."]
    doc.weaknesses = ["Málo obchodov."]
    text = pp.render(doc)

    assert "**V čom je dobrá**" in text
    assert "Break-even drží nad poplatkom." in text
    assert "**Kde má chyby**" in text
    assert "Málo obchodov." in text


def test_poplatok_do_baterie_ide_z_behov(monkeypatch):
    """`fee` je v behu ako podiel (0,0005), batéria ho chce v percentách."""
    from tester import checkup as ck

    videne = {}
    povodne = ck.measure
    monkeypatch.setattr(ck, "measure", lambda r, t, **kw: (videne.update(kw),
                                                           povodne(r, t, **kw))[1])
    zaznamy = [beh("r0", "20250904-20260904")]
    pp.build(zaznamy, FakeStore(zaznamy), strategy="ibs")

    assert videne["fee_pct"] == pytest.approx(0.05)
