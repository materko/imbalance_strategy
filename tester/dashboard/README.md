# Dashboard výsledkov testovania

Statická stránka (jeden súbor `index.html`, bez buildu) na prehľad výsledkov hľadania
nastavení stratégií — vzhľadom podobná dashboardu prop firmy Tradeify: tmavý režim
(prepínač na svetlý, rešpektuje aj nastavenie systému), karty, zelená/červená.
Funguje aj na telefóne.

Jediná externá knižnica je Chart.js z `cdnjs.cloudflare.com`; všetko ostatné je v súbore.
Štatistiky v detaile (win rate, PF, priemerný zisk/strata, séria strát, prepad, obchody
za rok, očakávanie) sa počítajú v prehliadači z `trades`; kalendár a mesačné súčty z `daily`;
krivka z `equity`. Hodnoty `is`, `oos`, `years` a `plateau_min` sa iba zobrazujú.

`dashboard_data.json` v tomto priečinku sú **ukážkové, vymyslené dáta** na odskúšanie stránky.

## Obrazovky

- **Prehľad** — karta pre každú stratégiu: názov, krok postupu, výsledok kroku 1,
  počet skúšaných kombinácií, počet kandidátov (nastavenia so stavom `kandidát` alebo
  `prešiel…`) a najlepší PF in-sample. Klik otvorí stratégiu.
- **Stratégia** — tabuľka nastavení: popis, stav, PF IS, obchody za rok, PF najhoršieho roka, PF OOS.
- **Detail nastavenia** — krivka kapitálu s prepadom (zvislá čiara na začiatku odloženého
  roka 4. 9. 2025, ak má nastavenie `oos`), dlaždice štatistík (celé obdobie / in-sample /
  odložený rok), kalendár denného PnL po mesiacoch so súčtom týždňov, mesačné súčty
  (klik na stĺpec prepne kalendár), PF po rokoch s čiarami 1,0 a 1,3, blok odloženého
  roka a tabuľka obchodov (triedenie podľa dátumu a PnL, 50 na stranu).
- **Diverzifikácia** (`#/div`, odkaz v hlavičke) — viac nastavení naraz, aj z rôznych stratégií
  (najviac 8): pri nastavení **Pridať**, pri vybranom násobok veľkosti (0,5 = polovica; stratégie
  nemajú rovnaké riziko na obchod) a **Prepočítať**. Obchody aj dni sa zlúčia v prehliadači z tých
  istých `trades` a `daily` a ukáže sa súhrn (posledný rok a celé obdobie), automatické zistenia
  (roky v pluse, korelácia denných výsledkov, mesiace v pluse, prepad spolu vs. súčet prepadov,
  podiel na zisku), krivky kapitálu a prepad spolu, roky, mesiace, dni, dni v týždni, hodina
  vstupu (New York), korelácie dvojíc a denník obchodov a dní s filtrom. Výber si stránka pamätá
  v prehliadači (`localStorage`); pri prvom otvorení predvyplní nastavenie č. 1 z prvých troch
  stratégií, ktoré prešli smernicou.

- **Live** (`#/live`, odkaz v hlavičke) — stratégie nasadené naživo (NinjaTrader, MetaTrader 5) zo sekcie `live`
  dát (viď nižšie): súhrn (obchody, WR, PF, zisk, R, otvorené pozície, vyplnené signály), zistenia
  (signál bez vyplnenia u brokera, výstup bez vstupu, zastavená alebo tichá inštancia, či tá istá stratégia
  dáva na dvoch platformách tie isté signály odkedy bežia obe, málo obchodov na porovnanie), tabuľka
  „naživo vs. test" (nastavenie stránky podľa čísla profilu, test = posledný rok), krivka zisku a denník
  obchodov, signálov, otvorených pozícií a varovaní platformy. Časy sú v miestnom čase prehliadača; zisk je
  hrubý (bez poplatkov), MT5 CFD má inú veľkosť kontraktu, preto sa porovnávajú WR, PF a R. Inštancie bez
  obchodu a bez správy viac ako 7 dní sú zbalené dole.
  Je to Diverzifikácia nad živými obchodmi: výber inštancií a jednotka **$ / R** hore (pamätá si ich `localStorage`)
  platia pre celú stránku a inštancie idú cez ten istý výpočet (`dvComputeParts`) — prepad spolu, dni, dni v týždni,
  hodina vstupu (New York), obchody, korelácia denných výsledkov (od 11 spoločných dní) a koláč podielu na zisku.
  Navyše **pásmo naživo vs. test**: z obchodov testu toho istého nastavenia (posledný rok, ak ich je ≥ 40, inak celý
  test) sa 2000-krát (pevné semienko) vytiahne toľko obchodov, koľko je naživo, a ukáže sa pásmo 5 – 95 %, percentil
  živého výsledku, prepad naživo proti najhoršiemu v teste a graf cesty naživo v pásme — v **bodoch indexu**, aby sa
  MNQ aj US100.cash dali porovnať bez ohľadu na veľkosť kontraktu. A **kvalita plnenia**: sklz vstupu proti plánovanej
  cene enginu, sklz na stope a TP, čo plnenia stáli v $ a R a oneskorenie Market príkazov od odoslania po vyplnenie.

Adresy sú v hashi: `#/`, `#/s/<key stratégie>`, `#/d/<id nastavenia>`, `#/div`, `#/live` — dajú sa poslať ako odkaz.

## Ako otvoriť

Stránka si načíta `dashboard_data.json` ležiaci vedľa nej (`fetch`). Prehliadač to zo
súboru (`file://`) nedovolí, preto ju treba servírovať:

```bash
cd tester/dashboard
python3 -m http.server 8800
# otvor http://localhost:8800/
```

### Jeden súbor s dátami vnútri

Ak pred hlavným skriptom stránky existuje `window.DASHBOARD_DATA`, stránka použije ten
objekt a nič nesťahuje. Takto sa dá publikovať ako jediný súbor — stačí do `index.html`
pred `<script>` s kódom stránky (napr. hneď za `<script src=…chart.umd.min.js>`) vložiť:

```html
<script>window.DASHBOARD_DATA = { …obsah dashboard_data.json… };</script>
```

## Formát `dashboard_data.json`

```jsonc
{
  "updated": "2026-10-09 07:00",          // čas aktualizácie, zobrazí sa v hlavičke
  "note": "text",                          // poznámka v hlavičke
  "strategies": [{
    "key": "vwaporb",                      // kľúč stratégie (časť adresy)
    "name": "VWAP ORB",
    "guideline_step": "krok 4 — hľadanie", // kde v postupe stratégia je
    "combos": 1234,                        // počet skúšaných kombinácií
    "step1": "prešiel",                    // výsledok kroku 1 („prešiel" / „neprešiel")
    "settings": [{
      "id": "vwaporb-1",                   // jedinečné id nastavenia (časť adresy)
      "label": "krátky popis nastavenia",
      "status": "kandidát",                // „kandidát" | „prešiel odloženým rokom" | „neprešiel"
      "params": {"name": 1.5},             // parametre nastavenia, ľubovoľné kľúče
      "is": {                              // in-sample (pred 4. 9. 2025)
        "pf": 1.47, "trades": 571, "trades_per_year": 145, "winrate": 52.1,
        "pnl": 12345, "maxdd": 2100,
        "years": {"21/22": 1.24, "22/23": 1.34, "23/24": 1.90, "24/25": 1.54}  // PF po rokoch
      },
      "oos": {"pf": 0.91, "trades": 150, "winrate": 48.0, "pnl": -800, "maxdd": 1500},  // alebo null
      "plateau_min": 0.85,                 // najnižší PF v okolí nastavenia (plató)
      "equity": [["2021-10-04", 120.5]],   // kumulatívny PnL podľa dní
      "daily":  [["2021-10-04", 120.5]],   // PnL za deň (len obchodné dni)
      "trades": [{
        "open": "2021-10-04T13:35:00Z", "close": "2021-10-04T14:10:00Z",  // UTC
        "dir": "long",                     // „long" | „short"
        "entry": 15000.25, "exit": 15020.5,
        "pnl": 40.5,                       // v USD
        "reason": "take_profit"
      }]
    }]
  }]
}
```

Začiatok odloženého roka (out-of-sample) je pevne 2025-09-04 (konštanta `OOS_START`
v `index.html`). Zvislá značka v grafe a voľba „Odložený rok" sa ukážu len pri nastavení
s `oos` ≠ `null`.

## Sekcia `live` (karta Live)

Vyrába ju `tester/dashboard/live.py` zo zrkadla live telemetrie webapp (`tester/live/mirror.sqlite`, docs/LIVE.md)
na stroji, ktorý stránku generuje — webapp tam musí bežať s `tester/agent.json`, aby si zrkadlo ťahalo z hubu:

```python
from tester.dashboard.live import build_live
data["live"] = build_live()
```

alebo `python -m tester.dashboard.live --into dashboard_data.json` (pridá kľúč `live` do hotových dát).
Bez kľúča `live` karta povie, že dáta ešte nie sú.

```jsonc
"live": {
  "generated": "2026-10-16T05:24:00Z",
  "instances": [{
    "id": "ninjatrader_DEMO9584400_MNQ_3m_vwaporbnet", "engine": "vwaporbnet", "strategy": "vwaporb",
    "name": "VWAP ORB 1.5", "setting": "vwaporb-1",          // id nastavenia stránky z čísla profilu, inak null
    "profile": "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1", "platform": "ninjatrader", "account": "DEMO9584400",
    "symbol": "MNQ", "tf": 3, "point_value": 2.0, "status": "beží",   // beží | ticho (>30 min bez správy) | zastavená (bye)
    "stale": false, "since": "…Z", "last_event": "…Z", "last_bar": "…Z", "orphan_fills": 0,
    "trades": [{"id": "orb:ny:5081", "open": "…Z", "close": "…Z", "signal": "…Z", "dir": "long", "entry": 0, "exit": 0,
                "qty": 1, "sl": 0, "tp": 0, "order_type": "Market", "reason": "take_profit", "pts": 0, "pnl": 0, "r": 0.5,
                "plan": 0, "sent": "…Z", "sd": 0}],   // plánovaná cena vstupu, odoslanie príkazu, 1 R v bodoch (kvalita plnenia)
    "open": [{"id": "…", "open": "…Z", "dir": "short", "entry": 0, "qty": 1, "sl": 0, "tp": 0}],
    "signals": [{"t": "…Z", "id": "…", "dir": "long", "type": "Market", "entry": 0, "sl": 0, "tp": 0, "qty": 1,
                 "why": "…", "result": "vyplnený"}],   // vyplnený | zrušený: <dôvod> | čaká | bez vyplnenia
    "notes": [{"t": "…Z", "level": "warn", "text": "…"}]
  }]
}
```

