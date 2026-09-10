"""Kalendár: sviatky búrz a makro udalosti.

Sviatky sú **pravidlo**, takže sa dajú overiť proti dátumom, ktoré poznáme. Makro udalosti
pravidlo nemajú a sú odpísané zo zdroja — tam sa stráži hlavne to, že sa mimo pokrytia
nedopĺňa nič: mlčanie kalendára sa nesmie čítať ako pokojný deň.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from tester import calendar as cal


def obchod(iso: str) -> dict:
    return {"open_date": iso, "open_rate": 100.0, "close_rate": 101.0, "amount": 1.0}


# --------------------------------------------------------------------------- #
# sviatky sú pravidlo
# --------------------------------------------------------------------------- #


def test_velka_noc_sedi_so_znamymi_rokmi():
    assert cal.easter(2021) == date(2021, 4, 4)
    assert cal.easter(2024) == date(2024, 3, 31)
    assert cal.easter(2025) == date(2025, 4, 20)


def test_americke_sviatky_2024_sedia():
    """Overené proti kalendáru NYSE — pravidlo musí dať presne tie dni."""
    h = cal.us_holidays(2024)

    assert h[date(2024, 1, 15)] == "Deň M. L. Kinga"      # tretí pondelok januára
    assert h[date(2024, 2, 19)] == "Deň prezidentov"
    assert h[date(2024, 3, 29)] == "Veľký piatok"
    assert h[date(2024, 5, 27)] == "Deň pamiatky"          # posledný pondelok mája
    assert h[date(2024, 11, 28)] == "Vďakyvzdanie"         # štvrtý štvrtok novembra
    assert len(h) == 10


def test_juneteenth_je_sviatkom_burzy_az_od_2022():
    assert date(2021, 6, 18) not in cal.us_holidays(2021)
    assert date(2021, 6, 19) not in cal.us_holidays(2021)
    assert date(2022, 6, 20) in cal.us_holidays(2022)      # 19. bola nedeľa


def test_sviatok_cez_vikend_sa_drzi_v_susedny_pracovny_den():
    """4. júla 2021 bola nedeľa — burza mala zatvorené v pondelok 5."""
    assert date(2021, 7, 5) in cal.us_holidays(2021)
    assert date(2021, 7, 4) not in cal.us_holidays(2021)
    # 1. januára 2022 bola sobota — drží sa v piatok 31. decembra 2021
    assert date(2021, 12, 31) in cal.us_holidays(2021)


def test_polovicne_dni():
    assert cal.us_half_days(2024)[date(2024, 11, 29)] == "deň po Vďakyvzdaní"
    assert date(2024, 12, 24) in cal.us_half_days(2024)


def test_europske_sviatky_maju_velkonocny_pondelok_aj_1_maj():
    h = cal.eu_holidays(2024)

    assert date(2024, 4, 1) in h                            # Veľkonočný pondelok
    assert date(2024, 5, 1) in h
    assert date(2024, 12, 26) in h


# --------------------------------------------------------------------------- #
# makro udalosti sú odpísané, nie odvodené
# --------------------------------------------------------------------------- #


def test_kalendar_ma_pokrytie_aj_zdroj():
    """Bez zdroja sa o rok nedá zistiť, čo treba doplniť a odkiaľ."""
    rozsah = cal.coverage()

    assert rozsah and rozsah[0] < rozsah[1]
    for kluc, blok in (cal._raw().get("events") or {}).items():
        assert blok.get("source"), kluc
        assert blok.get("dates"), kluc


def test_znama_udalost_sedi():
    e = cal.events()

    assert e[date(2024, 1, 31)][0] == "FOMC"                # posledný deň zasadnutia
    assert e[date(2024, 5, 15)][0] == "CPI"
    assert e[date(2024, 3, 8)][0] == "NFP"                  # nie prvý piatok!


def test_nfp_nie_je_vzdy_prvy_piatok():
    """Preto sa dátumy odpisujú a neodvodzujú pravidlom."""
    e = cal.events()

    assert date(2024, 3, 1) not in e                        # prvý piatok marca 2024
    assert e[date(2024, 3, 8)][0] == "NFP"


def test_dva_vypisy_v_jeden_den_sa_nezlucia_do_jednej_udalosti():
    e = cal.events()
    spolocne = [v[0] for v in e.values() if "+" in v[0]]

    assert spolocne, "aspoň jeden deň má dve udalosti"
    assert all(len(x.split("+")) == 2 for x in spolocne)
