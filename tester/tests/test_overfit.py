"""Štatistické brány SMERNICE V2 (`tester.overfit`, `tester.walkforward`, U8/U9): PBO, haircut, Sortino, stav."""

from __future__ import annotations

import itertools
import json
import math
import random
from statistics import NormalDist

import pytest

from tester import overfit, robust


def test_bloky_pokryju_obdobie_bez_diery():
    b = overfit.blocks("20211001-20250904", 16)
    assert len(b) == 16 and b[0].startswith("20211001-") and b[-1].endswith("-20250904")
    assert all(b[i].split("-")[1] == b[i + 1].split("-")[0] for i in range(15))
    with pytest.raises(ValueError):
        overfit.blocks("20250101-20250104", 8)
    mb = overfit.month_blocks([f"2020-{m:02d}" for m in range(1, 13)] + [f"2021-{m:02d}" for m in range(1, 9)], 16)
    assert len(mb) == 16 and sum(len(x) for x in mb) == 20 and mb[0] == ["2020-01", "2020-02"]


def test_cscv_skutocny_edge_ma_nizke_pbo_a_sum_okolo_polovice():
    rng = random.Random(7)
    edge = [[1.0 + rng.gauss(0, 0.1) for _ in range(8)]] + [[rng.gauss(0, 0.1) for _ in range(8)] for _ in range(30)]
    r = overfit.cscv(edge)
    assert r["pbo"] == 0.0 and r["splits"] == 70 and r["trials"] == 31 and r["blocks"] == 8
    noise = [[rng.gauss(0, 1) for _ in range(16)] for _ in range(60)]
    r16 = overfit.cscv(noise)
    assert r16["splits"] == 12870 and 0.25 < r16["pbo"] < 0.75


def test_cscv_pretrenovane_ma_pbo_nad_polovicou():
    rows = [[1.0 if j in half else -1.0 for j in range(8)] for half in itertools.combinations(range(8), 4)]
    r = overfit.cscv(rows)
    assert r["pbo"] == 1.0 and r["degradation"] <= 0


def test_cscv_odmietne_zly_tvar():
    with pytest.raises(ValueError):
        overfit.cscv([[1, 2, 3], [1, 2, 3]])
    with pytest.raises(ValueError):
        overfit.cscv([[1, 2, 3, 4]])


def test_pbo_z_epoch_hyperoptu():
    okna = overfit.blocks("20220101-20230101", 4)
    epochs = [{"windows": {w: {"pnl_pct": (5.0 if i == 0 else 0.1 * k)} for k, w in enumerate(okna)}} for i in range(5)]
    epochs.append({"windows": {okna[0]: {"pnl_pct": 1.0}}})
    epochs.append({"windows": None})
    r = overfit.pbo_of_epochs(epochs, okna)
    assert r is not None and r["trials"] == 5 and r["metric"] == "pnl_pct" and r["pbo"] == 0.0
    assert overfit.pbo_of_epochs(epochs[:1], okna) is None


def test_pbo_z_mesacneho_pnl_registra_16_blokov():
    rng = random.Random(3)
    months = [f"{y}-{m:02d}" for y in (2020, 2021, 2022) for m in range(1, 13)]
    rows = [{"source": "grid", "key": "x", "tf": "3m", "params": {"a": 0},
             "monthly": [{"month": m, "pnl": 100 + rng.gauss(0, 10)} for m in months]}]
    rows += [{"source": "grid", "key": "x", "tf": "3m", "params": {"a": i},
              "monthly": [{"month": m, "pnl": rng.gauss(0, 10)} for m in months]} for i in range(1, 20)]
    rows.append({"source": "wf", "key": "x", "params": {"a": 99}, "monthly": [{"month": "2020-01", "pnl": 1e9}]})
    r = overfit.pbo_of_register(rows)
    assert r is not None and r["blocks"] == 16 and r["trials"] == 20 and r["months"] == 36 and r["pbo"] == 0.0
    assert overfit.pbo_of_register(rows[:1]) is None


def _hl_reference(sr: float, days: int, m: int) -> float:
    """Nezávislý prepočet Harvey–Liu BHY (najlepšia z m skúšok)."""
    nd = NormalDist()
    yrs = days / 252
    t = sr * math.sqrt(yrs)
    p = 2 * nd.cdf(-t)
    c = sum(1 / i for i in range(1, m + 1))
    padj = min(1.0, p * m * c)
    return 0.0 if padj >= 1 else nd.inv_cdf(1 - padj / 2) / math.sqrt(yrs)


def test_haircut_harvey_liu_a_pf_po_haircute():
    for sr, days, m in ((1.5, 1000, 10), (2.0, 2500, 160), (0.9, 750, 40)):
        h = overfit.haircut_hl(sr, days, m)
        assert h["sr_haircut"] == pytest.approx(_hl_reference(sr, days, m), rel=0.01)
        assert 0 <= h["ratio"] <= 1
    h1 = overfit.haircut_hl(1.5, 1000, 1)       # jediná skúška: BHY = obyčajná p-hodnota
    assert h1["sr_haircut"] == pytest.approx(1.5, rel=1e-6) and h1["haircut"] == pytest.approx(0, abs=1e-9)
    weak = overfit.haircut_hl(0.5, 500, 160)    # slabý Sharpe pri mnohých skúškach: edge zmizne
    assert weak["sr_haircut"] == 0.0 and weak["ratio"] == 0.0
    assert overfit.pf_after_haircut(1.6, 0.5) == pytest.approx(1.3) and overfit.pf_after_haircut(0.9, 0.5) == 0.9
    assert overfit.pf_mc(1.6, 200) == pytest.approx(1.3) and overfit.pf_mc(1.6, 300) == 1.6


def test_sortino():
    assert overfit.sortino([0.01, -0.01, 0.0, 0.02]) == pytest.approx(0.005 / math.sqrt(0.0001 / 4) * math.sqrt(252))
    assert overfit.sortino([0.0]) is None and overfit.sortino([0.01, 0.02]) == math.inf


def test_brany_a_stavovy_automat_na_hraniciach():
    e = 1e-9
    ok = overfit.gates(dsr_neff=0.95, dsr_n=0.50, pbo=0.20, walk_forward={"passed": True}, pf=1.4,
                       haircut_ratio=0.25 + e, sortino_oos=1.0)
    assert ok["passed"] and ok["pf_live"] == pytest.approx(1.1, abs=1e-6)
    assert overfit.status(ok) == ("🟡", "brány prešli; trezor neotvorený")
    assert overfit.status(ok, vault="✅")[0] == "🟡" and overfit.status(ok, vault="✅", signed=True)[0] == "✅"
    # každá hranica o epsilon zle
    assert overfit.status(overfit.gates(dsr_neff=0.95 - e, dsr_n=0.5, pbo=0.2, walk_forward={"passed": True}, pf=1.4,
                                        haircut_ratio=0.3, sortino_oos=1.0))[0] == "❌"
    assert overfit.status(overfit.gates(dsr_neff=0.96, dsr_n=0.5 - e, pbo=0.2, walk_forward={"passed": True}, pf=1.4,
                                        haircut_ratio=0.3, sortino_oos=1.0))[0] == "❌"
    assert overfit.status(overfit.gates(dsr_neff=0.96, dsr_n=0.6, pbo=0.2 + e, walk_forward={"passed": True}, pf=1.4,
                                        haircut_ratio=0.3, sortino_oos=1.0))[0] == "❌"
    assert overfit.status(overfit.gates(dsr_neff=0.96, dsr_n=0.6, pbo=0.1, walk_forward={"passed": True}, pf=1.4,
                                        haircut_ratio=0.3, sortino_oos=1.0 - e))[0] == "❌"
    low = overfit.gates(dsr_neff=0.96, dsr_n=0.6, pbo=0.1, walk_forward={"passed": True}, pf=1.4, haircut_ratio=0.25 - e,
                        sortino_oos=1.2)
    assert overfit.status(low) == ("⏳", "PF po haircute < 1,10")
    miss = overfit.gates(dsr_neff=0.97, dsr_n=0.6, pf=1.5, haircut_ratio=0.5)
    assert overfit.status(miss)[0] == "⏳" and set(miss["missing"]) == {"pbo", "walk_forward", "sortino"}
    assert overfit.status(ok, year_a_pf=0.99)[0] == "❌" and overfit.status(ok, vault="❌")[0] == "❌"
    # legacy: DSR, PBO, haircut len informácia; najviac 🟡, so zápornou správou ⚠
    leg = overfit.gates(dsr_neff=0.1, dsr_n=0.1, pbo=0.9, walk_forward={"passed": True}, pf=1.4, haircut_ratio=0.0,
                        sortino_oos=1.5, legacy=True)
    assert leg["passed"] and leg["info"] == ["dsr", "pbo", "haircut"]
    assert overfit.status(leg)[0] == "🟡" and overfit.status(leg, negative=True)[0] == "⚠"


def test_walk_forward_okna_v_l_a_brany():
    from tester import walkforward as wf

    mnq = wf.wf_windows("MNQ")
    assert mnq[0] == "20190505-20191105" and mnq[-1].endswith("-20221001") and wf.train_count("MNQ") == 3
    assert all(mnq[i].split("-")[1] == mnq[i + 1].split("-")[0] for i in range(len(mnq) - 1))
    assert wf.train_count("ES") == 4 and wf.wf_windows("ES")[0] == "20150101-20150701"

    class Knob:
        def __init__(self, name, low, high):
            self.name, self.low, self.high, self.choices = name, low, high, None

    def fold(i, test, pnls, rr):
        return {"fold": i, "test": test, "params": {"rr": rr}, "is_pnl_pct": 3.0, "is_days": 548, "oos_days": 183,
                "trades": [{"close": test[:4] + "-" + test[4:6] + "-10T15:00:00+00:00", "pnl": p} for p in pnls]}

    folds = [fold(0, "20210101-20210701", [300, -100], 2.0), fold(1, "20210701-20220101", [200, -100], 2.5),
             fold(2, "20220101-20220701", [150, -50], 2.0), fold(3, "20220701-20221001", [-50, 100], 2.0)]
    g = wf.wf_gates(folds, [Knob("rr", 1.0, 3.0)], wallet=10000)
    assert g["pf_oos"] == pytest.approx(750 / 300) and g["positive"] == 4 and g["positive_ok"] and g["stable_ok"]
    assert g["wfe"] is not None and g["wfe"] > 0.5 and g["passed"]
    assert sum(g["daily"].values()) == pytest.approx(450) and g["sortino_oos"] is not None
    skok = [dict(f) for f in folds]
    skok[1]["params"] = {"rr": 3.0}                                   # 2,0 -> 3,0 je ½ rozsahu (smie), späť 2,0 tiež
    assert wf.wf_gates(skok, [Knob("rr", 1.0, 3.0)])["stable_ok"]
    skok[2]["params"] = {"rr": 1.0}                                   # 3,0 -> 1,0 > ½ rozsahu
    assert not wf.wf_gates(skok, [Knob("rr", 1.0, 3.0)])["stable_ok"]
    zle = [dict(f) for f in folds]
    zle[3]["trades"] = [{"close": "2022-07-10T15:00:00+00:00", "pnl": -400}]
    gz = wf.wf_gates(zle, [Knob("rr", 1.0, 3.0)])
    assert gz["positive"] == 3 and gz["positive_ok"]                  # 3 zo 4 = 75 %
    assert not wf.wf_gates(zle, [], limits={"wf_positive_min": 0.8})["positive_ok"]
    assert "WALK-FORWARD DRZI" in wf.verdict(g)


def test_robust_ulozi_vysledok_do_profilu(tmp_path):
    p = tmp_path / "ZAKLAD_MNQ.json"
    p.write_text(json.dumps({"rr": 2.0, "_title": "X 1"}), encoding="utf-8")
    g = overfit.gates(dsr_neff=0.97, dsr_n=0.8, pbo=0.1, walk_forward={"passed": True}, pf=1.5, haircut_ratio=0.6,
                      sortino_oos=1.3)
    rep = robust.Report(profile=str(p), total={"pf": 1.5, "pf_fee2": 1.2, "pf_delay": 1.3, "trades_per_year": 120},
                        dsr={"dsr": 0.8}, dsr_neff={"dsr": 0.97}, haircut={"pf": 1.5, "pf_live": 1.3, "haircut": 0.4},
                        gates=g, status="🟡", status_reason="brány prešli")
    assert robust.save_to_profile(str(p), rep, 1234, {"pbo": 0.1, "n_eff": 40, "walk_forward": {"passed": True, "wfe": 0.7}})
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["rr"] == 2.0 and data["_title"] == "X 1"
    r = data["_robust"]
    assert (r["smernica"], r["trials"], r["n_eff"], r["dsr_neff"], r["pbo"], r["walk_forward"], r["wfe"], r["status"]) == \
        ("V2", 1234, 40, 0.97, 0.1, True, 0.7, "🟡")
    assert not robust.save_to_profile(str(tmp_path / "nie.json"), rep, 1, {})


def test_robust_berie_walk_forward_v2_a_pbo(tmp_path):
    s, w = tmp_path / "s.json", tmp_path / "w.json"
    s.write_text(json.dumps({"mode": "search", "pbo": {"pbo": 0.11}}), encoding="utf-8")
    w.write_text(json.dumps({"mode": "walkforward_v2", "verdict": "WALK-FORWARD DRZI: x",
                             "gates": {"passed": True, "sortino_oos": 1.4, "wfe": 0.6, "daily": {"2020-01-01": 1}}}),
                 encoding="utf-8")
    out = robust.from_hyperopt([s, w])
    assert out["pbo"] == 0.11 and out["sortino"] == 1.4
    assert out["walk_forward"]["passed"] is True and "daily" not in out["walk_forward"]


def test_webapp_v2_stlpce_pomlcka_cervena_a_poradie_bez_roka_a():
    """U10: nespočítané = None („—“, nikdy 0), nesplnená brána = fail, poradie stav -> PF po haircute, rok A nie."""
    from tester.webapp.api.catalog import profile_haircut, profile_order, v2_view

    empty = v2_view(None)
    assert empty["stav"] is None and empty["pf_live"] is None and empty["dsr"] is None and not any(empty["fail"].values())
    assert profile_haircut({"pf": 1.5}, {"profit_factor": 1.4}, None) is None             # žiadny odhad ½
    r = {"smernica": "V2", "status": "🟡", "pf_live": 1.05, "dsr_neff": 0.97, "dsr": 0.4, "pbo": 0.3, "trials": 120,
         "n_eff": 30, "sortino": 1.2, "trades_per_year": 60, "year_a_pf": 1.3, "legacy": True, "info": ["dsr", "pbo", "haircut"]}
    v = v2_view(r)
    assert v["fail"]["pf_live"] and v["fail"]["dsr"] and v["fail"]["pbo"] and v["fail"]["trades_year"] and not v["fail"]["sortino"]
    assert v["legacy"] and v["info"] == ["dsr", "pbo", "haircut"] and v["n"] == 120 and v["n_eff"] == 30
    a = v2_view({**r, "status": "🟡", "pf_live": 1.3})
    b = v2_view({**r, "status": "⏳", "pf_live": 1.9})
    c = v2_view({**r, "status": "🟡", "pf_live": 1.2})
    assert sorted([b, c, a], key=profile_order) == [a, c, b]
    a2 = v2_view({**r, "status": "🟡", "pf_live": 1.3, "year_a_pf": 0.5})                  # zmena len roka A
    c2 = v2_view({**r, "status": "🟡", "pf_live": 1.2, "year_a_pf": 9.0})
    assert sorted([c2, a2], key=profile_order) == [a2, c2]
    assert v2_view({"status": "✅"})["stav"] is None                                       # starý `_robust` (pred V2) sa neukazuje
