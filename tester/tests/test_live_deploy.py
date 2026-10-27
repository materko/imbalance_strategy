"""`tradebot.live.deploy.DeployStore`: účty (bez stroja), nasadenia (so strojom a terminálom), hash
configu, id inštancie, šifrované heslo doručené každému stroju raz za verziu (`desired_for_agent` →
`report_applied(secret_ack)`), verzia prihlásenia `rev`, migrácia účtov viazaných na stroj, audit
a pravidlá mazania — všetko bez siete, nad sqlite v dočasnom adresári."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tradebot.live.deploy import Conflict, DeployError, DeployStore, NotFound, account_identity, config_hash
from tradebot.live.schema import instance_id
from tradebot.live.store import LiveStore
from tradebot.live.vault import Vault, VaultError


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
                       vault=Vault(key=b"k" * 32),
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
    a = store.upsert_account({"platform": "mt5", "label": "IC Markets Demo", "login": "5012345",
                              "server": "ICMarkets-Demo"}, by="rasto", password="tajne-heslo")
    assert a["id"] == "ic-markets-demo" and a["by"] == "rasto" and "agent" not in a and "terminal" not in a
    assert a["secret"] is True and a["secret_waiting"] == [] and a["secret_pending"] is False   # nikto ho zatiaľ nepoužíva
    assert "tajne" not in json.dumps(a)
    b = store.upsert_account({"platform": "mt5", "label": "IC Markets Demo", "login": "9"}, by="x")
    assert b["id"] == "ic-markets-demo-2" and b["secret"] is False
    assert [x["id"] for x in store.accounts()] == ["ic-markets-demo", "ic-markets-demo-2"]
    assert store.accounts(agent="iny") == [] and store.account("nie") is None
    # heslo nie je v žiadnom zozname ani v databáze čitateľne — len šifrované
    assert "tajne" not in json.dumps(store.accounts())
    raw = sqlite3.connect(str(store.path)).execute(
        "SELECT secret_enc, secret_pending FROM accounts WHERE id = 'ic-markets-demo'").fetchone()
    assert raw[1] is None and raw[0].startswith("v1:") and "tajne" not in raw[0]
    assert store.vault.decrypt(raw[0]) == "tajne-heslo"


def test_ucet_povinne_polia_platforma_a_zmena(store: DeployStore):
    with pytest.raises(DeployError):
        store.upsert_account({"platform": "cokolvek", "login": "1"}, by="r")      # len MT5 a NinjaTrader
    with pytest.raises(DeployError):
        store.upsert_account({"platform": "mt5"}, by="r")
    a = _acc(store)
    rev = a["rev"]
    z = store.upsert_account({"id": a["id"], "label": "Nový názov", "portable": True}, by="rasto")
    assert z["label"] == "Nový názov" and z["login"] == "5012345" and "portable" not in z
    assert z["rev"] == rev                                              # názov nie je prihlásenie
    assert store.upsert_account({"id": a["id"]}, by="r") == z    # nič na zmenu = nič sa nestane
    assert store.upsert_account({"id": a["id"], "label": "Nový názov"}, by="r") == z
    with pytest.raises(DeployError):
        store.upsert_account({"id": a["id"], "login": ""}, by="r")
    akcie = [x["action"] for x in store.audit()]
    assert akcie[:2] == ["account_update", "account_create"]
    assert store.audit()[0]["old"] == {"label": "IC Markets Demo"}
    # NinjaTrader heslo nemá — ani pri založení, ani pri zmene sa neuloží
    nt = store.upsert_account({"platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r", password="x")
    assert nt["secret"] is False
    assert store.upsert_account({"id": nt["id"]}, by="r", password="y")["secret"] is False


def test_rev_sa_meni_s_prihlasenim(store: DeployStore):
    a = _acc(store)
    b = store.upsert_account({"id": a["id"], "server": "ICMarkets-Live"}, by="r")
    assert b["rev"] and b["rev"] != a["rev"]
    c = store.upsert_account({"id": a["id"]}, by="r", password="nove")
    assert c["rev"] != b["rev"] and c["secret"] is True
    assert store.audit()[0]["new"] == {"password": True}


def test_platforma_uctu_s_nasadeniami_sa_nemeni(store: DeployStore):
    a = _acc(store)
    store.create_deployment({"account": a["id"], "agent": "pc", "strategy": "ibsnet", "symbol": "NAS100", "tf": 3,
                             "profile": "p1"}, by="r")
    with pytest.raises(Conflict):
        store.upsert_account({"id": a["id"], "platform": "ninjatrader"}, by="r")
    b = _acc(store, label="b")
    assert store.upsert_account({"id": b["id"], "platform": "ninjatrader"}, by="r", password="x")["platform"] == "ninjatrader"


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


def test_viac_strategii_na_jednom_ucte_a_symbole(store: DeployStore):
    """docs/MT5.md „Viac stratégií na jednom serveri“: iná stratégia na tom istom účte, symbole a TF je iná
    inštancia (vlastný control a spool); tá istá stratégia znova na inom symbole alebo TF tiež."""
    a = _acc(store)
    base = {"account": a["id"], "symbol": "NAS100", "tf": 3, "profile": "p1"}
    ibs = store.create_deployment({**base, "strategy": "ibsnet"}, by="r")
    orb = store.create_deployment({**base, "strategy": "orbnet"}, by="r")
    ibs5 = store.create_deployment({**base, "strategy": "ibsnet", "tf": 5}, by="r")
    assert len({ibs["instance"], orb["instance"], ibs5["instance"]}) == 3
    assert orb["instance"] == instance_id("mt5", "5012345-ICMarkets-Demo", "NAS100", 3, "orbnet")
    assert [d["agent"] for d in store.desired_for_agent("trade-pc")["deployments"]] == ["trade-pc"] * 3


def test_ta_ista_instancia_na_inom_stroji_povie_kde_bezi_a_ako_presunut(store: DeployStore):
    """Inštancia nepozná stroj: ten istý účet + stratégia + symbol + TF na druhom stroji je kolízia a chyba
    povie, kde beží a čo s tým (presun = odstrániť tam, zmazať, nasadiť tu)."""
    a = _acc(store)
    base = {"account": a["id"], "strategy": "orbnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}
    d = store.create_deployment({**base, "agent": "nb-rasto"}, by="r")
    with pytest.raises(Conflict, match=r"orbnet NAS100 3m na tomto účte už beží na stroji nb-rasto .*profil p1.*"
                                       r"na presun na stroj nas-win11 ho najprv .*odstráň"):
        store.create_deployment({**base, "agent": "nas-win11", "profile": "p2"}, by="r")
    with pytest.raises(Conflict, match=r"už beží na stroji nb-rasto .*iný profil mu zmeníš"):
        store.create_deployment({**base, "agent": "nb-rasto", "profile": "p2"}, by="r")
    store.delete_deployment(d["id"], by="r")                          # odstrániť: agent ho zastaví
    with pytest.raises(Conflict, match=r"je odstránené na stroji nb-rasto .*zmaž"):
        store.create_deployment({**base, "agent": "nas-win11"}, by="r")
    assert store.delete_deployment(d["id"], by="r")["deleted"] is True  # zmazať (agent ho nikdy nevidel)
    assert store.create_deployment({**base, "agent": "nas-win11"}, by="r")["agent"] == "nas-win11"


def test_slot_dovoli_tu_istu_strategiu_s_inym_profilom(store: DeployStore):
    """Slot (docs/MT5.md): druhé nasadenie tej istej stratégie na účte, symbole a TF s iným profilom — iná inštancia
    `…_orbnet_b`; slot je identita (nemení sa), vie ho len MT5 a chyba pri kolízii ho poradí."""
    a = _acc(store)
    base = {"account": a["id"], "agent": "nas-win11", "strategy": "orbnet", "symbol": "NAS100", "tf": 3}
    prvy = store.create_deployment({**base, "profile": "p1"}, by="r")
    with pytest.raises(Conflict, match=r"zadaj nasadeniu slot"):
        store.create_deployment({**base, "profile": "p2"}, by="r")
    druhy = store.create_deployment({**base, "profile": "p2", "slot": "b"}, by="r")
    assert druhy["slot"] == "b" and druhy["instance"] == prvy["instance"] + "_b"
    assert druhy["instance"] == instance_id("mt5", "5012345-ICMarkets-Demo", "NAS100", 3, "orbnet", "b")
    with pytest.raises(Conflict, match=r"slot b na tomto účte už beží"):
        store.create_deployment({**base, "profile": "p1", "slot": "b"}, by="r")
    for zly in ("a_b", "x" * 17, "č"):
        with pytest.raises(DeployError, match="slot"):
            store.create_deployment({**base, "slot": zly, "profile": "p1"}, by="r")
    with pytest.raises(DeployError):
        store.update_deployment(druhy["id"], {"slot": "c"}, by="r")
    nt = store.upsert_account({"platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    with pytest.raises(DeployError, match="slot vie len MetaTrader 5"):
        store.create_deployment({**base, "account": nt["id"], "slot": "b", "profile": "p1"}, by="r")
    agent = store.desired_for_agent("nas-win11")["deployments"]
    assert sorted(d["slot"] for d in agent) == ["", "b"]


def test_vlastny_terminal_nema_terminal_uctu_a_neblokuje_spolocny(store: DeployStore):
    """`own_terminal`: nasadenie ide do vlastnej portable kópie — terminál/portable sa mu neukladá, pravidlo „jeden
    spoločný terminál účtu na stroji“ sa ho netýka a terminál účtu v heartbeate určujú len spoločné nasadenia."""
    a = _acc(store)
    base = {"account": a["id"], "agent": "nas-win11", "symbol": "NAS100", "tf": 3, "profile": "p1"}
    own = store.create_deployment({**base, "strategy": "orbnet", "own_terminal": True, "terminal": "C:\\X\\terminal64.exe"}, by="r")
    assert own["own_terminal"] is True and own["terminal"] == "" and own["portable"] is False
    spol = store.create_deployment({**base, "strategy": "ibsnet", "terminal": "C:\\MT5\\terminal64.exe"}, by="r")
    store.create_deployment({**base, "strategy": "ibsnet", "tf": 5, "own_terminal": True}, by="r")
    with pytest.raises(Conflict, match="do toho istého"):
        store.create_deployment({**base, "strategy": "ibsnet", "tf": 15}, by="r")   # spoločný: iný terminál nejde
    acc = store.desired_for_agent("nas-win11")["accounts"][0]
    assert acc["terminal"] == spol["terminal"] == "C:\\MT5\\terminal64.exe"
    with pytest.raises(DeployError):
        store.update_deployment(own["id"], {"own_terminal": False}, by="r")


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


def test_heslo_dostane_kazdy_stroj_s_nasadenim_raz_za_verziu(store: DeployStore):
    a = store.upsert_account({"platform": "mt5", "label": "IC", "login": "1", "server": "S"}, by="r", password="tajne")
    store.upsert_account({"platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    d = store.create_deployment({"account": a["id"], "agent": "trade-pc", "strategy": "ibsnet", "symbol": "NAS100",
                                 "tf": 3, "profile": "p1"}, by="r")
    assert store.account(a["id"])["secret_waiting"] == ["trade-pc"]

    want = store.desired_for_agent("trade-pc")
    assert [x["id"] for x in want["accounts"]] == [a["id"]] and want["accounts"][0]["secret"] == "tajne"
    assert want["accounts"][0]["rev"] == store.account(a["id"])["rev"] and "agent" not in want["accounts"][0]
    assert [x["id"] for x in want["deployments"]] == [d["id"]] and want["deployments"][0]["config"] == d["config"]
    # účet bez nasadenia na stroji stroj nedostane
    assert store.desired_for_agent("iny-pc") == {"accounts": [], "deployments": []}
    assert [x["id"] for x in store.desired_for_agent("trade-pc")["accounts"]] == [a["id"]]   # nie `b`

    # cudzí agent heslo nepotvrdí (a cudzie applied sa ignoruje)
    assert store.report_applied("iny-pc", [{"deployment": d["id"], "status": "ok"}], secret_ack=[a["id"]]) == 0
    assert store.desired_for_agent("trade-pc")["accounts"][0]["secret"] == "tajne"
    assert store.deployment(d["id"])["applied"] is None

    n = store.report_applied("trade-pc", [{"deployment": d["id"], "config_hash": d["config_hash"], "mode": "enabled",
                                           "status": "ok"}, {"deployment": "nie-je"}, {}], secret_ack=[a["id"]])
    assert n == 1
    assert "secret" not in store.desired_for_agent("trade-pc")["accounts"][0]
    assert store.account(a["id"])["secret_pending"] is False and store.account(a["id"])["secret"] is True
    ap = store.deployment(d["id"])["applied"]
    assert ap["agent"] == "trade-pc" and ap["status"] == "ok" and ap["config_hash"] == d["config_hash"] and ap["ts"] == 1000.0
    assert [x["action"] for x in store.audit()][0] == "secret_taken"

    # ten istý účet na druhom stroji: heslo dostane aj on (hub ho drží), prvý už nie
    e = store.create_deployment({"account": a["id"], "agent": "iny-pc", "strategy": "ibsnet", "symbol": "NAS100",
                                 "tf": 5, "profile": "p1"}, by="r")
    assert store.account(a["id"])["secret_waiting"] == ["iny-pc"]
    iny = store.desired_for_agent("iny-pc")
    assert iny["accounts"][0]["secret"] == "tajne" and [x["id"] for x in iny["deployments"]] == [e["id"]]
    store.report_applied("iny-pc", [], secret_ack=[a["id"]])
    assert store.account(a["id"])["secret_waiting"] == []

    # nové heslo → znova čaká na oboch strojoch; neznámy stav → error; opakované hlásenie prepíše
    store.upsert_account({"id": a["id"]}, by="r", password="nove")
    assert store.account(a["id"])["secret_waiting"] == ["iny-pc", "trade-pc"]
    assert store.desired_for_agent("trade-pc")["accounts"][0]["secret"] == "nove"
    store.report_applied("trade-pc", [{"deployment": d["id"], "status": "divny", "error": "x" * 900}])
    ap = store.deployment(d["id"])["applied"]
    assert ap["status"] == "error" and len(ap["error"]) == 500


def test_heslo_s_inym_klucom_sa_nedoruci(tmp_path: Path):
    st = DeployStore(tmp_path / "live.sqlite", config_resolver=_resolver, strategy_check=lambda k: k,
                     vault=Vault(key=b"a" * 32))
    a = st.upsert_account({"platform": "mt5", "label": "IC", "login": "1", "server": "S"}, by="r", password="tajne")
    st.create_deployment({"account": a["id"], "agent": "pc", "strategy": "ibsnet", "symbol": "X", "tf": 3,
                          "profile": "p"}, by="r")
    st2 = DeployStore(tmp_path / "live.sqlite", config_resolver=_resolver, strategy_check=lambda k: k,
                      vault=Vault(key=b"b" * 32))
    acc = st2.desired_for_agent("pc")["accounts"][0]
    assert "secret" not in acc and "nedá rozšifrovať" in acc["secret_error"]


def test_vault_kluc_v_subore_a_overenie(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADEBOT_HUB_SECRET_KEY", raising=False)
    v = Vault(tmp_path / "secret.key")
    blob = v.encrypt("heslo s diakritikou ľščť")
    assert (tmp_path / "secret.key").exists() and blob.startswith("v1:")
    assert v.encrypt("heslo s diakritikou ľščť") != blob                # náhodný nonce
    assert Vault(tmp_path / "secret.key").decrypt(blob) == "heslo s diakritikou ľščť"
    pokazeny = blob[:-6] + ("A" if blob[-6] != "A" else "B") + blob[-5:]
    with pytest.raises(VaultError):
        v.decrypt(pokazeny)
    with pytest.raises(VaultError):
        Vault(key=b"z" * 32).decrypt(blob)
    monkeypatch.setenv("TRADEBOT_HUB_SECRET_KEY", "11" * 32)
    assert Vault(tmp_path / "iny.key").decrypt(Vault(key=bytes.fromhex("11" * 32)).encrypt("x")) == "x"
    assert not (tmp_path / "iny.key").exists()


def test_terminal_mt5_je_v_nasadeni_a_jeden_na_ucet_a_stroj(store: DeployStore):
    a = _acc(store)
    base = {"account": a["id"], "agent": "pc", "strategy": "ibsnet", "symbol": "NAS100", "profile": "p1"}
    d = store.create_deployment({**base, "tf": 3, "terminal": r"C:\MT5\terminal64.exe", "portable": True}, by="r")
    assert d["terminal"] == r"C:\MT5\terminal64.exe" and d["portable"] is True and d["agent"] == "pc"
    acc = store.desired_for_agent("pc")["accounts"][0]
    assert acc["terminal"] == r"C:\MT5\terminal64.exe" and acc["portable"] is True
    with pytest.raises(Conflict):                                    # iný terminál pre ten istý účet na tom stroji
        store.create_deployment({**base, "tf": 5}, by="r")
    store.create_deployment({**base, "tf": 5, "terminal": r"C:\MT5\terminal64.exe", "portable": True}, by="r")
    store.create_deployment({**base, "tf": 15, "agent": "iny"}, by="r")          # iný stroj, iný terminál
    with pytest.raises(DeployError):
        store.update_deployment(d["id"], {"agent": "iny"}, by="r")
    bez = store.upsert_account({"platform": "mt5", "label": "bez stroja", "login": "7", "server": "S"}, by="r")
    with pytest.raises(DeployError, match="stroj"):                  # stroj je povinný (účet žiadny nemá)
        store.create_deployment({**base, "account": bez["id"], "tf": 30, "agent": ""}, by="r")
    # NinjaTrader terminál nemá — pole sa ignoruje
    nt = store.upsert_account({"platform": "ninjatrader", "label": "NT", "login": "Sim101"}, by="r")
    e = store.create_deployment({**base, "account": nt["id"], "tf": 3, "terminal": "x", "portable": True}, by="r")
    assert e["terminal"] == "" and e["portable"] is False


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


def test_ucet_sa_neda_zmazat_ked_na_nom_nieco_bezi(store: DeployStore):
    a = _acc(store)
    d = store.create_deployment({"account": a["id"], "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"}, by="r")
    for force in (False, True):                                      # ani force aktívne nasadenia neprebije
        with pytest.raises(Conflict, match="ešte beží: ibsnet NAS100 3m na trade-pc"):
            store.delete_account(a["id"], by="r", force=force)
    store.update_deployment(d["id"], {"active": False}, by="r")      # odstránené (čaká na potvrdenie agentom)
    out = store.delete_account(a["id"], by="r")
    assert out == {"id": a["id"], "deleted": True, "deployments": [d["id"]]}
    assert store.accounts() == [] and store.deployments() == []
    with pytest.raises(NotFound):
        store.delete_account(a["id"], by="r")
    b = _acc(store, label="x")
    assert store.delete_account(b["id"], by="r")["deployments"] == []


def test_migracia_uctu_viazaneho_na_stroj(tmp_path: Path):
    """Starý súbor: účet so strojom, terminálom a čitateľným `secret_pending`. Nasadenia zdedia stroj aj
    terminál (agent dostane to isté ako doteraz), heslo sa zašifruje a doručí znova."""
    path = tmp_path / "live.sqlite"
    with sqlite3.connect(str(path)) as c:
        c.executescript("""
        CREATE TABLE accounts (id TEXT PRIMARY KEY, agent TEXT NOT NULL, platform TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '', login TEXT NOT NULL DEFAULT '', server TEXT NOT NULL DEFAULT '',
            terminal TEXT NOT NULL DEFAULT '', portable INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
            updated REAL NOT NULL, by TEXT NOT NULL DEFAULT '', secret_pending TEXT);
        CREATE TABLE deployments (id TEXT PRIMARY KEY, account TEXT NOT NULL, strategy TEXT NOT NULL,
            symbol TEXT NOT NULL, tf INTEGER NOT NULL, profile TEXT NOT NULL DEFAULT '', config TEXT NOT NULL DEFAULT '{}',
            config_hash TEXT NOT NULL DEFAULT '', mode TEXT NOT NULL DEFAULT 'enabled', active INTEGER NOT NULL DEFAULT 1,
            instance TEXT NOT NULL DEFAULT '', created REAL NOT NULL, updated REAL NOT NULL, by TEXT NOT NULL DEFAULT '');
        INSERT INTO accounts VALUES ('ic', 'trade-pc', 'mt5', 'IC', '1', 'S', 'C:\\MT5', 1, 1, 1, 'r', 'tajne');
        INSERT INTO accounts VALUES ('nt', 'nas-win11', 'ninjatrader', 'NT', 'Sim101', '', '', 0, 1, 1, 'r', NULL);
        INSERT INTO deployments VALUES ('d1', 'ic', 'ibsnet', 'NAS100', 3, 'p1', '{}', 'h', 'enabled', 1,
            'mt5_1-S_NAS100_3m_ibsnet', 1, 1, 'r');
        INSERT INTO deployments VALUES ('d2', 'nt', 'ibsnet', 'MNQ 12-26', 3, 'p1', '{}', 'h', 'enabled', 1,
            'ninjatrader_Sim101_MNQ_3m_ibsnet', 1, 1, 'r');
        """)
    st = DeployStore(path, config_resolver=_resolver, strategy_check=lambda k: k, vault=Vault(key=b"k" * 32))
    assert st.deployment("d1")["agent"] == "trade-pc" and st.deployment("d2")["agent"] == "nas-win11"
    assert st.deployment("d1")["terminal"] == "C:\\MT5" and st.deployment("d1")["portable"] is True
    want = st.desired_for_agent("trade-pc")
    assert want["accounts"][0] == {"id": "ic", "platform": "mt5", "label": "IC", "login": "1", "server": "S", "rev": "",
                                   "terminal": "C:\\MT5", "portable": True, "secret": "tajne"}
    nt = st.desired_for_agent("nas-win11")
    assert nt["accounts"] == [{"id": "nt", "platform": "ninjatrader", "label": "NT", "login": "Sim101", "server": "",
                               "rev": "", "terminal": "", "portable": False}]
    assert [d["instance"] for d in nt["deployments"]] == ["ninjatrader_Sim101_MNQ_3m_ibsnet"]
    raw = sqlite3.connect(str(path)).execute("SELECT secret_pending, secret_enc FROM accounts WHERE id = 'ic'").fetchone()
    assert raw[0] is None and "tajne" not in raw[1]
    # druhé otvorenie nič nemení
    st2 = DeployStore(path, config_resolver=_resolver, strategy_check=lambda k: k, vault=Vault(key=b"k" * 32))
    assert st2.deployment("d1")["terminal"] == "C:\\MT5" and st2.account("ic")["secret"] is True


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
    a = dep.upsert_account({"platform": "mt5", "label": "x", "login": "1", "server": "s"}, by="r")
    live.ingest("a", "mt5_1-s_NAS100_3m_ibsnet", "s1", [{"seq": 1, "t": 1, "k": "note", "text": "hi"}])
    assert [i["id"] for i in live.instances()] == ["mt5_1-s_NAS100_3m_ibsnet"]
    assert dep.accounts()[0]["id"] == a["id"]
    assert dep.counts() == {"accounts": 1, "deployments": 0}
    tabulky = {r[0] for r in sqlite3.connect(str(path)).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"instances", "events", "accounts", "deployments", "audit", "applied", "secret_sent"} <= tabulky


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


def test_nasadenie_prepocita_prahy_v_tickoch_na_body_nastroja_ladenia():
    """25. 10. 2026: profil z MNQ (tick 0,25) na MT5 US100.cash (tick 0,01) — ticky sa pri nasadení prepočítajú na body."""
    from tradebot.live.deploy import ticks_to_points
    cfg = {"imbMaxDistTicks": 40.0, "state2ConfirmTicks": {"value": 6.0, "unit": "ticks"}, "pbMinRangePoints": 4.0,
           "minImbSizePoints": {"value": 0.3, "unit": "atr"}, "rrRatio": 0.5}
    out = ticks_to_points("ibsentrynet", cfg, "mnq_databento")
    assert out["imbMaxDistTicks"] == {"value": 10.0, "unit": "abs"}
    assert out["state2ConfirmTicks"] == {"value": 1.5, "unit": "abs"}
    assert out["pbMinRangePoints"] == 4.0 and out["minImbSizePoints"] == {"value": 0.3, "unit": "atr"}
    assert out["_instrument"] == "mnq_databento"
    assert ticks_to_points("ibsentrynet", cfg, None) is cfg      # bez nástroja ladenia bez zmeny
