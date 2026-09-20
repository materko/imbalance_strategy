"""Najdlhšia séria ziskov a strát v súhrne behu — jedna definícia pre oba enginy.

Séria hovorí to, čo priemerný winrate zamlčí: koľko strát za sebou musí tester ustáť
a kedy to bolo. Preto ju počíta `tradebot.core.money` (ten istý vzorec pre emulátor
MultiCharts aj pre normalizovaný Freqtrade beh), nesie len rozsah indexov do obchodov
behu — obchody série sa vypíšu z `trades.json`, takže sa so súhrnom nemôžu rozísť —
a starým behom ju dopočíta prepočet (`tester.recompute`) aj detail behu vo webapp.
"""

from __future__ import annotations

from tester.trade_metrics import streaks_with_trades
from tradebot.core.money import streaks, summary_money


def _rows(*profits: float) -> list[dict]:
    return [{"open_date": f"2026-01-{i + 1:02d}T10:00:00+00:00",
             "close_date": f"2026-01-{i + 1:02d}T12:00:00+00:00",
             "open_rate": 100.0, "close_rate": 100.0 + p, "amount": 1.0, "point_value": 1.0,
             "exit_reason": "take_profit" if p > 0 else "stop_loss", "profit_abs": p}
            for i, p in enumerate(profits)]


def test_najdlhsia_seria_vie_kolko_kedy_a_za_kolko():
    s = streaks(_rows(1, 2, -1, -2, -3, 4, 5, 6, 7, -1))
    assert s["win"]["n"] == 4 and (s["win"]["from_i"], s["win"]["to_i"]) == (5, 8)
    assert s["win"]["pnl_abs"] == 22.0
    assert s["win"]["start"].startswith("2026-01-06") and s["win"]["end"].startswith("2026-01-09")
    assert s["loss"]["n"] == 3 and (s["loss"]["from_i"], s["loss"]["to_i"]) == (2, 4)
    assert s["loss"]["pnl_abs"] == -6.0


def test_rozsah_serie_sedi_na_obchody_behu():
    """`from_i`..`to_i` sú indexy do obchodov — výpis série je presne tých n obchodov."""
    rows = _rows(1, -1, -2, -3, 2)
    s = streaks(rows)["loss"]
    vybrane = rows[s["from_i"]: s["to_i"] + 1]
    assert len(vybrane) == s["n"]
    assert sum(t["profit_abs"] for t in vybrane) == s["pnl_abs"]
    assert all(t["profit_abs"] < 0 for t in vybrane)


def test_rovnako_dlhe_serie_a_nulovy_obchod():
    """Vypíše sa prvá z rovnako dlhých sérií; nulový obchod do série nepatrí a preruší ju."""
    s = streaks(_rows(-1, -2, 3, -4, -5, 6))
    assert s["loss"]["from_i"] == 0 and s["loss"]["count"] == 2
    bez_nuly = streaks(_rows(1, 0, 2, 3))
    assert bez_nuly["win"]["n"] == 2 and bez_nuly["win"]["from_i"] == 2
    prazdne = streaks([])
    assert prazdne["win"] is None and prazdne["loss"] is None


def test_suhrn_behu_serie_nesie():
    suhrn = summary_money(_rows(1, 1, -1, -1, -1), 1_000.0)
    assert suhrn["streaks"]["win"]["n"] == 2 and suhrn["streaks"]["loss"]["n"] == 3
    assert summary_money([], 1_000.0)["streaks"] == {"win": None, "loss": None}


def test_prepocet_doplni_serie_staremu_behu():
    """Beh spred sérií ich v `run.json` nemá — prepočet ich dopíše ako zmenu súhrnu."""
    from tester.recompute import recompute_run

    rows = _rows(1, -1, -2, 3)
    stary = {k: v for k, v in summary_money(rows, 1_000.0).items() if k != "streaks"}
    rec = {"id": "20260920-101010-abcd", "status": "done",
           "settings": {"pair": "BTC/USDT:USDT", "engine": "multicharts", "wallet": 1_000.0},
           "result": {**stary, "starting_balance": 1_000.0}, "series": {"equity": []}}
    out = recompute_run(rec, rows)
    assert out.changes["streaks"][0] is None
    assert out.summary["streaks"]["loss"]["n"] == 2


# --------------------------------------------------------------------------- #
# analytika: séria si nesie svoje obchody (zliate behy nemajú „index do behu")
# --------------------------------------------------------------------------- #


def test_analytika_nesie_obchody_serie_a_radi_ich_podla_zatvorenia():
    """Obchody prídu z dvoch behov v poradí načítania — séria musí ísť podľa času."""
    rows = _rows(1, -1, -2, -3, 2)
    prehadzane = [rows[3], rows[0], rows[4], rows[1], rows[2]]
    s = streaks_with_trades(prehadzane)["loss"]
    assert s["n"] == 3 and s["pnl_abs"] == -6.0
    assert [t["profit_abs"] for t in s["trades"]] == [-1, -2, -3]
    assert "from_i" not in s and "to_i" not in s     # index do zliatych behov nič neznamená


def test_analytika_behu_serie_obsahuje():
    from tester.trade_splits import analyze

    report = analyze(_rows(1, 1, -1, -1, -1, 2), strategy="ibs", min_bucket=5)
    assert report["streaks"]["win"]["n"] == 2 and report["streaks"]["loss"]["n"] == 3


# --------------------------------------------------------------------------- #
# dokument stratégie
# --------------------------------------------------------------------------- #


def test_analytika_strategie_serie_vypise_aj_s_obchodmi():
    """`ANALYTIKA.md`: sekcia so sériami a stĺpec `séria +/-` v tabuľke okien."""
    from tester import checkup as ck

    beh = {"id": "20260101-000000-aaaaaa", "status": "done",
           "settings": {"timerange": "20250904-20260904", "strategy": "ibs"},
           "result": {"trades": 6, "pnl_pct": 1.0, "break_even_pct": 0.08,
                      "max_drawdown_pct": 5.0, "winrate": 50.0, "profit_factor": 1.2,
                      "streaks": streaks(_rows(1, 1, -1, -1, -1, 2))}}
    report = {
        "strategy": "ibs", "title": "IBS", "pair": "BTC/USDT:USDT", "timeframe": "3m",
        "engine": "freqtrade", "profile": "", "fee_pct": 0.05, "account": 10_000.0,
        "windows": ck.window_rows([beh]), "years_positive": 1, "years_done": 1,
        "trades": 6, "break_even_pct": 0.08, "duplicates": 0,
        "strengths": [], "weaknesses": [],
        "analytics": {"streaks": streaks_with_trades(_rows(1, 1, -1, -1, -1, 2))},
    }
    doc = ck.markdown(report)
    assert "## Najdlhšie série" in doc
    assert "**Straty za sebou: 3**" in doc
    assert "séria +/-" in doc and "| +2/-3 |" in doc
    # obchody série sú v dokumente vypísané, nie len spočítané
    assert doc.count("| `stop_loss` |") == 3
