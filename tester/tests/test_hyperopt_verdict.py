"""Verdikt hyperoptu a matice: znamienkom je break-even NAD POPLATKOM, nie nad nulou.

Break-even 0,01 % pri poplatku 0,05 % je strata; keby verdikt bral „kladný", vyhlásil by
prežitie tam, kde burza zoberie viac, než stratégia zarobí.
"""

from __future__ import annotations

from tester import hyperopt as ho, matrix as mx


def beh(timerange: str, be: float, fee: float = 0.0005, trades: int = 30, pair: str = "A") -> dict:
    return {"id": f"r-{timerange}-{pair}", "status": "done",
            "settings": {"timerange": timerange, "fee": fee, "pair": pair, "timeframe": "3m"},
            "result": {"break_even_pct": be, "trades": trades}}


def test_edge_je_break_even_minus_poplatok():
    assert abs(ho.edge_of(beh("w", 0.08)) - 0.03) < 1e-9
    assert ho.edge_of({"result": {}}) is None


def test_kladny_break_even_pod_poplatkom_nie_je_prezitie():
    okna = [beh("tuned", 0.3)] + [beh(f"w{i}", 0.01) for i in range(4)]
    assert "PRETRENOVANE" in ho.verdict(okna, "tuned")

    okna = [beh("tuned", 0.3)] + [beh(f"w{i}", 0.09) for i in range(4)]
    assert "VITAZ PREZIL" in ho.verdict(okna, "tuned")

    okna = [beh("tuned", 0.3), beh("w1", 0.09), beh("w2", 0.09), beh("w3", 0.02), beh("w4", 0.0)]
    assert "NEJASNE" in ho.verdict(okna, "tuned")


def test_matica_porovnava_s_poplatkom_bunky():
    """CFD bunka s poplatkom 0,001 % a krypto s 0,05 %: rovnaký break-even, iný záver."""
    trhy = [beh("w", 0.03, fee=0.00001, pair=p) for p in ("A", "B", "C")]
    assert "MYSLIENKA DRZI" in mx.verdict(trhy)

    trhy = [beh("w", 0.03, fee=0.0005, pair=p) for p in ("A", "B", "C")]
    assert "MYSLIENKA DRZI" not in mx.verdict(trhy)


def test_detail_ma_jeden_tvar_pre_webapp_aj_cli():
    rec = {"id": "h1", "status": "done", "note": "x",
           "settings": {"strategy": "ibs", "pair": "A", "timeframe": "3m", "timerange": "tuned",
                        "fee": 0.0005, "hyperopt": {"knobs": {"rrRatio": "2:8:0.5"}, "goal": "break_even",
                                                    "overrides": {"rrRatio": 4.0}}}}
    overenia = [{**beh("tuned", 0.3), "settings": {**beh("tuned", 0.3)["settings"],
                                                    "hyperopt_run": {"id": "h1", "tuned": True}}}]
    overenia += [{**beh(f"w{i}", 0.09), "settings": {**beh(f"w{i}", 0.09)["settings"],
                                                      "hyperopt_run": {"id": "h1"}}} for i in range(4)]
    cudzi = {**beh("w9", 0.09), "settings": {**beh("w9", 0.09)["settings"], "hyperopt_run": {"id": "h2"}}}

    d = ho.detail(rec, [{"epoch": 1, "loss": -0.1, "usable": True}], overenia + [cudzi])

    assert d["params"] == ["rrRatio"] and d["overrides"] == {"rrRatio": 4.0}
    assert len(d["verify"]) == 5 and d["verify"][0]["tuned"] is True
    assert "VITAZ PREZIL" in d["verdict"]
