"""`tradebot.live.deploy.DeployStore`: účty, nasadenia, hash configu, id inštancie, heslo na jedno
prevzatie (`secret_pending` → `desired_for_agent` → `report_applied(secret_ack)`), audit a
pravidlá mazania — všetko bez siete, nad sqlite v dočasnom adresári."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tradebot.live.deploy import Conflict, DeployError, DeployStore, NotFound, account_identity, config_hash
from tradebot.live.schema import instance_id
from tradebot.live.store import LiveStore


class Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def _resolver(strategy: str, profile: str) -> dict:
    """Falošný profil → config: bez repozitára, ale deterministický a závislý od mena."""
    if profile == "neexistuje":
        raise FileNotFoundError(profile)
    return {"rrRatio": 3.0 if profile == "p1" else 2.5, "profile": profile, "strategy": strategy}


@pytest.fixture
def store(tmp_path: Path):
    return DeployStore(tmp_path / "live.sqlite", clock=Clock(), config_resolver=_resolver,
                       strategy_check=lambda k: {"ibsnet": "ibsnet", "ibsninja": "ibsnet", "orbnet": "orbnet"}.get(k)
                       or (_ for _ in ()).throw(DeployError(f"neznáma stratégia {k!r}")))


def _acc(store: DeployStore, **kw) -> dict:
    data = {"agent": "trade-pc", "platform": "mt5", "label": "IC Markets Demo", "login": "5012345",
            "server": "ICMarkets-Demo", **kw}
    return store.upsert_account(data, by="rasto", password=kw.pop("password", None) if "password" in kw else None)


# --------------------------------------------------------------------------- #
# účty
# --------------------------------------------------------------------------- #


def test_ucet_id_zo_slugu_a_zoznam_bez_hesla(store: DeployStore):
    a = store.upsert_account({"agent": "trade-pc", "platform": "mt5", "label": "IC Markets Demo",
                              "login": "5012345", "server": "ICMarkets-Demo"}, by="rasto", password="tajne-heslo")
    assert a["id"] == "ic-markets-demo" and a["by"] == "rasto" and a["portable"] is False
    assert a["secret_pending"] is True and "secret" not in a and "tajne" not in json.dumps(a)
    b = store.upsert_account({"agent": "trade-pc", "platform": "mt5", "label": "IC Markets Demo", "login": "9"}, by="x")
    assert b["id"] == "ic-markets-demo-2" and b["secret_pending"] is False
    assert [x["id"] for x in store.accounts()] == ["ic-markets-demo", "ic-markets-demo-2"]
    assert store.accounts(agent="iny") == [] and store.account("nie") is None
    # heslo nie je v žiadnom zozname, len v tabuľke
    assert "tajne" not in json.dumps(store.accounts())
    raw = sqlite3.connect(str(store.path)).execute("SELECT secret_pending FROM accounts WHERE id = 'ic-markets-demo'").fetchone()
    assert raw[0] == "tajne-heslo"


def test_ucet_povinne_polia_a_zmena(store: DeployStore):
    with pytest.raises(DeployError):
        store.upsert_account({"platform": "mt5", "login": "1"}, by="r")
    with pytest.raises(DeployError):
        store.upsert_account({"agent": "a", "platform": "mt5"}, by="r")
    a = _acc(store)
    z = store.upsert_account({"id": a["id"], "label": "Nový názov", "portable": True}, by="rasto")
    assert z["label"] == "Nový názov" and z["portable"] is True and z["login"] == "5012345"
    assert store.upsert_account({"id": a["id"]}, by="r") == z    # nič na zmenu = nič sa nestane
    with pytest.raises(DeployError):
        store.upsert_account({"id": a["id"], "login": ""}, by="r")
    akcie = [x["action"] for x in store.audit()]
    assert akcie[:2] == ["account_update", "account_create"]
    assert store.audit()[0]["old"] == {"label": "IC Markets Demo", "portable": False}


def test_identita_uctu_podla_platformy():
    assert account_identity({"platform": "mt5", "login": "5012345", "server": "ICMarkets-Demo"}) == "5012345-ICMarkets-Demo"
    assert account_identity({"platform": "ninjatrader", "login": "Sim101", "server": "NinjaTrader Continuum"}) == "Sim101"
    assert account_identity({"platform": "cokolvek", "login": "x"}) == "x"


# --------------------------------------------------------------------------- #
# nasadenia
# --------------------------------------------------------------------------- #


def test_nasadenie_hash_instancia_a_config_z_profilu(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsninja", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="rasto")
    assert d["strategy"] == "ibsnet"                                  # alias → dnešný kľúč
    assert d["instance"] == instance_id("mt5", "5012345-ICMarkets-Demo", "NAS100", 3, "ibsnet")
    assert d["config"] == _resolver("ibsnet", "p1") and d["config_hash"] == config_hash(d["config"])
    assert d["mode"] == "paused" and d["active"] is True and d["applied"] is None and d["agent"] == "trade-pc"   # štartuje pauznuté
    assert len(d["id"]) == 12
    # výslovný režim sa rešpektuje
    z = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 5, "profile": "p1",
                                 "mode": "enabled"}, by="r")
    assert z["mode"] == "enabled"
    # hash je kanonický: poradie kľúčov nehrá rolu
    assert config_hash({"b": 1, "a": [1, 2]}) == config_hash({"a": [1, 2], "b": 1})
    # hotový config má prednosť pred profilom
    e = store.create_deployment({"account": a["id"], "strategy": "orbnet", "symbol": "NAS100", "tf": 3,
                                 "profile": "p1", "config": {"x": 1}}, by="r")
    assert e["config"] == {"x": 1} and e["config_hash"] == config_hash({"x": 1})
    assert [x["id"] for x in store.deployments(agent="trade-pc")] == [d["id"], z["id"], e["id"]]
    assert store.deployments(account="nie") == [] and store.deployment("nie") is None


def test_nasadenie_validacia(store: DeployStore):
    a = _acc(store)
    base = {"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}
    with pytest.raises(DeployError):
        store.create_deployment({**base, "strategy": "cudzia"}, by="r")
    with pytest.raises(DeployError):
        store.create_deployment({**base, "symbol": ""}, by="r")
    with pytest.raises(DeployError):
        store.create_deployment({**base, "tf": 0}, by="r")
    with pytest.raises(DeployError):
        store.create_deployment({**base, "mode": "off"}, by="r")
    with pytest.raises(DeployError):
        store.create_deployment({**base, "profile": "neexistuje"}, by="r")
    with pytest.raises(DeployError):
        store.create_deployment({**base, "profile": ""}, by="r")
    with pytest.raises(NotFound):
        store.create_deployment({**base, "account": "nie"}, by="r")
    store.create_deployment(base, by="r")
    with pytest.raises(Conflict):                                    # tá istá inštancia dvakrát
        store.create_deployment({**base, "profile": "p2"}, by="r")


def test_update_meni_len_mode_profil_a_active(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    store.clock.t = 2000.0
    u = store.update_deployment(d["id"], {"mode": "enabled"}, by="rasto")     # nové je paused → zapnutie je zmena
    assert u["mode"] == "enabled" and u["updated"] == 2000.0 and u["config_hash"] == d["config_hash"]
    u = store.update_deployment(d["id"], {"profile": "p2"}, by="rasto")
    assert u["profile"] == "p2" and u["config"]["rrRatio"] == 2.5 and u["config_hash"] != d["config_hash"]
    u = store.update_deployment(d["id"], {"config": {"rrRatio": 9.0}}, by="rasto")   # hotový config, profil ostáva
    assert u["profile"] == "p2" and u["config"] == {"rrRatio": 9.0}
    u = store.update_deployment(d["id"], {"active": False}, by="rasto")
    assert u["active"] is False
    for zle in ({"symbol": "ES"}, {"tf": 5}, {"strategy": "orbnet"}, {"account": "x"}):
        with pytest.raises(DeployError):
            store.update_deployment(d["id"], zle, by="r")
    with pytest.raises(DeployError):
        store.update_deployment(d["id"], {"mode": "zle"}, by="r")
    with pytest.raises(NotFound):
        store.update_deployment("nie", {"mode": "paused"}, by="r")
    # rovnaká hodnota = žiadna zmena ani audit
    n = len(store.audit())
    assert store.update_deployment(d["id"], {"mode": "enabled"}, by="r")["updated"] == u["updated"]
    assert len(store.audit()) == n
    zaznam = [x for x in store.audit() if x["action"] == "deployment_update"]
    assert zaznam[-1]["old"] == {"mode": "paused"} and zaznam[-1]["new"] == {"mode": "enabled"} and zaznam[-1]["by"] == "rasto"


# --------------------------------------------------------------------------- #
# agent: desired / applied / heslo
# --------------------------------------------------------------------------- #


def test_heslo_odide_agentovi_raz_a_po_potvrdeni_zmizne(store: DeployStore):
    a = store.upsert_account({"agent": "trade-pc", "platform": "mt5", "label": "IC", "login": "1", "server": "S"},
                             by="r", password="tajne")
    b = store.upsert_account({"agent": "iny-pc", "platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")

    want = store.desired_for_agent("trade-pc")
    assert [x["id"] for x in want["accounts"]] == [a["id"]] and want["accounts"][0]["secret"] == "tajne"
    assert [x["id"] for x in want["deployments"]] == [d["id"]] and want["deployments"][0]["config"] == d["config"]
    iny = store.desired_for_agent("iny-pc")
    assert [x["id"] for x in iny["accounts"]] == [b["id"]] and "secret" not in iny["accounts"][0] and iny["deployments"] == []
    assert store.desired_for_agent("nikto") == {"accounts": [], "deployments": []}

    # cudzí agent heslo nepotvrdí (a cudzie applied sa ignoruje)
    assert store.report_applied("iny-pc", [{"deployment": d["id"], "status": "ok"}], secret_ack=[a["id"]]) == 0
    assert store.desired_for_agent("trade-pc")["accounts"][0]["secret"] == "tajne"
    assert store.deployment(d["id"])["applied"] is None

    n = store.report_applied("trade-pc", [{"deployment": d["id"], "config_hash": d["config_hash"], "mode": "enabled",
                                           "status": "ok"}, {"deployment": "nie-je"}, {}], secret_ack=[a["id"]])
    assert n == 1
    assert "secret" not in store.desired_for_agent("trade-pc")["accounts"][0]
    assert store.account(a["id"])["secret_pending"] is False
    ap = store.deployment(d["id"])["applied"]
    assert ap["agent"] == "trade-pc" and ap["status"] == "ok" and ap["config_hash"] == d["config_hash"] and ap["ts"] == 1000.0
    assert [x["action"] for x in store.audit()][0] == "secret_taken"

    # nové heslo → znova čaká; neznámy stav → error; opakované hlásenie prepíše
    store.upsert_account({"id": a["id"]}, by="r", password="nove")
    assert store.desired_for_agent("trade-pc")["accounts"][0]["secret"] == "nove"
    store.report_applied("trade-pc", [{"deployment": d["id"], "status": "divny", "error": "x" * 900}])
    ap = store.deployment(d["id"])["applied"]
    assert ap["status"] == "error" and len(ap["error"]) == 500


def test_desired_nesie_aj_neaktivne_nasadenia(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    store.update_deployment(d["id"], {"active": False}, by="r")
    deps = store.desired_for_agent("trade-pc")["deployments"]
    assert [(x["id"], x["active"]) for x in deps] == [(d["id"], False)]


# --------------------------------------------------------------------------- #
# mazanie
# --------------------------------------------------------------------------- #


def test_mazanie_nasadenia_najprv_vypne_potom_zmaze_po_potvrdeni(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    store.report_applied("trade-pc", [{"deployment": d["id"], "config_hash": d["config_hash"], "mode": "enabled", "status": "ok"}])
    store.clock.t = 2000.0
    assert store.delete_deployment(d["id"], by="rasto") == {"id": d["id"], "deleted": False, "active": False}
    assert store.deployment(d["id"])["active"] is False
    # agent to ešte nepotvrdil (applied je spred deaktivácie) → stále len vypnuté
    assert store.delete_deployment(d["id"], by="rasto")["deleted"] is False
    store.clock.t = 3000.0
    store.report_applied("trade-pc", [{"deployment": d["id"], "status": "removed"}])
    assert store.delete_deployment(d["id"], by="rasto")["deleted"] is True
    assert store.deployment(d["id"]) is None
    with pytest.raises(NotFound):
        store.delete_deployment(d["id"], by="r")
    akcie = [x["action"] for x in store.audit()]
    assert akcie[0] == "deployment_delete" and "deployment_update" in akcie


def test_mazanie_nasadenia_ktore_agent_nikdy_nevidel_a_force(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    e = store.create_deployment({"account": a["id"], "strategy": "orbnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    # bez applied: prvé volanie vypne, druhé zmaže (na platforme z toho nič nie je)
    assert store.delete_deployment(d["id"], by="r")["deleted"] is False
    assert store.delete_deployment(d["id"], by="r")["deleted"] is True
    # force maže hneď, aj aktívne s applied
    store.report_applied("trade-pc", [{"deployment": e["id"], "status": "ok"}])
    assert store.delete_deployment(e["id"], by="r", force=True)["deleted"] is True
    assert store.deployments() == []
    raw = sqlite3.connect(str(store.path)).execute("SELECT COUNT(*) FROM applied").fetchone()[0]
    assert raw == 0


def test_mazanie_uctu_s_nasadeniami_len_s_force(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    with pytest.raises(Conflict):
        store.delete_account(a["id"], by="r")
    out = store.delete_account(a["id"], by="r", force=True)
    assert out == {"id": a["id"], "deleted": True, "deployments": [d["id"]]}
    assert store.accounts() == [] and store.deployments() == []
    with pytest.raises(NotFound):
        store.delete_account(a["id"], by="r")
    b = _acc(store, label="x")
    assert store.delete_account(b["id"], by="r")["deployments"] == []


def test_zmena_loginu_prepocita_instancie(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    store.upsert_account({"id": a["id"], "server": "ICMarkets-Live"}, by="r")
    assert store.deployment(d["id"])["instance"] == instance_id("mt5", "5012345-ICMarkets-Live", "NAS100", 3, "ibsnet")


# --------------------------------------------------------------------------- #
# spolužitie s LiveStore v jednom súbore
# --------------------------------------------------------------------------- #


def test_zdiela_subor_s_livestore(tmp_path: Path):
    path = tmp_path / "live.sqlite"
    live = LiveStore(path)
    dep = DeployStore(path, config_resolver=_resolver, strategy_check=lambda k: k)
    a = dep.upsert_account({"agent": "a", "platform": "mt5", "label": "x", "login": "1", "server": "s"}, by="r")
    live.ingest("a", "mt5_1-s_NAS100_3m_ibsnet", "s1", [{"seq": 1, "t": 1, "k": "note", "text": "hi"}])
    assert [i["id"] for i in live.instances()] == ["mt5_1-s_NAS100_3m_ibsnet"]
    assert dep.accounts()[0]["id"] == a["id"]
    assert dep.counts() == {"accounts": 1, "deployments": 0}
    tabulky = {r[0] for r in sqlite3.connect(str(path)).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"instances", "events", "accounts", "deployments", "audit", "applied"} <= tabulky


def test_predvoleny_resolver_berie_profil_z_repozitara(tmp_path: Path):
    """Bez podstrčeného resolvera ide config z profilu repozitára stratégie (aj cez webapp)."""
    st = DeployStore(tmp_path / "live.sqlite")
    a = st.upsert_account({"agent": "a", "platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    d = st.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "MNQ 12-26", "tf": 3,
                              "profile": "multicharts_mnq_3m"}, by="r")
    # NT: do id ide `MasterInstrument.Name` (`MNQ`), nie celý názov `MNQ 12-26` — tak ho počíta AddOn
    # (`LiveSpool.InstanceId`), inak by control súbor z hubu nikdy nečítal.
    assert d["instance"] == "ninjatrader_Sim101_MNQ_3m_ibsnet"
    assert d["config"] and "rrRatio" in d["config"]
    with pytest.raises(DeployError):
        st.create_deployment({"account": a["id"], "strategy": "nie", "symbol": "X", "tf": 1, "profile": "p"}, by="r")


def test_instance_symbol_ninjatrader_berie_master_name():
    """NT: id inštancie počíta AddOn z `MasterInstrument.Name` — hub aj driver musia dať to isté."""
    from tradebot.live.schema import instance_id, instance_symbol

    assert instance_symbol("ninjatrader", "MNQ 12-26") == "MNQ"
    assert instance_symbol("ninjatrader", "  ES 03-27 ") == "ES"
    assert instance_symbol("ninjatrader", "MNQ") == "MNQ"
    assert instance_symbol("mt5", "US100.cash") == "US100.cash"
    assert instance_symbol("mt5", "NAS100 x") == "NAS100 x"   # iná platforma sa nemení
    assert (instance_id("ninjatrader", "Sim101", instance_symbol("ninjatrader", "MNQ 12-26"), 3, "ibsnet")
            == "ninjatrader_Sim101_MNQ_3m_ibsnet")


def test_instance_sa_prepocita_pri_starte_storu(tmp_path: Path):
    """`instance` je odvodený stĺpec: riadok uložený podľa starého pravidla (`…_MNQ-12-26_…`) sa pri
    ďalšom otvorení storu dorovná na to, čo počíta platforma (`…_MNQ_…`)."""
    import sqlite3

    st = DeployStore(tmp_path / "live.sqlite")
    a = st.upsert_account({"agent": "a", "platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    d = st.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "MNQ 12-26", "tf": 3,
                              "profile": "multicharts_mnq_3m"}, by="r")
    with sqlite3.connect(tmp_path / "live.sqlite") as c:
        c.execute("UPDATE deployments SET instance = ? WHERE id = ?", ("ninjatrader_Sim101_MNQ-12-26_3m_ibsnet", d["id"]))
    st2 = DeployStore(tmp_path / "live.sqlite")
    assert st2.deployment(d["id"])["instance"] == "ninjatrader_Sim101_MNQ_3m_ibsnet"
