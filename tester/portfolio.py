"""Portfólio z viacerých behov: jedna krivka kapitálu, korelácie a cena rizika.

### Na akú otázku odpovedá
„Koľko sa na tom dá zarobiť?" je otázka, na ktorú jeden beh odpovedať nevie — a nie preto,
že by chýbali dáta, ale preto, že odpoveď závisí od dvoch vecí, ktoré beh nedrží:
**koľko riskuješ na obchod** a **čo všetko obchoduješ naraz**.

Tento modul preto vezme vybrané behy, prepočíta ich na spoločný účet a povie:

- **cena rizika** — tabuľka „riziko na obchod → ročné zhodnotenie → max drawdown". Nie je
  jedno číslo; 12 % ročne pri 5 % drawdowne a 60 % ročne pri 30 % drawdowne je tá istá
  stratégia s inou pákou.
- **rok po roku** — či to nesie jeden dobrý rok, alebo je to rozložené.
- **korelácie** — koľko z toho, čo robí jeden člen, robia aj ostatní.

### Prečo sú korelácie to najdôležitejšie číslo
Portfólio má zmysel len vtedy, keď sa členovia nechovajú rovnako: keď jeden prehráva a
druhý zarába, krivka je hladšia než ktorýkoľvek z nich. Keď sú členovia korelovaní, je to
len jeden beh s väčšou pozíciou — a **drawdown sa nezmenší, len sa znásobí**.

U nás to treba povedať nahlas: naše „portfólio" je zvyčajne **jedna stratégia na viacerých
trhoch**, a tá bude korelovaná viac než portfólio rôznych stratégií. Výpis to preto meria a
nehovorí „portfólio je hladšie", kým to čísla nepotvrdia.

### Čo je a čo nie je člen portfólia
Člen je **jeden beh**. Dva behy toho istého trhu v tom istom období nie sú dvaja členovia,
ale dve **alternatívy** tej istej veci — a keby sa ich obchody sčítali, to isté obdobie by
sa započítalo dvakrát a portfólio by vyzeralo dvakrát aktívnejšie, než v skutočnosti je.
Modul takú dvojicu nájde a nahlási; do súčtu ich pustí, ale záver o nich nerobí.

Portfólio má zmysel medzi **rôznymi trhmi** (matica trhov je na to ideálny zdroj) alebo
medzi **rôznymi stratégiami**. Nie medzi variantmi jedného profilu.

### Ako sa počíta
Obchody všetkých členov sa zoradia podľa času zatvorenia a prehrajú cez jeden účet.
Veľkosť pozície sa **prepočíta** na zvolené riziko: `riziko = zostatok x risk %`,
`množstvo = riziko / vzdialenosť stopu`. Bez toho by sa sčítavali veľkosti z rôznych behov
a výsledok by nehovoril o stratégii, ale o tom, s akou peňaženkou ktorý beh bežal.

Dve zjednodušenia, ktoré treba poznať:

- **Súbežné pozície sa nekrátia.** Keď majú dvaja členovia otvorené naraz, obaja sú
  sizovaní z vtedajšieho zostatku a margin sa nekontroluje. Skutočný účet by mohol naraziť
  na limit; toto je horná hranica toho, čo by šlo.
- **Vzdialenosť stopu musí byť známa.** Berie sa z plánu obchodu (kresby SL/TP), inak zo
  skutočného stopu. Obchod, pri ktorom sa nedá určiť, do prepočtu nevstúpi — a výpis
  povie, koľko ich bolo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

__all__ = [
    "RISKS", "DEFAULT_ACCOUNT", "Member", "members", "equity_curve", "risk_table",
    "by_year", "correlations", "analyze", "report",
]

#: Riziko na obchod v % zo zostatku, pre ktoré sa počíta tabuľka.
RISKS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 3.0)

#: Východiskový účet. Výsledky sú v %, takže na absolútnej hodnote nezáleží.
DEFAULT_ACCOUNT = 10_000.0

#: Nad touto koreláciou už členovia nediverzifikujú, len zväčšujú pozíciu.
HIGH_CORRELATION = 0.7

#: Menej spoločných mesiacov a korelácia je náhodné číslo. Pri troch mesiacoch vyšla
#: medzi NAS100 a zemným plynom hodnota +0,99 — dva trhy, ktoré spolu nemajú nič.
MIN_MONTHS = 6


@dataclass
class Member:
    """Jeden člen portfólia — jeden beh."""

    id: str
    label: str = ""
    pair: str = ""
    timeframe: str = ""
    timerange: str = ""
    trades: int = 0
    first: str = ""
    last: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _sl_distance(t: dict[str, Any]) -> float | None:
    """Vzdialenosť stopu v cene. `None`, keď sa nedá určiť ani z plánu, ani z výstupu."""
    open_rate = float(t.get("open_rate") or 0)
    if not open_rate:
        return None
    podiel = t.get("_sl_pct")
    if podiel:
        return float(podiel) / 100.0 * open_rate
    if t.get("exit_reason") == "stop_loss":
        vzdialenost = abs(float(t.get("close_rate") or 0) - open_rate)
        return vzdialenost or None
    return None


def members(records: Sequence[dict[str, Any]]) -> list[Member]:
    """Popis členov portfólia — jeden člen je jeden beh."""
    out: list[Member] = []
    for rec in records:
        nast = rec.get("settings") or {}
        out.append(Member(
            id=rec["id"],
            label=f"{nast.get('pair')} {nast.get('timeframe')} {nast.get('timerange')}",
            pair=nast.get("pair") or "", timeframe=nast.get("timeframe") or "",
            timerange=nast.get("timerange") or "",
            trades=int((rec.get("result") or {}).get("trades") or 0),
        ))
    return out


def _overlap(a: str, b: str) -> bool:
    """Prekrývajú sa okná `YYYYMMDD-YYYYMMDD`?"""
    try:
        a1, a2 = a.split("-")
        b1, b2 = b.split("-")
    except (ValueError, AttributeError):
        return False
    return a1 < b2 and b1 < a2


def duplicates(records: Sequence[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """Dvojice behov, ktoré pokrývajú **ten istý trh v tom istom čase**.

    Nie sú to členovia portfólia, ale alternatívy toho istého — dva profily na BTC v tom
    istom roku. Keby sa sčítali, to isté obdobie by sa započítalo dvakrát.
    """
    out: list[tuple[str, str, str]] = []
    zoznam = list(records)
    for i, a in enumerate(zoznam):
        na, oa = (a.get("settings") or {}), (a.get("settings") or {}).get("timerange") or ""
        for b in zoznam[i + 1:]:
            nb = b.get("settings") or {}
            if na.get("pair") != nb.get("pair"):
                continue
            if _overlap(oa, nb.get("timerange") or ""):
                out.append((a["id"], b["id"], f"{na.get('pair')} {oa} x {nb.get('timerange')}"))
    return out


# --------------------------------------------------------------------------- #
# krivka kapitálu
# --------------------------------------------------------------------------- #


def equity_curve(trades: Sequence[dict[str, Any]], *, risk_pct: float,
                 account: float = DEFAULT_ACCOUNT) -> dict[str, Any]:
    """Prehrá obchody cez jeden účet pri danom riziku na obchod.

    Obchody sa radia podľa času **zatvorenia** — zostatok sa mení, keď obchod skončí, nie
    keď sa otvorí. Súbežné pozície sa nekrátia (viď hlavička modulu).
    """
    zoradene = sorted(
        (t for t in trades if _dt(t.get("close_date")) is not None),
        key=lambda t: _dt(t["close_date"]))
    zostatok = float(account)
    vrchol = zostatok
    max_dd = 0.0
    body: list[tuple[str, float]] = []
    preskocene = 0
    ruina = False
    for t in zoradene:
        sl = _sl_distance(t)
        if not sl or sl <= 0:
            preskocene += 1
            continue
        riziko = zostatok * risk_pct / 100.0
        mnozstvo = riziko / sl
        smer = -1.0 if t.get("is_short") else 1.0
        zisk = (float(t["close_rate"]) - float(t["open_rate"])) * mnozstvo * smer
        # Poplatky behu: obchod ich uz zaplatil, tak sa prepocitaju na novu velkost.
        objem = (float(t["open_rate"]) + float(t["close_rate"])) * mnozstvo
        poplatok = float(t.get("fee_open") or 0) * objem / 2 + float(t.get("fee_close") or 0) * objem / 2
        zostatok += zisk - poplatok
        if zostatok <= 0:
            zostatok = 0.0
            ruina = True
        vrchol = max(vrchol, zostatok)
        if vrchol > 0:
            max_dd = max(max_dd, (vrchol - zostatok) / vrchol)
        body.append((str(t["close_date"])[:19], round(zostatok, 2)))
        if ruina:
            break
    return {
        "risk_pct": risk_pct,
        "account": account,
        "final": round(zostatok, 2),
        "return_pct": round((zostatok / account - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "trades": len(body),
        "skipped": preskocene,
        "ruin": ruina,
        "curve": body,
    }


def _years(trades: Sequence[dict[str, Any]]) -> float:
    casy = [_dt(t.get("close_date")) for t in trades]
    casy = [c for c in casy if c]
    if len(casy) < 2:
        return 1.0
    return max((max(casy) - min(casy)).days, 1) / 365.0


def risk_table(trades: Sequence[dict[str, Any]], *, account: float = DEFAULT_ACCOUNT,
               risks: Sequence[float] = RISKS) -> list[dict[str, Any]]:
    """„Koľko sa dá zarobiť" — pre každé riziko jeden riadok.

    Ročné zhodnotenie je **zložené** (CAGR), nie celkové delené rokmi: pri dvojcifernom
    zhodnotení sa tie dve čísla líšia natoľko, že by z toho bol iný záver.
    """
    roky = _years(trades)
    out = []
    for risk in risks:
        v = equity_curve(trades, risk_pct=risk, account=account)
        podiel = v["final"] / account
        cagr = ((podiel ** (1 / roky)) - 1) * 100 if podiel > 0 and roky > 0 else -100.0
        out.append({**{k: v[k] for k in
                       ("risk_pct", "return_pct", "max_drawdown_pct", "trades", "ruin", "skipped")},
                    "cagr_pct": round(cagr, 2),
                    "final": v["final"]})
    return out


def by_year(trades: Sequence[dict[str, Any]], *, risk_pct: float = 1.0,
            account: float = DEFAULT_ACCOUNT) -> list[dict[str, Any]]:
    """Zhodnotenie po kalendárnych rokoch — nesie to jeden rok, alebo je to rozložené?"""
    v = equity_curve(trades, risk_pct=risk_pct, account=account)
    po_rokoch: dict[str, list[float]] = {}
    predch = account
    for cas, zostatok in v["curve"]:
        po_rokoch.setdefault(cas[:4], []).append(zostatok)
    out = []
    for rok in sorted(po_rokoch):
        konec = po_rokoch[rok][-1]
        out.append({"year": rok, "return_pct": round((konec / predch - 1) * 100, 2),
                    "trades": len(po_rokoch[rok]), "final": round(konec, 2)})
        predch = konec
    return out


# --------------------------------------------------------------------------- #
# korelácie
# --------------------------------------------------------------------------- #


def correlations(per_member: dict[str, Sequence[dict[str, Any]]]) -> dict[str, Any]:
    """Korelácia mesačných výsledkov medzi členmi.

    Mesiace, nie obchody: obchody sa dejú v rôznych časoch a spárovať sa nedajú, kým
    kalendárny mesiac majú spoločný. Členovia bez prekryvu sa neporovnávajú — korelácia
    z nula spoločných mesiacov nie je nula, je to „nevieme".
    """
    import numpy as np

    mesacne: dict[str, dict[str, float]] = {}
    for meno, trades in per_member.items():
        podla_mesiaca: dict[str, float] = {}
        for t in trades:
            cas = _dt(t.get("close_date"))
            if cas is None:
                continue
            podla_mesiaca[f"{cas:%Y-%m}"] = podla_mesiaca.get(f"{cas:%Y-%m}", 0.0) + float(
                t.get("profit_abs") or 0.0)
        mesacne[meno] = podla_mesiaca

    mena = sorted(mesacne)
    matica: dict[str, dict[str, float | None]] = {a: {} for a in mena}
    dvojice: list[tuple[str, str, float]] = []
    for i, a in enumerate(mena):
        for b in mena[i:]:
            spolocne = sorted(set(mesacne[a]) & set(mesacne[b]))
            if a == b:
                matica[a][b] = 1.0
                continue
            if len(spolocne) < MIN_MONTHS:
                matica[a][b] = matica[b][a] = None
                continue
            x = np.array([mesacne[a][m] for m in spolocne])
            y = np.array([mesacne[b][m] for m in spolocne])
            if x.std() == 0 or y.std() == 0:
                matica[a][b] = matica[b][a] = None
                continue
            r = float(np.corrcoef(x, y)[0, 1])
            matica[a][b] = matica[b][a] = round(r, 3)
            dvojice.append((a, b, round(r, 3), len(spolocne)))
    hodnoty = [r for _, _, r, _ in dvojice]
    vysoke = [d for d in dvojice if d[2] >= HIGH_CORRELATION]
    return {
        "matrix": matica,
        "pairs": sorted(dvojice, key=lambda x: -x[2]),
        "mean": round(float(np.mean(hodnoty)), 3) if hodnoty else None,
        "max": max(hodnoty) if hodnoty else None,
        "compared": len(dvojice),
        "high": len(vysoke),
        "high_share": round(len(vysoke) / len(dvojice), 3) if dvojice else None,
        "min_months": MIN_MONTHS,
        "skipped": sum(1 for a in mena for b in mena if a < b and matica[a].get(b) is None),
    }


# --------------------------------------------------------------------------- #
# celok
# --------------------------------------------------------------------------- #


def analyze(per_member: dict[str, Sequence[dict[str, Any]]], *,
            records: Sequence[dict[str, Any]] = (), account: float = DEFAULT_ACCOUNT,
            risks: Sequence[float] = RISKS, risk_pct: float = 1.0) -> dict[str, Any]:
    """Celé portfólio: cena rizika, rok po roku, korelácie a jedna veta na záver."""
    vsetky: list[dict[str, Any]] = []
    for trades in per_member.values():
        vsetky += list(trades)
    if not vsetky:
        return {"members": [], "trades": 0, "verdict": "Ziadne obchody."}

    korelacie = correlations(per_member)
    tabulka = risk_table(vsetky, account=account, risks=risks)
    zdvojene = duplicates(records) if records else []
    return {
        "duplicates": [{"a": a, "b": b, "what": co} for a, b, co in zdvojene],
        "members": [m.to_dict() for m in members(records)] if records else
                   [{"id": k, "label": k, "trades": len(v)} for k, v in per_member.items()],
        "trades": len(vsetky),
        "account": account,
        "risks": tabulka,
        "by_year": by_year(vsetky, risk_pct=risk_pct, account=account),
        "correlations": korelacie,
        "verdict": _verdict(korelacie, tabulka, len(per_member), zdvojene),
    }


def _verdict(korelacie: dict[str, Any], tabulka: list[dict[str, Any]], clenov: int,
             zdvojene: Sequence[tuple[str, str, str]] = ()) -> str:
    """Jedna veta — a je predovšetkým o koreláciách, lebo tie rozhodujú o zmysle portfólia.

    Priemer sám nestačí: pri desiatich členoch vyšiel priemer −0,03, hoci štyri dvojice
    mali nad +0,90. Priemer blízko nuly vtedy neznamená „nezávislé", ale „polovica sa hýbe
    spolu a polovica proti" — a to je iná vec. Rozhoduje preto aj **podiel silne
    korelovaných dvojíc**.
    """
    if zdvojene:
        return (f"TO NIE JE PORTFOLIO: {len(zdvojene)} dvojic behov pokryva TEN ISTY trh "
                f"v tom istom case (napr. {zdvojene[0][2]}). Su to alternativy jednej veci, "
                "nie clenovia portfolia - to iste obdobie sa v sucte zapocitalo viackrat. "
                "Vyber behy z roznych trhov (matica trhov) alebo z roznych strategii.")
    if clenov < 2:
        return ("Jeden clen nie je portfolio - tabulka rizika plati, ale o diverzifikacii "
                "nehovori nic.")
    priemer, podiel = korelacie.get("mean"), korelacie.get("high_share")
    if priemer is None:
        return (f"{clenov} clenov, ale spolocnych mesiacov je primalo na korelacie "
                f"(treba aspon {korelacie.get('min_months')}) - bez nich sa neda povedat, "
                "ci sa navzajom dopĺňaju.")
    vysoke = korelacie.get("high") or 0
    dvojic = korelacie.get("compared") or 0
    if podiel and podiel >= 0.3:
        return (f"CAST CLENOV SA HYBE SPOLU: {vysoke} z {dvojic} dvojic ma korelaciu nad "
                f"{HIGH_CORRELATION:+.1f} (priemer {priemer:+.2f}). Tie sa navzajom "
                "nediverzifikuju, len zvacsuju poziciu - drawdown sa im scita.")
    if priemer >= HIGH_CORRELATION:
        return (f"CLENOVIA SU KORELOVANI (priemer {priemer:+.2f}). Portfolio sa chova ako jeden "
                "beh s vacsou poziciou: drawdown sa nezmensi, len sa znasobi.")
    if priemer <= 0.3:
        return (f"CLENOVIA SU MALO KORELOVANI (priemer {priemer:+.2f}, silne korelovanych "
                f"{vysoke} z {dvojic} dvojic) - presne o to v portfoliu ide: ked jeden "
                "prehrava a druhy zaraba, krivka je hladsia nez ktorykolvek z nich.")
    return (f"CIASTOCNA DIVERZIFIKACIA (priemer korelacie {priemer:+.2f}). Nieco to prinesie, "
            "ale nie tolko ako naozaj nezavisle strategie.")


def report(vysledok: dict[str, Any]) -> str:
    """Výpis — ASCII, konzola na Windows beží v cp1250."""
    if not vysledok.get("risks"):
        return vysledok.get("verdict", "portfolio sa nedalo spocitat")
    lines = [f"clenov {len(vysledok['members'])}, obchodov {vysledok['trades']}, "
             f"ucet {vysledok['account']:g}", ""]
    lines.append(f"{'riziko/obchod':<15}{'zhodnotenie':>13}{'rocne (CAGR)':>14}"
                 f"{'max drawdown':>14}{'obchodov':>10}")
    for r in vysledok["risks"]:
        ruina = "  RUINA" if r["ruin"] else ""
        lines.append(f"{r['risk_pct']:>13.2f} %{r['return_pct']:>12.1f} %"
                     f"{r['cagr_pct']:>13.1f} %{r['max_drawdown_pct']:>13.1f} %"
                     f"{r['trades']:>10}{ruina}")
    if vysledok["risks"] and vysledok["risks"][0]["skipped"]:
        lines.append(f"  (bez vzdialenosti stopu: {vysledok['risks'][0]['skipped']} obchodov "
                     "do prepoctu nevstupilo)")

    if vysledok.get("by_year"):
        lines += ["", f"{'rok':<8}{'zhodnotenie':>13}{'obchodov':>10}"]
        for r in vysledok["by_year"]:
            lines.append(f"{r['year']:<8}{r['return_pct']:>12.1f} %{r['trades']:>10}")

    if vysledok.get("duplicates"):
        lines += ["", f"POZOR: {len(vysledok['duplicates'])} dvojic pokryva ten isty trh "
                      "v tom istom case:"]
        for d in vysledok["duplicates"][:5]:
            lines.append(f"  {d['what']}")

    k = vysledok.get("correlations") or {}
    if k.get("pairs"):
        lines += ["", "najkorelovanejsie dvojice:"]
        for a, b, r, mesiacov in k["pairs"][:5]:
            lines.append(f"  {r:+.2f}  {a}  <->  {b}   ({mesiacov} spolocnych mesiacov)")
        if k.get("skipped"):
            lines.append(f"  ({k['skipped']} dvojic sa neporovnalo - menej nez "
                         f"{k.get('min_months')} spolocnych mesiacov)")
    lines += ["", vysledok["verdict"]]
    return "\n".join(lines)
