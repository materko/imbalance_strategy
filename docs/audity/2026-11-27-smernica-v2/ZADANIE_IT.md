# Zadanie pre vývojára: zavedenie SMERNICE V2 v TradeBote

*Verzia 27. 11. 2026. Zdroj: `SMERNICA_V2.md` (schválená 27. 11. 2026). Ak sa zadanie a smernica líšia, platí smernica,
ale vývojár rozpor nahlási, nerozhoduje ho sám. Úlohy U1–U11 idú v uvedenom poradí. Každá úloha má akceptačné
kritériá, podľa ktorých ju skontrolujeme.*

## 0. Pravidlá pre celú prácu

- Repozitár `~/IBS` (TradeBot). Pracuje sa v režime developer podľa `CLAUDE.md`.
- **Pred každým pushom musí prejsť:**
  - `pytest` vrátane golden testov `tester/tests/test_golden_tv_binance.py`,
  - `ruff check .`,
  - ESLint webapp (príkaz je v hlavičke `tester/webapp/eslint.config.mjs`),
  - `python -m tradebot.adapters.csharp.build --force`.
- **Každá zmena logiky v Pythone musí mať rovnakú zmenu v C#** (`tradebot/core/ports/csharp/…`) a prejsť paritou bar po
  bare: `python -m tester.compare.csharp_parity` a `tester/tests/test_csharp_parity.py` s **0 nezhodami**.
- **Jadro ani adaptéry nesmú poznať stratégiu menom.** Všetko ide cez `StrategySpec` a konfiguráciu nástroja.
- **Cesty sa píšu len v `tradebot/core/paths.py`.**
- **Commity:** slovenská veta v imperatíve, čo a prečo. Jedna úloha môže mať viac commitov.
- **Zakázané:**
  - zasahovať do živého stroja `nas-win11` a do bežiacich inštancií na FTMO,
  - nasadzovať EA alebo NT naživo. Nasadenie robí používateľ, vývojár dodá súbor a postup.
  - hromadne mazať behy v `tester/runs/` (len cez `cli archive`),
  - commitovať Pine skripty, tokeny a heslá.
- **Nové parametre** majú predvolenú hodnotu, s ktorou sa správanie nezmení, okrem miest, kde zadanie výslovne hovorí inak.
  Patria do `PORT_ONLY_FIELDS` alebo do konfigurácie nástroja.
- **Na konci každej úlohy** vývojár dodá krátky zápis v `docs/merania/` alebo v PR: čo sa zmenilo, ako sa to testuje
  a výsledok akceptačných testov.

---

## U1. Denná ochrana účtu v EA (MT5) a NinjaTrader — **najvyššia priorita**

**Súbory:**
- `tradebot/adapters/mt5/TradeBotEA.mqh`, `tradebot/adapters/mt5/TradeBotExecutor.mqh`, šablóny `deploy/mt5/*.mq5`,
- `tradebot/adapters/ninjatrader/TradeBotStrategy.cs`, `TradeBotLiveAddOn.cs`,
- testy `tester/tests/test_mt5_static_host.py` a nové testy.

**Požiadavky (všetko lokálne v EA a NT, bez závislosti od hubu a Mac mini):**

1. **Denný stop −4 %:**
   - Základ dňa = `max(balance, equity)` v okamihu resetu dňa.
   - Reset je konfigurovateľný: predvolene **00:00 Europe/Prague** (FTMO), časové pásmo sa zadáva parametrom.
   - Spúšťač: `equity ≤ základ × (1 − 0,04)`, kontrola pri každom ticku aj pri každom fille.
   - Pri spustení:
     - zavrieť všetky otvorené pozície účtu (všetky inštancie, všetky symboly, nielen vlastné),
     - zrušiť všetky čakajúce príkazy,
     - zablokovať nové vstupy do najbližšieho resetu.
   - Stav „zablokované do“ sa uloží do súboru alebo do GlobalVariable, aby **prežil reštart EA aj terminálu**.
   - Parameter `DailyStopPct` (predvolene 4,0). Hodnota 0 vypína, ale pri spustení sa vypíše varovanie.
   - **Celkový stop sa nerobí** (rozhodnutie používateľa).
2. **Kontrola súčasného rizika pred vstupom:**
   - Súčet rizík do SL všetkých otvorených pozícií a nového obchodu ≤ **1,5 % equity**, inak sa vstup neodošle a zapíše sa do logu.
   - Riziko jednej pozície = |vstup − SL| × objem × hodnota bodu.
   - Parameter `MaxOpenRiskPct` = 1,5.
3. **SL a TP vždy u brokera** (príkaz sa odosiela so SL a TP, nie ako „virtuálny“ stop v EA).
   - Pozícia bez SL u brokera do 5 s od fillu sa zavrie trhom a zapíše sa chyba.
4. **Duplicita:** ten istý kľúč stratégie s rovnakým profilom na dvoch účtoch, ktoré sa sčítavajú (rovnaký login alebo
   skupina zo zoznamu), sa pri štarte odmietne. Zoznam skupín je v konfigurácii.
5. **Alarm:**
   - Žiadny heartbeat inštancie > 30 min počas seansy → Telegram (`tester/hub/agent_plugins/telegram`, hub plugin `watchdog`).
   - Alarm smie závisieť od hubu, stop podľa bodov 1–3 nie.
6. **Log:** každé spustenie stopu, zablokovanie a odmietnutý vstup ide do logu EA a do zrkadla
   (`livedata`, `tester/live/mirror.sqlite`) ako udalosť `account_guard`.

**Akceptácia:**
- Unit testy výpočtu základu, spúšťača, resetu (aj cez prechod letného času) a kontroly rizika.
- Na **demo** účte (nie Server3) sa simuluje strata 4 % (malý účet alebo znížený prah, napr. 0,2 %):
  - pozície sa zavrú,
  - nové vstupy sa odmietnu,
  - po reštarte EA ostane blokovanie,
  - po resete sa obchodovanie obnoví.
- Fasáda `StaticHost` musí dávať to isté ako most (`test_mt5_static_host.py`).

**Odhad:** 3–5 dní.

---

## U2. Zápis bid, ask, spreadu a presného času pri fille

**Súbory:**
- `tradebot/adapters/mt5/TradeBotEA.mqh` (dnes `DEAL_TIME` v sekundách, `:1621`, `:1887`, `:2078`; spread M1 sa zahadzuje, `:1047`),
- NT `TradeBotStrategy.cs`,
- hub plugin `tester/hub/plugins/livedata`,
- `tester/live/`.

**Požiadavky:**
1. Čas fillu sa berie z `DEAL_TIME_MSC` (ms), nie z `DEAL_TIME`. Všade sa ukladá v **UTC ms**.
   - Overiť a opraviť prevod času servera (+2/+3 h) aj cez prechody letného času.
2. **Pri každom fille** sa uloží:
   - `bid`, `ask` a `spread` (v bodoch) v okamihu spustenia príkazu a v okamihu fillu (`SymbolInfoTick`),
   - typ príkazu (market / limit / stop / SL / TP),
   - požadovaná cena (úroveň) a skutočná cena.
3. **Pri M1 sviečke** sa posiela aj spread sviečky z MT5 (`spread` z `MqlRates`). Dnes sa zahadzuje.
4. **NT:** to isté cez `GetCurrentBid()` a `GetCurrentAsk()` v okamihu fillu.
5. **Zrkadlo:**
   - nové stĺpce `bid`, `ask`, `spread`, `time_msc`, `req_price`, `order_kind` v tabuľke fillov,
   - stĺpec `spread` v M1,
   - migrácia nesmie zmazať staré dáta.
6. **Odmietnutý príkaz** (napr. `10015 invalid price`) sa zapíše ako udalosť s cenou a bid/ask.

**Akceptácia:**
- Na deme 10 fillov s vyplnenými stĺpcami.
- Rozdiel `time_msc` oproti času v histórii terminálu ≤ 1 s.
- Test migrácie zrkadla na kópii `mirror.sqlite`.

**Odhad:** 1–2 dni.

---

## U3. Jednorazové meranie spreadu z histórie brokera

**Cieľ:** nahradiť odhady v tabuľke CFD (§3 smernice) nameranými číslami. **Bez nového sťahovania platených dát.**

1. Skript MQL5 (`tradebot/adapters/mt5/`) a spracovanie v Pythone (`tester/live/` alebo `tester/`).
   - Skript cez `CopyTicks` (bid/ask) a spread M1 exportuje celú dostupnú históriu pre **US100.cash, US500.cash a XAUUSD**
     do CSV v čase UTC.
   - **Spúšťa ho používateľ na demo termináli.** Na `nas-win11` len so súhlasom používateľa.
2. Výstup je tabuľka na symbol:

   | okno | p50, p75, p95 spreadu |
   |---|---|
   | po 30-min úsekoch času New York | ✓ |
   | hlavná seansa 9:30–16:00 NY | ✓ |
   | otvorenie NY 9:30–9:40 | ✓ |
   | ±5 min okolo udalostí z `calendar_us.json` (podľa typu udalosti) | ✓ |
   | mimo hlavnej seansy | ✓ |

   Ku každému oknu aj počet tickov.
3. Výsledok sa zapíše do `docs/merania/<dátum>-cfd-spread.md`.
4. Ak sa p75 líši od tabuľky v §3 o viac ako 0,5 S, navrhne sa nová tabuľka. **Zmenu tabuľky schvaľuje používateľ.**

**Odhad:** 1 deň.

---

## U4. Nové plnenie príkazov („fill v2“) v emulátore — Python aj C#

**Súbory:**
- `tradebot/adapters/multicharts/emulator.py` (`_entry_fill` `:189`, `_exit_fill` `:231`, `emulate` `:251`),
- `tradebot/core/ports/csharp/TradeBot.Backtest/McEmulator.cs`,
- konfigurácia nástrojov `tradebot/core/instruments_databento.json` (+ nový súbor alebo sekcia pre CFD),
- `tester/fees.py`,
- CLI `tester/webapp/cli`: prepínač `--fill v1|v2`.

**Pravidlá:**
- `v1` = dnešné správanie, ostáva kvôli golden testom proti TradingView a na porovnanie.
- `v2` = predvolené pre emulátor MultiCharts a C# jadro **až po akceptácii**.
- Golden testy bežia na `v1`.
- Freqtrade sa nemení, CFD ide len cez emulátor.

### U4a. Futures (MNQ, MYM, ES/MES, MGC, 6E, BTC)

Parametre na nástroj:

| | MNQ | MYM | ES / MES | MGC | 6E | BTC (Binance perp) |
|---|---|---|---|---|---|---|
| tick (bodov) | 0,25 | 1 | 0,25 | 0,10 | 0,00005 | podľa burzy |
| `cost_ticks` na stranu (poplatok + ½ spreadu) | 1,75 | 1,75 | 1 | 1,5 | 1 | 0,02 % maker / 0,05 % taker |
| `slip_ticks` (SL, stop vstup, market, výstup v čase) | 2 | 2 | 1 | 1 | 0,5 | 0,02 % |
| `pass_ticks` (limit vstup a TP) | 1 | 1 | 1 | 1 | 1 | 1 tick |

Vzorce (m = minúta, O/H/L = open, high, low minúty, T = tick):

| udalosť | podmienka v minúte m | cena fillu |
|---|---|---|
| long limit vstup na úrovni P | `L ≤ P − pass·T` | P |
| short limit vstup | `H ≥ P + pass·T` | P |
| long TP | `H ≥ TP + pass·T` | TP |
| short TP | `L ≤ TP − pass·T` | TP |
| long SL | `L ≤ SL` | `min(SL, O) − slip·T` |
| short SL | `H ≥ SL` | `max(SL, O) + slip·T` |
| long stop vstup E | `H ≥ E` | `max(E, O) + slip·T` |
| short stop vstup E | `L ≤ E` | `min(E, O) − slip·T` |
| market / výstup v čase, long nákup | open nasledujúcej minúty | `O + slip·T` |
| market predaj | open nasledujúcej minúty | `O − slip·T` |

- Náklad: `cost_ticks · T · hodnota bodu` za každú stranu (vstup aj výstup).
- **SL aj TP v tej istej minúte → SL.** Lepšia cena (price improvement) sa nikdy nepočíta.

### U4b. CFD (US100.cash, US500.cash, XAUUSD; ďalšie ako odhad)

Graf (broker aj Dukascopy) je **bid**. Ask = bid + S. Okná sa počítajú v čase New York (DST podľa NY), správy podľa
`calendar_us.json`.

| symbol | S hlavná seansa 9:30–16:00 NY | S mimo seansy | `pass_sell` | `slip_sl` (SL a stop vstup) | `slip_mkt` | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | 2,0 b | 4,0 b (S×2) | 0,25 b | 1,0 b | 0,5 b | S×2 a sklz +2 b | S×4 a sklz +4 b |
| US500.cash | 0,8 b | 1,6 b | 0,05 b | 0,3 b | 0,3 b | S×2 a +1 b | S×4 a +2 b |
| XAUUSD | 0,40 $ | 0,80 $ (S×2) | 0,05 $ | 0,25 $ | 0,15 $ | S×2 a +0,5 $ | S×5 a +1,5 $ |
| US30 (odhad) | 3 b | 6 b | 0 | 2 b | 1 b | S×2 | S×4 |
| EURUSD (odhad) | 0,3 pip + 0,25 pip provízia | 0,6 pip | 0 | 0,2 pip | 0,1 pip | S×1,5 | S×5 a +1 pip |
| BTCUSD (odhad) | zo zmluvy × 1,5 | — | 0 | 0,02 % | 0,02 % | — | S×3 |

Hodnoty sú v konfiguračnom súbore, nie v kóde, aby sa dali nahradiť meraním z U3.

Vzorce (O/H/L sú **bid**, S podľa okna v čase udalosti):

| udalosť | strana | podmienka | cena fillu |
|---|---|---|---|
| long limit vstup P | nákup | `L ≤ P − S` | P |
| short limit vstup P | predaj | `H ≥ P + pass_sell` | P |
| long TP | predaj | `H ≥ TP + pass_sell` | TP |
| short TP | nákup | `L ≤ TP − S` | TP |
| long SL | predaj | `L ≤ SL` | `min(SL, O) − slip_sl` |
| short SL | nákup | `H + S ≥ SL` | `max(SL, O + S) + slip_sl` |
| long stop vstup E | nákup | `H + S ≥ E` | `max(E, O + S) + slip_sl` |
| short stop vstup E | predaj | `L ≤ E` | `min(E, O) − slip_sl` |
| market nákup | nákup | open nasledujúcej minúty | `O + S + slip_mkt` |
| market predaj | predaj | open nasledujúcej minúty | `O − slip_mkt` |

- **Limit, ktorý je pri odoslaní už za trhom, sa neplní.** Ide o long limit `P ≥ O + S` alebo short limit `P ≤ O` v minúte odoslania.
  Do výsledku sa zapíše ako odmietnutý (MT5 ho odmietne chybou 10015).
- SL aj TP v tej istej minúte → SL. Lepšia cena sa nepočíta.
- Swap za každú noc podľa konfigurácie symbolu. Predvolene 0, vypíše sa varovanie, že chýba.

**Akceptácia U4:**
- Unit testy na každý riadok oboch tabuliek vzorcov: long aj short, okraj presne na hranici, minúta s gapom cez úroveň.
- Parita Python = C# na `v2`: 0 nezhôd na všetkých C# stratégiách (`csharp_parity`).
- `v1` dáva bit po bite to isté ako dnes (golden testy aj parita na `v1`).
- Report `v1` proti `v2` pre `ibsentrynet` (US100 aj MNQ), `vwaporbnet`, `noanet`, `nyvaesnet` (US500) a `spravynet` (XAUUSD)
  na rokoch ladenia (L) daného trhu: PF, obchody, zisk, podiel TP „dotykov“ (TP presne na high/low minúty).

**Odhad:** 3–4 dni.

---

## U5. Rolovanie futures

**Súbory:** `tester/bento_import.py`, `dq_night_rolls.py` (v `.nightsearch/kritika/`), Python jadro aj C# (parita).

1. Importér zapíše do `rolls.json` každé rolovanie: dátum, starý a nový kontrakt a **skok** (pomer close nového / starého
   v čase rolovania).
2. **Indikátory naprieč dňami** (PDH/PDL, predošlé zatvorenie, overnight H/L, gap, denné ATR, SMA dní, filter špičky)
   sa počítajú na **ratio back-adjustovanom** rade. Obchod a fill zostávajú na surovom rade.
3. Kým bod 2 nie je hotový, je parameter `skipRoll` **predvolene zapnutý** pre každú stratégiu, ktorá číta predošlú seansu.
   Znamená to žiadne vstupy v deň rolovania a 1 seansu po ňom.
4. **Oprava detektora** návratov kontraktu: jednociferný rok kódu kontraktu (napr. `ESH0`) sa po 10 rokoch opakuje.
   Rok kontraktu sa musí určiť z dátumu, inak detektor hlási falošné návraty.
   Správny výsledok: návrat len v MGC 1/2011.

**Akceptácia:**
- `rolls.json` so skokmi pre ES, MNQ, MYM, MGC a 6E.
- Parita na stratégiách s `skipRoll` zapnutým aj vypnutým.
- Detektor vráti presne 1 problém (MGC 1/2011).

**Odhad:** 3–4 dni.

---

## U6. Register pokusov a rozpočet

**Súbory:** nový `.nightsearch/register.py`, úprava `.nightsearch/glsearch.py`, `glhyper.py`, `glwr.py`, `glrr.py`.

1. **Register `.nightsearch/register/<hypotéza>.jsonl`** (len pridávanie, nič sa nemaže). Jeden riadok = jeden pokus:
   `čas, kľúč, trh, TF, parametre, obdobie, zdroj (grid|hyperopt|manual|study|plateau|wf), git hash kódu stratégie,
   PF, obchody, mesačný PnL (zoznam {mesiac, pnl})`.
2. **Hlavička `<hypotéza>.md`** musí byť commitnutá **pred prvým behom**. Bez nej automat beh odmietne.
   Obsah:
   - dôvod edge (3 vety),
   - zdroj,
   - **zoznam štúdií a výskumov, z ktorých hypotéza vychádza**,
   - mriežka,
   - trhy,
   - obdobie L,
   - hranice všetkých brán,
   - pevne zvolený typ vstupu (market/limit) a filter IBS + pin bar (neladia sa a nerátajú sa do parametrov),
   - prípadná výnimka pod 75 obchodov za rok.
3. **Rozpočet:**
   - ≤ **300 konfigurácií** na hypotézu spolu (všetky kópie a trhy, vrátane susedov v plató),
   - ≤ **5 voľných parametrov** (vrátane TF a bool, bez typu vstupu a IBS/pin bar),
   - po vyčerpaní automat skončí, navýšenie sa nepripúšťa.
4. **Strop:** najviac **10 nových hypotéz za štvrťrok na jeden trezor**.
5. **Hľadanie nikdy nepúšťa trezor ani rok A.** Odstrániť OOS z hľadania (`glsearch.py:864`, `glwr.py:244`, `glrr.py:140`).
6. **Legacy:**
   - jednorazový skript odhadne N pre dnešné stratégie z `gl_state.json`, `hyper_state.json`, `glwr` a `glrr`,
   - zapíše ho do registra s príznakom `legacy`,
   - commit zmrazí `GROUPS` a profily.

**Akceptácia:**
- Test, že beh bez hlavičky alebo nad rozpočet je odmietnutý.
- Test, že hľadanie nikdy nesiahne na dátumy trezoru ani roka A (kontrola rozsahu dát pri každom behu).

**Odhad:** 2 dni.

---

## U7. Trezory, zámky a počiatočné k

**Súbory:** `.nightsearch/register/vaults.json`, príkaz `--vault B|C`, `tester/checkup.py`, `tester/hyperopt.py`
(dnes `REFERENCE_WINDOWS` 10/2021–9/2026, `:56`).

1. **Obdobia** (presne podľa §1 smernice):

   | trh | L (ladenie + WF) | trezor B | rok A (len kontrola) |
   |---|---|---|---|
   | ES | 2015-01-01 – 2025-09-03 | 2010-06-06 – 2014-12-31 | 2025-09-04 – 2026-09-03 |
   | 6E | 2016-01-03 – 2021-09-30 | 2021-10-01 – 2025-09-03 | to isté |
   | MNQ | 2019-05-05 – 2022-09-30 | 2022-10-01 – 2025-09-03 | to isté |
   | MYM | 2019-06-02 – 2022-09-30 | 2022-10-01 – 2025-09-03 | to isté |
   | BTC (Binance perp) | 2019-09-08 – 2022-09-30 | 2022-10-01 – 2025-09-03 | to isté |
   | MGC | 2023-01-01 – 2025-09-03 | 2020-01-01 – 2022-12-31 | to isté |

   C = dáta od commitu hraníc (nové mesiace cez `bento_import`).
2. **Trezor sa otvára raz na hypotézu.** Druhé spustenie `--vault` pre tú istú hypotézu a trezor príkaz odmietne.
   Hranice brán sa berú z hlavičky (commit pred otvorením).
3. **Počiatočné k:**
   - Skript spočíta pre každý trezor počet rodín a kópií v `tradebot/strategies`, štúdií a triedení, ktoré na danom období
     kedy bežali. Zdroje: história behov `tester/runs` (index), `gl_state`, `hyper_state`, iCloud štúdie podľa tabuľky v §1.
   - Výsledok sa zapíše do `vaults.json` a commitne.
   - Očakávané rády: ES 2010–14 ≈ 10, MNQ, MYM, BTC a 6E ≈ 160 (horný odhad).
   - **Kým nie je spočítané, trezor sa neotvorí.**
4. **k ďalej rastie:** +1 za každú hypotézu **a každú kópiu rodiny**, ktorá trezor otvorila, a +1 za štúdiu, ktorá videla
   jeho obdobie.
5. **`checkup` a hyperopt** predvolene počítajú **len na L daného trhu** (`--windows L`), nie na `REFERENCE_WINDOWS`.
   Trezor smie počítať len `--vault`.
6. **„Iný režim“ sa meria pred otvorením a zapíše do hlavičky.** Režim je iný, ak v trezore existuje aspoň jeden štvrťrok
   s mediánom denného ATR(14) % mimo medzikvartilového rozpätia L, alebo pokles podkladu > 15 % od vrcholu, aký v L
   nebol. Bez merania je výsledok trezoru najviac ⏳.
7. **Dĺžka trezoru:** ≥ 2 roky alebo ≥ 30 % použiteľných dát trhu (platí dlhšie z oboch). Kontrola pri otvorení.

**Akceptácia:**
- `vaults.json` s obdobiami a počiatočným k (s rozpisom, odkiaľ sa k skladá).
- Test zámku (druhé otvorenie odmietnuté).
- Test, že `checkup` bez prepínača nesiahne mimo L.

**Odhad:** 2 dni.

---

## U8. Walk-forward so zámkom

**Súbory:** nový `tester/walkforward.py`, CLI `tester/webapp/cli` (`--wf`).

1. Okná:
   - **ES a 6E:** učenie 24 mesiacov, test 6 mesiacov, posun 6 mesiacov,
   - **MNQ, MYM, BTC a MGC:** učenie 18 mesiacov, test 6, posun 6.
   - Všetko len v rámci L.
2. V každom okne sa reoptimalizuje **tým istým automatom a zmrazenou mriežkou** z hlavičky, s rozpočtom ≤ 300 / počet okien.
3. **Brány:**
   - spojená OOS krivka PF ≥ **1,15**,
   - WFE (OOS výkon / IS výkon) ≥ **0,5**,
   - ≥ **75 %** kúskov v pluse (pri < 4 kúskoch všetky),
   - žiaden parameter sa medzi susednými oknami nezmení o viac ako **½ rozsahu mriežky**.
4. **Zámok:** WF sa pre hypotézu púšťa raz (záznam vo `vaults.json`). Behy WF idú do registra so zdrojom `wf`,
   ale **do N pre DSR sa nepočítajú**.
5. Výstup obsahuje aj denný PnL OOS (pre Sortino v U9).

**Akceptácia:**
- Test na syntetických dátach so známym výsledkom.
- Test zámku.
- Beh na jednej legacy stratégii s reportom.

**Odhad:** 3–4 dni.

---

## U9. Štatistické brány, odolnosť a stav

**Súbory:** `tester/robust.py`, nový `tester/pbo.py`, `tester/montecarlo.py`, `tester/prop.py`, `tester/nulltest.py`,
`.nightsearch/glrobust_missing.py`, nový skript stavu (napr. `.nightsearch/glstav.py`).

Zo smernice je tu všetko s presnými hranicami:

| brána | výpočet | hranica |
|---|---|---|
| N | počet konfigurácií v registri (kroky 4–5, bez WF) | — |
| N_eff | počet zhlukov mesačného PnL všetkých konfigurácií pri \|ρ\| > 0,5, podlaha N/50 | — |
| **DSR** | Bailey & López de Prado (2014), denný PnL na L | ≥ **0,95** pri N_eff **a** ≥ **0,50** pri surovom N |
| **PBO** | CSCV, S = **16** blokov mesačného PnL všetkých konfigurácií | ≤ **0,20** |
| **Haircut** | Harvey & Liu (2015), BHY, N = N_eff (½ N_eff s bonusom za ekonomický dôvod) | ohaircutovaný SR > 0; **PF po haircute < 1,10 → ⏳** |
| break-even náklad | `checkup` na L | ≥ 2× náklad z U4 |
| test proti náhode | `tester.nulltest` | > 95 % (len doplnok) |
| **Sortino** | ročné, z denného PnL (každý pracovný deň, bez obchodu = 0), **len WF OOS a trezory** | ≥ **1,0** |
| plató | každý parameter ±1 krok + 20 náhodných susedov s 2 parametrami | medián susedov ≥ **0,85 × PF**, minimum ≥ **0,70**; vyberá sa stred plató |
| kandidát (krok 4) | na L | PF ≥ **1,25**, žiadny rok L pod **0,95**, ≥ **75 obchodov v každom kalendárnom roku** L (neúplný rok pomerne 75 × mesiace / 12) |
| krok 3 | východisko na L, fill v2 | PF < 0,95 pri ≥ 200 obchodoch → ❌; PF < 1,15 → ďalej nejde |
| odolnosť | 2× náklad; vstup o sviečku neskôr; tercily ATR(20 dní) | PF ≥ 1,05; PF ≥ 1,05 a ≥ 80 % PF; žiadny tercil < 0,90 a žiadny nenesie > 60 % zisku |
| legacy T2 | TP s exit = high/low minúty | ≤ 30 %; PF po vyradení dotykov a +1 tick na SL ≥ 1,10 |

**Trezor (krok 8b):**
- Počet obchodov sa počíta na trh a trezor, trhy sa nesčítavajú.
  - < **150** obchodov → ⏳,
  - 🟡 pri ≥ 150, t ≥ t_req, PF ≥ 1,10 a ≥ 60 % rokov v pluse,
  - ✅ pri ≥ **200**, t ≥ t_req, PF ≥ 1,15, ≥ 60 % rokov v pluse a žiadnom roku pod 0,90.
  - Pri šikmosti R < −1 je potrebných ≥ 250 obchodov a t_req + 0,3.
- **t = min(t z obchodov, t z mesačného PnL)**, kde t = priemer R / σ · √n.
  - Mesačné t sa počíta len pri ≥ 24 mesiacoch, inak t z obchodov s HAC (Newey–West, lag = ⌊4·(n/100)^(2/9)⌋).
- **t_req = Φ⁻¹(1 − 0,025 / k)**, jednostranne s Bonferronim. Kontrolné hodnoty: k = 1 → 1,96, 5 → 2,58, 10 → 2,81,
  20 → 3,02, 50 → 3,29, 100 → 3,48, 160 → 3,61.
  - Úpravy: −0,3 za ekonomický dôvod (podmienky v §2 smernice), +0,5 pri výnimke pod 75 obchodov za rok,
    +0,3 pri šikmosti < −1.
- **Rok A:** PF ≥ 1,0, inak ❌.
- **8c, iný trh:** bez zmeny parametrov, len na L druhého trhu, prahy v ATR alebo %.
  - Príbuzný trh (MNQ ↔ ES ↔ MYM, BTC ↔ ETH perp) PF ≥ 0,95, inak ❌.
  - Iný typ trhu PF ≥ 1,05.
  - Bez príbuzného trhu (MGC, 6E) najviac 🟡.

**Monte Carlo a veľkosť pozície:**
- Blokový bootstrap mesačných blokov trezoru.
- PF_MC = 1 + (PF_obs − 1) / 2, kým n < 300.
- Riziko na obchod ≤ 5 % / p95 DD v R. Horizont = obchody za rok × 2.
- Bez MC je výsledok najviac 🟡.

**Portfólio (krok 11):**
- Denná equita z 1m sviečok a MAE súčasne otvorených pozícií pri skutočných veľkostiach.
- Blokový bootstrap s blokom 5 obchodných dní, **10 000 ciest × 12 mesiacov**.
- Hranice:
  - P(denný pokles ≥ 4 %) ≤ **2 %**,
  - P(DD ≥ 8 %) ≤ **5 %**,
  - súčasné riziko ≤ 1,5 %,
  - najviac 2 stratégie na index v rovnakom časovom okne (MNQ, MYM a ES/US500 sú jeden index),
  - korelácia denného PnL ≤ 0,5,
  - Sortino portfólia z WF OOS a trezorov ≥ 1,0.

**Stav (✅ 🟡 ⏳ ⚠ ❌):**
- Stav počíta len skript z registra a výsledky ukladá do registra.
- **Legacy a hypotézy zo štúdií:** DSR, PBO a haircut sa počítajú a ukazujú, ale len ako informácia. Ich stav je najviac 🟡.
- Prechod na ✅ podpisuje používateľ (záznam v registri s dátumom).

**Akceptácia:**
- Testy DSR, PBO a haircutu proti publikovaným príkladom alebo nezávislej implementácii (tolerancia 1 %).
- Test tabuľky t_req.
- Test stavového automatu na syntetických prípadoch (každá hranica ±ε).

**Odhad:** 4–5 dní.

---

## U10. Webapp, stránka výsledkov a ranné nahrávanie

**Súbory:** `.nightsearch/gldash.py` (dnes radí podľa OOS, `:480–490`), `glwebvyber.py` (zrušiť `APPROVED = {"spravyeur"}`),
`glaudit.py`, `glreport.py`, `glsmernice.py`, `glmorning.sh`, `tester/webapp/static/js/*`, `tester/webapp_vyber.json`.

1. **Stĺpce v každej tabuľke** (webapp, stránka, ranná tabuľka o 6:00, export do iCloudu):
   - stav,
   - PF po nákladoch v2,
   - **PF po haircute**,
   - WR (len informácia),
   - **DSR**, **PBO**,
   - N / N_eff,
   - t na trezore / t_req a k trezoru,
   - Sortino (WF OOS a trezor),
   - obchody za rok,
   - MC 95 % DD dennej equity,
   - **iné trhy** (PF na príbuznom a inom trhu),
   - **posledný rok = rok A**, sivou, len kontrola.
2. **Zobrazenie:**
   - hodnota, ktorá nesplní bránu, je **červená**,
   - nespočítaná hodnota sa zobrazí ako **„—“** (nikdy 0),
   - pri legacy majú DSR, PBO a haircut značku „info“.
3. **Poradie:**
   - najprv stav, potom PF po haircute z L a WF,
   - **nikdy podľa roka A ani trezoru**,
   - titul ani karta Výkon neberú rok A do žiadneho súčtu.
4. **Detail stratégie:** WFE, k trezoru, podiel TP dotykov a dátumy spálenia.
5. **`glaudit`:** trieda A = ✅ V2. Pravidlo „odložený rok PF ≥ 1,4“ sa ruší.
6. **Ranné nahrávanie:** `glsmernice --apply` a `glwebvyber --apply` ostanú vypnuté, kým body 1–3 nefungujú.
   Potom sa zapnú s poradím podľa stavov V2.

**Akceptácia:**
- Snímka webapp a stránky s novými stĺpcami.
- Test, že poradie sa nemení, keď sa zmení len rok A.
- Test „—“ pri chýbajúcej hodnote.
- ESLint prejde.

**Odhad:** 2–3 dni.

---

## U11. Dokumenty

1. `docs/SMERNICA_TESTOVANIA.md` nahradiť obsahom `SMERNICA_V2.md` (iCloud bude obsahovať len odkaz).
2. `CLAUDE.md`:
   - `checkup` a analytika len na L,
   - hľadanie bez trezorov a roka A,
   - fill v2 predvolený,
   - denný stop −4 %.
3. `README.md`: „Kde sme“ a rozcestník.
4. `docs/STRATEGIE.md`: definícia hotového podľa V2 (hlavička, register, brány).

**Odhad:** 0,5 dňa.

---

## U12. Základné profily: čo vyžaduje zmenu kódu (z kontroly A/B/C, `22`–`28`)

1. **23 profilov `ZAKLAD_6E` je neplatných.** Polia `slPoints` (tks a 12 kópií), `targetPoints` (orb15, mtkorb a kópie),
   `trailActivatePoints`/`trailBufferPoints` (flashorb ×4) a `slPts` (mag7) vychádzajú pod dolnú hranicu rozsahu Pine.
   Riešenie: pole presunúť do `SIZE_FIELDS` s jednotkou `ticks`, alebo rozšíriť CONSTRAINTS cez `PORT_ONLY_FIELDS`
   (default zhodný s Pine), v Pythone aj C# s paritou. Potom spustiť
   `docs/audity/2026-11-27-smernica-v2/zaklad_profily/build.py --apply` a overiť, že neplatných je 0.
2. **`scalp3ma` má domovský trh 6E**, ale webapp ju zaraďuje pod NASDAQ (`STRATEGIA_TRH_TYP` v
   `tester/webapp/static/js/settings.js`). Opraviť zaradenie.
3. **ATR pre pomer je denný, nie zo seansy.** Voliteľne prepočítať pomer z ATR seansy (RTH) a porovnať; ak sa líši o
   > 20 %, prejsť na seansový.

**Akceptácia:** 0 neplatných profilov, parita na dotknutých stratégiách, `test_config` prejde.
**Odhad:** 1–2 dni.

## Poradie a odhad

| poradie | úloha | odhad |
|---|---|---|
| 1 | U1 denný stop účtu −4 %, kontrola rizika 1,5 % | 3–5 dní |
| 2 | U2 zápis bid, ask a ms | 1–2 dni |
| 3 | U3 meranie spreadu | 1 deň |
| 4 | U4 fill v2 (futures a CFD), Python a C# | 3–4 dni |
| 5 | U5 rolovanie | 3–4 dni |
| 6 | U6 register a rozpočet | 2 dni |
| 7 | U7 trezory, zámky a počiatočné k | 2 dni |
| 8 | U8 walk-forward | 3–4 dni |
| 9 | U9 štatistika, odolnosť a stav | 4–5 dní |
| 10 | U10 webapp a stránka | 2–3 dni |
| 11 | U11 dokumenty | 0,5 dňa |

**Spolu ~25–33 pracovných dní**, s rezervou 7–9 týždňov.

U1 a U2 smú ísť paralelne s ostatnými. U4 musí byť hotové pred U8 a U9 a U7 pred akýmkoľvek otvorením trezoru.

## Ako to skontrolujeme

Pri každej úlohe:
- prejdú všetky testy, lint a parita z bodu 0,
- skontrolujeme akceptačné kritériá úlohy,
- agenti A, B a C nezávisle prejdú diff proti smernici (`.nightsearch/kritika/`).

Výsledok kontroly dostane vývojár ako zoznam „opravené / chýba / zle“ s odkazom na riadok kódu.
