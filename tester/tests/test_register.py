"""Register pokusov, rozpočet, trezory a zámky (`tester.register`, SMERNICA V2 §1–2, zadanie U6 a U7)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tester import hyperopt as ho
from tester import register as rg

def _ok(*_a, **_k) -> bool:
    return True


def _nie(*_a, **_k) -> bool:
    return False


HLAVICKA = """# Hypotéza `orb-test`

## Dôvod edge
Ráno po otvorení NY sa rozsah prvých minút prerazí v smere toku príkazov. Inštitúcie dokupujú. Platí len v seanse.

## Zdroj
Článok X (2019).

## Štúdie a výskumy
žiadne

## Mriežka
rr 1,5:3:0,5; orMinutes 5,15

## Trhy
MNQ, ES

## Obdobie L
podľa §1

## Hranice brán
podľa SMERNICE V2 krok 7–8

## Typ vstupu a filter IBS + pin bar
stop vstup, bez IBS a pin baru

## Pevné parametre
`entryType`, `ibsFilter`

## Iný režim
ATR % 2022Q2 mimo IQR L (zmerané 28. 11.)
"""


@pytest.fixture
def reg(tmp_path):
    (tmp_path / "orb-test.md").write_text(HLAVICKA, encoding="utf-8")
    return tmp_path


def _pokus(i: int, **extra):
    row = {"source": "grid", "key": "orb", "pair": "MNQ/USD", "tf": "3m", "timerange": "20200101-20210101",
           "params": {"rr": 1.5 + i}, "pf": 1.1, "trades": 100, "git": "abc"}
    row.update(extra)
    return row


# -- rozdelenie ---------------------------------------------------------------- #

def test_rozdelenie_trhov_podla_paragrafu_1():
    assert rg.market_of("MNQ/USD") == "MNQ" and rg.market_of("BTC/USDT:USDT") == "BTC"
    assert rg.market_of("NAS100/USD") is None and rg.market_of("ETH/USDT:USDT") is None
    assert rg.market_of_instrument("mnq_databento") == "MNQ" and rg.market_of_instrument("nas100_dukascopy") is None
    assert rg.l_timerange("MNQ") == "20190505-20221001"
    okna = rg.l_windows("MNQ")
    assert okna[0] == "20190505-20200505" and okna[-1].endswith("-20221001")
    assert all(okna[i].split("-")[1] == okna[i + 1].split("-")[0] for i in range(len(okna) - 1))
    assert rg.zones("20221001-20231001", "MNQ") == ["B"]
    assert rg.zones("20250904-20260904", "MNQ") == ["A"]
    assert rg.zones("20210101-20230101", "MNQ") == ["L", "B"]
    assert rg.zones("20120101-20130101", "ES") == ["B"]
    assert rg.zones("20230101-20240101", "MGC") == ["L"]         # MGC je obrátené: trezor 2020–22 pred L


def test_hladanie_nikdy_nesiahne_na_trezor_ani_rok_a():
    rg.check_search("20200101-20210101", "MNQ/USD")
    for zle in ("20221001-20231001", "20250904-20260904", "20220101-20230101"):
        with pytest.raises(rg.RegisterError, match="mimo L"):
            rg.check_search(zle, "MNQ/USD")
    rg.check_search("20250904-20260904", "NAS100/USD")          # CFD nemá v §1 rozdelenie
    # checkup a hyperopt bez prepínača: okná L po rokoch, nie päť referenčných (tie ležia v trezore MNQ)
    assert ho.windows_for("MNQ/USD") == rg.l_windows("MNQ")
    assert ho.windows_for("NAS100/USD") == list(ho.REFERENCE_WINDOWS)
    assert ho.search_problem(None, ho.REFERENCE_WINDOWS, "MNQ/USD")
    assert ho.search_problem(None, ho.windows_for("MNQ/USD"), "MNQ/USD") is None
    assert ho.search_problem("20250904-20260904", None, "ES/USD")


def test_t_req_tabulka_smernice():
    for k, t in ((1, 1.96), (5, 2.58), (10, 2.81), (20, 3.02), (50, 3.29), (100, 3.48), (160, 3.61)):
        assert rg.t_req(k) == pytest.approx(t, abs=0.011)
    assert rg.t_req(10, economic=True) == pytest.approx(rg.t_req(10) - 0.3)
    assert rg.t_req(10, few_trades=True, skew=True) == pytest.approx(rg.t_req(10) + 0.8)


def test_dlzka_trezoru():
    for m in rg.MARKETS:
        assert rg.vault_length_ok(m)[0], m


# -- hlavička a pokusy --------------------------------------------------------- #

def test_hlavicka_musi_byt_hotova_a_commitnuta(reg):
    assert rg.header_problems(rg.header_template("x"))                      # šablóna nie je hotová
    assert rg.header_problems(HLAVICKA) == []
    assert rg.header_markets("orb-test", reg) == ["ES", "MNQ"]
    assert rg.header_fixed("orb-test", reg) == {"entryType", "ibsFilter"}
    with pytest.raises(rg.RegisterError, match="commitnutá"):
        rg.require_header("orb-test", reg, committed=_nie)
    rg.require_header("orb-test", reg, committed=_ok)
    with pytest.raises(rg.RegisterError, match="chýba hlavička"):
        rg.append("ina", _pokus(0), reg, committed=_ok)
    with pytest.raises(rg.RegisterError):
        rg.header_path("Zle Meno")


def test_beh_bez_hlavicky_alebo_mimo_l_je_odmietnuty(reg):
    with pytest.raises(rg.RegisterError, match="commitnutá"):
        rg.append("orb-test", _pokus(0), reg, committed=_nie)
    with pytest.raises(rg.RegisterError, match="mimo L"):
        rg.append("orb-test", _pokus(0, timerange="20221001-20231001"), reg, committed=_ok)
    with pytest.raises(rg.RegisterError, match="zdroj"):
        rg.append("orb-test", _pokus(0, source="nahoda"), reg, committed=_ok)
    assert rg.attempts("orb-test", reg) == []


def test_rozpocet_300_konfiguracii(reg, monkeypatch):
    monkeypatch.setattr(rg, "BUDGET", 3)
    for i in range(3):
        rg.append("orb-test", _pokus(i), reg, committed=_ok)
    rg.append("orb-test", _pokus(0, timerange="20210101-20220101"), reg, committed=_ok)   # tá istá konfigurácia
    rg.append("orb-test", _pokus(9, source="wf"), reg, committed=_ok)                     # WF sa do 300 neráta
    with pytest.raises(rg.RegisterError, match="rozpočet"):
        rg.append("orb-test", _pokus(3), reg, committed=_ok)
    st = rg.status("orb-test", reg)
    assert st["budget_used"] == 3 and st["N"] == 3 and st["attempts"] == 5


def test_najviac_5_volnych_parametrov(reg):
    params = {}
    rg.append("orb-test", _pokus(0, params={}), reg, committed=_ok)       # východisko: všetko default
    for i, name in enumerate(["a", "b", "c", "d", "e"]):
        params = {**params, name: i}
        rg.append("orb-test", _pokus(0, params=dict(params)), reg, committed=_ok)
    # entryType je v hlavičke pevný -> nerátá sa
    rg.append("orb-test", _pokus(0, params={**params, "entryType": "Limit"}), reg, committed=_ok)
    with pytest.raises(rg.RegisterError, match="voľných parametrov"):
        rg.append("orb-test", _pokus(0, params={**params, "f": 1}), reg, committed=_ok)
    with pytest.raises(rg.RegisterError, match="voľných parametrov"):          # TF je tiež parameter
        rg.append("orb-test", _pokus(0, params=dict(params), tf="5m"), reg, committed=_ok)


def test_strop_novych_hypotez_za_stvrtrok(reg, monkeypatch):
    monkeypatch.setattr(rg, "MAX_NEW_PER_QUARTER", 1)
    (reg / "druha.md").write_text(HLAVICKA, encoding="utf-8")
    t = datetime(2026, 12, 1, tzinfo=timezone.utc)
    rg.append("orb-test", _pokus(0), reg, committed=_ok, now=t)
    with pytest.raises(rg.RegisterError, match="nových hypotéz"):
        rg.append("druha", _pokus(0), reg, committed=_ok, now=t)
    rg.append("druha", _pokus(0), reg, committed=_ok, now=datetime(2027, 1, 2, tzinfo=timezone.utc))


def test_n_a_n_eff():
    rast = [{"month": f"2020-{m:02d}", "pnl": float(m)} for m in range(1, 13)]
    sum_ = [{"month": f"2020-{m:02d}", "pnl": (-1) ** m * 5.0} for m in range(1, 13)]
    rows = [{"source": "grid", "key": "x", "params": {"a": i}, "monthly": rast} for i in range(10)]
    rows += [{"source": "grid", "key": "x", "params": {"b": 1}, "monthly": sum_},
             {"source": "wf", "key": "x", "params": {"c": 1}},
             {"source": "legacy", "n": 40}]
    assert rg.n_trials(rows) == 11 + 40                  # WF nie, legacy odhadom
    assert rg.n_eff(rows) == 2                           # 10 rovnakých kriviek = 1 zhluk, + šum; podlaha 51/50 → 2
    assert rg.n_eff([{"source": "legacy", "n": 500}]) == 10


def test_mesacny_pnl_a_pokus_z_behu():
    trades = [{"close_date": "2020-01-05T10:00:00+00:00", "profit_abs": 10},
              {"close_date": "2020-01-20T10:00:00+00:00", "profit_abs": -4},
              {"close_date": "2020-03-01T10:00:00+00:00", "profit_abs": 7}]
    assert rg.monthly_pnl(trades) == [{"month": "2020-01", "pnl": 6.0}, {"month": "2020-03", "pnl": 7.0}]
    rec = {"id": "r1", "settings": {"strategy": "orb", "pair": "MNQ/USD", "timeframe": "3m",
                                    "timerange": "20200101-20210101"},
           "params": {"rr": 2}, "result": {"profit_factor": 1.3, "trades": 3}}
    row = rg.attempt_of_run(rec, trades)
    assert (row["market"], row["pf"], row["trades"], row["source"]) == ("MNQ", 1.3, 3, "manual")


# -- trezory -------------------------------------------------------------------- #

def _k0(reg, market="MNQ", k=160):
    data = rg.load_vaults(reg)
    data.setdefault("markets", {}).setdefault(market, {}).setdefault("k0", {})["B"] = {"k": k}
    rg.save_vaults(data, reg)


def test_trezor_sa_otvara_raz_a_k_rastie(reg):
    kw = {"committed": _ok, "k0_committed": _ok}
    with pytest.raises(rg.RegisterError, match="počiatočné k nie je spočítané"):
        rg.open_vault("orb-test", "MNQ", "B", ["orb"], reg, **kw)
    _k0(reg)
    with pytest.raises(rg.RegisterError, match="nie je commitnuté"):
        rg.open_vault("orb-test", "MNQ", "B", ["orb"], reg, committed=_ok, k0_committed=_nie)
    r = rg.open_vault("orb-test", "MNQ", "B", ["orb", "orbnet"], reg, **kw)
    assert r["k"] == 162 and r["t_req"] == pytest.approx(rg.t_req(162)) and r["regime_measured"]
    assert r["period"] == ["2022-10-01", "2025-09-03"]
    with pytest.raises(rg.RegisterError, match="už trezor"):
        rg.open_vault("orb-test", "MNQ", "B", ["orb"], reg, **kw)
    (reg / "druha.md").write_text(HLAVICKA, encoding="utf-8")
    assert rg.open_vault("druha", "MNQ", "B", ["x"], reg, **kw)["k"] == 163
    assert rg.k_of("MNQ", "B", rg.load_vaults(reg)) == 163
    with pytest.raises(rg.RegisterError, match="c_from"):
        rg.open_vault("orb-test", "MNQ", "C", ["orb"], reg, **kw)
    _k0(reg, "MGC")
    with pytest.raises(rg.RegisterError, match="nie je v hlavičke"):
        rg.open_vault("orb-test", "MGC", "B", ["orb"], reg, **kw)
    with pytest.raises(rg.RegisterError, match="commitnutá"):
        rg.open_vault("orb-test", "ES", "B", ["orb"], reg, committed=_nie, k0_committed=_ok)
    assert rg.vault_timerange("MNQ", "B", rg.load_vaults(reg)) == "20221001-20250904"


def test_walk_forward_raz_na_hypotezu(reg):
    rg.lock_wf("orb-test", reg)
    with pytest.raises(rg.RegisterError, match="walk-forward už bežal"):
        rg.lock_wf("orb-test", reg)
    assert rg.status("orb-test", reg)["wf"]


def test_pociatocne_k_z_historie_behov():
    behy = [{"strategy": "a", "pair": "ES/USD", "timerange": "20120101-20130101"},
            {"strategy": "b", "pair": "ES/USD", "timerange": "20100701-20150101"},
            {"strategy": "c", "pair": "ES/USD", "timerange": "20200101-20210101"},       # L, nie trezor
            {"strategy": "z", "pair": "MNQ/USD", "timerange": "20221001-20231001"},
            {"strategy": "q", "pair": "NAS100/USD", "timerange": "20221001-20231001"}]
    k = rg.initial_k(settings=behy, registry_keys=["a", "x", "y"])
    assert k["ES"]["k"] == rg.TRIEDENIE_FAMILIES and k["ES"]["keys"] == ["a", "b"]    # triedenie: najmenej 11 rodín
    # trezor MNQ leží v referenčných oknách -> všetky kľúče registra + nájdené + štúdie
    assert k["MNQ"]["keys"] == ["a", "x", "y", "z"]
    assert k["MNQ"]["k"] == 4 + len(k["MNQ"]["studies"]) and "NASDAQ-STUDIUM" in k["MNQ"]["studies"]
