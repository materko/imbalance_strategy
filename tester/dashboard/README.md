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

Adresy sú v hashi: `#/`, `#/s/<key stratégie>`, `#/d/<id nastavenia>` — dajú sa poslať ako odkaz.

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
