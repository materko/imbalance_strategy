"""Portfólio z viacerých behov — a hlavne to, čo portfóliom nie je.

Dva behy toho istého trhu v tom istom období nie sú dvaja členovia, ale dve alternatívy
jednej veci. Keby sa ich obchody sčítali, to isté obdobie by sa započítalo dvakrát
a portfólio by vyzeralo dvakrát aktívnejšie, než v skutočnosti je. Prvá verzia to robila —
dvanásť behov na BTC zliala do jedného člena s 1582 obchodmi. Testy strážia práve túto
hranicu a k tomu prepočet na riziko a korelácie.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from tester import portfolio as pf


def trade(*, close="2025-03-01T12:00:00+00:00", open_rate=100.0, close_rate=101.0,
          short=False, sl_pct=1.0, exit_reason="roi", fee=0.0):
    smer = -1.0 if short else 1.0
    return {
        "open_date": close, "close_date": close,
        "open_rate": open_rate, "close_rate": close_rate, "amount": 1.0,
        "profit_abs": (close_rate - open_rate) * smer, "is_short": short,
        "exit_reason": exit_reason, "_sl_pct": sl_pct,
        "fee_open": fee, "fee_close": fee,
    }


def zaznam(run_id: str, pair: str, timerange: str, trades: int = 20):
    return {"id": run_id, "status": "done",
            "settings": {"pair": pair, "timeframe": "3m", "timerange": timerange},
            "result": {"trades": trades}}


def mesiace(pnl_po_mesiacoch: dict[str, float]) -> list[dict]:
    """Obchody tak, aby mesačné súčty vyšli presne podľa zadania."""
    out = []
    for mesiac, pnl in pnl_po_mesiacoch.items():
        cena = 100.0
        out.append(trade(close=f"{mesiac}-15T12:00:00+00:00", open_rate=cena,
                         close_rate=cena + pnl))
    return out


# --------------------------------------------------------------------------- #
# čo portfóliom nie je
# --------------------------------------------------------------------------- #


def test_ten_isty_trh_v_tom_istom_case_nie_su_dvaja_clenovia():
    """Regresia: dvanásť behov na BTC sa zlialo do jedného člena s 1582 obchodmi."""
    zaznamy = [zaznam("a", "BTC/USDT:USDT", "20250904-20260904"),
               zaznam("b", "BTC/USDT:USDT", "20250904-20260904")]
    zdvojene = pf.duplicates(zaznamy)

    assert len(zdvojene) == 1
    assert "BTC/USDT:USDT" in zdvojene[0][2]

    v = pf.analyze({"a": mesiace({"2025-01": 1.0}), "b": mesiace({"2025-01": 1.0})},
                   records=zaznamy)
    assert "TO NIE JE PORTFOLIO" in v["verdict"]


def test_ten_isty_trh_v_INOM_case_je_v_poriadku():
    """Dva roky toho istého trhu za sebou sú legitímne — neprekrývajú sa."""
    zaznamy = [zaznam("a", "BTC/USDT:USDT", "20240101-20250101"),
               zaznam("b", "BTC/USDT:USDT", "20250101-20260101")]
    assert pf.duplicates(zaznamy) == []


def test_rozne_trhy_v_tom_istom_case_su_clenovia():
    zaznamy = [zaznam("a", "BTC/USDT:USDT", "20250904-20260904"),
               zaznam("b", "XAU/USD", "20250904-20260904")]
    assert pf.duplicates(zaznamy) == []


def test_jeden_clen_nie_je_portfolio():
    v = pf.analyze({"a": mesiace({"2025-01": 1.0, "2025-02": 2.0})},
                   records=[zaznam("a", "BTC/USDT:USDT", "20250101-20260101")])
    assert "Jeden clen" in v["verdict"]


# --------------------------------------------------------------------------- #
# prepočet na riziko
# --------------------------------------------------------------------------- #


def test_velkost_pozicie_sa_prepocita_na_riziko_nie_prevezme_z_behu():
    """Bez toho by sa sčítavali veľkosti z rôznych behov a výsledok by hovoril o peňaženkách."""
    # Stop 1 % z ceny 100 = 1 bod; pri riziku 1 % z 10 000 to je 100 -> mnozstvo 100.
    # Obchod ide +1 bod, teda +100 na ucte.
    v = pf.equity_curve([trade(open_rate=100.0, close_rate=101.0, sl_pct=1.0)],
                        risk_pct=1.0, account=10_000.0)
    assert v["final"] == pytest.approx(10_100.0)
    assert v["return_pct"] == pytest.approx(1.0)


def test_dvojnasobne_riziko_je_dvojnasobny_vysledok_na_prvom_obchode():
    jeden = pf.equity_curve([trade()], risk_pct=1.0)["final"] - pf.DEFAULT_ACCOUNT
    dva = pf.equity_curve([trade()], risk_pct=2.0)["final"] - pf.DEFAULT_ACCOUNT
    assert dva == pytest.approx(jeden * 2)


def test_obchod_bez_vzdialenosti_stopu_do_prepoctu_nevstupi():
    """Radšej ho vynechať a povedať to, než mu vymyslieť veľkosť."""
    bez = trade()
    bez.pop("_sl_pct")
    v = pf.equity_curve([bez], risk_pct=1.0)
    assert v["skipped"] == 1 and v["trades"] == 0

    # Zo skutočného stopu sa vzdialenosť odvodiť dá.
    zo_stopu = trade(open_rate=100.0, close_rate=99.0, exit_reason="stop_loss")
    zo_stopu.pop("_sl_pct")
    assert pf.equity_curve([zo_stopu], risk_pct=1.0)["skipped"] == 0


def test_ruina_zastavi_beh():
    straty = [trade(open_rate=100.0, close_rate=50.0, sl_pct=1.0) for _ in range(5)]
    v = pf.equity_curve(straty, risk_pct=5.0)
    assert v["ruin"] and v["final"] == 0.0
    assert v["trades"] < len(straty)          # po ruine sa dalej nepokracuje


def test_tabulka_rizika_ma_riadok_na_kazde_riziko():
    obchody = mesiace({f"2025-{m:02d}": 1.0 for m in range(1, 13)})
    tabulka = pf.risk_table(obchody, risks=(0.5, 1.0, 2.0))
    assert [r["risk_pct"] for r in tabulka] == [0.5, 1.0, 2.0]
    # Vyssie riziko = vacsi drawdown; to je cela pointa tabulky.
    assert tabulka[0]["max_drawdown_pct"] <= tabulka[-1]["max_drawdown_pct"]


def test_rocne_zhodnotenie_je_zlozene_nie_delene_rokmi():
    """Pri dvojcifernom zhodnotení sa tie dve čísla líšia natoľko, že by z toho bol iný záver."""
    obchody = [trade(close=f"202{r}-06-15T12:00:00+00:00", open_rate=100.0, close_rate=110.0)
               for r in range(4)]
    tabulka = pf.risk_table(obchody, risks=(1.0,))
    r = tabulka[0]
    assert r["cagr_pct"] < r["return_pct"]     # zlozene je nizsie nez celkove


# --------------------------------------------------------------------------- #
# korelácie
# --------------------------------------------------------------------------- #


def test_zhodne_mesiace_daju_koreláciu_jedna():
    a = mesiace({f"2025-{m:02d}": float(m) for m in range(1, 9)})
    k = pf.correlations({"a": a, "b": list(a)})
    assert k["matrix"]["a"]["b"] == pytest.approx(1.0, abs=0.01)


def test_opacne_mesiace_daju_zapornu_korelaciu():
    a = mesiace({f"2025-{m:02d}": float(m) for m in range(1, 9)})
    b = mesiace({f"2025-{m:02d}": float(-m) for m in range(1, 9)})
    assert pf.correlations({"a": a, "b": b})["matrix"]["a"]["b"] < -0.9


def test_malo_spolocnych_mesiacov_nie_je_korelacia():
    """Regresia: z troch mesiacov vyšla korelácia +0,99 medzi NAS100 a zemným plynom."""
    a = mesiace({"2025-01": 1.0, "2025-02": 2.0, "2025-03": 3.0})
    b = mesiace({"2025-01": 1.0, "2025-02": 2.0, "2025-03": 3.5})
    k = pf.correlations({"a": a, "b": b})

    assert k["matrix"]["a"]["b"] is None
    assert k["compared"] == 0 and k["skipped"] == 1


def test_verdikt_nepovie_diverzifikovane_ked_cast_dvojic_je_nad_prahom():
    """Priemer blízko nuly môže znamenať „polovica spolu, polovica proti", nie „nezávislé"."""
    rovnake = {f"2025-{m:02d}": float(m) for m in range(1, 10)}
    opacne = {f"2025-{m:02d}": float(-m) for m in range(1, 10)}
    per = {"a": mesiace(rovnake), "b": mesiace(rovnake), "c": mesiace(opacne)}
    zaznamy = [zaznam("a", "A", "20250101-20260101"), zaznam("b", "B", "20250101-20260101"),
               zaznam("c", "C", "20250101-20260101")]

    v = pf.analyze(per, records=zaznamy)
    assert "CAST CLENOV SA HYBE SPOLU" in v["verdict"]


def test_vypis_je_ascii_kvoli_konzole_na_windows():
    per = {"a": mesiace({f"2025-{m:02d}": 1.0 for m in range(1, 10)}),
           "b": mesiace({f"2025-{m:02d}": -0.5 for m in range(1, 10)})}
    v = pf.analyze(per, records=[zaznam("a", "A", "20250101-20260101"),
                                 zaznam("b", "B", "20250101-20260101")])
    assert pf.report(v).encode("ascii", "replace")
