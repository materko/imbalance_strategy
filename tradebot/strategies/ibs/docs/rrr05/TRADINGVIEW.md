# MNQ_R05_WR80_najlepsi_pomer — na prepísanie do TradingView

IBS Imbalance Breakout · **MNQ · 3m** · RRR 0,5 → **80,5 % WR**, +0,24R na obchod,
max DD 670 $ (pri riziku 300 $/obchod), najdlhšia séria strát 2, 82 obchodov za rok.
Merané na 20250904–20260904, emulátor MultiCharts, bez nákladov.

Poradie aj názvy sedia s panelom **Inputs** v TradingView. Vstupov je 115,
**21 sa líši od defaultu** — v úplnom zozname majú šípku ←.

## Rýchla verzia — 21 vstupov, ktoré treba prestaviť

Ak otváraš čistý skript, stačí zmeniť toto. Zvyšných 94 vstupov nechaj na defaulte.

| Skupina | Nastavenie | Z | Na |
|---|---|---|---|
| 🎯 Obchodovanie | Pin Bar entry | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | Obchoduj z likviditných zón (sweep) | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | Risk:Reward pomer | 1.0 | **0.5** |
| ⚙️ Základné nastavenia | Zatvor vsetky pozicie na konci session | ✅ ZAP | **⬜ VYP** |
| 📦 SD Zony | SD zona - detekcny TF (z akeho TF sa hlada pattern) | 5 | **3** |
| 📦 SD Zony | Max barov dozadu pre IMB | 20 | **30** |
| 📦 SD Zony | Min. velkost imbalance (body/points) | 2.5 | **6** |
| 📘 Session 2 | SD zona zaciatok (H) | 10 | **5** |
| 📙 Session 3 | Zapnúť | ✅ ZAP | **⬜ VYP** |
| 📙 Session 3 | SD zona koniec (H) | 10 | **11** |
| 📙 Session 3 | Trade koniec (H) | 11 | **12** |
| 🌊 Elliott Waves | Zobraz Elliott Waves (zapnut/vypnut) | ✅ ZAP | **⬜ VYP** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na výstup zo zóny | 10 | **5** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na potvrdenie | 15 | **10** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Potvrdenie (ticky nad/pod IMB telom) | 1 | **0** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na retest | 1 | **3** |
| 🔧 Pokročilé (časovanie vstupu, SL) | Max. barov čakania na vyplnenie orderu | 10 | **5** |
| 🔧 Pokročilé (časovanie vstupu, SL) | SL: lookback barov od aktualnej sviecky | 10 | **20** |
| 🔧 Pokročilé (časovanie vstupu, SL) | SL: buffer (ticky) | 2 | **6** |
| 💰 Veľkosť pozície a riziko | Max strata ($, 0 = vypnute) | 350 | **1000** |

---

## Úplný zoznam (115 vstupov, v poradí panela)

### 🎯 Obchodovanie

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| IMB entry (imbalance/gap) | **✅ ZAP** | ✅ ZAP |
| Pin Bar entry | **✅ ZAP**  ← | ⬜ VYP |
| Engulfing entry | **⬜ VYP** | ⬜ VYP |
| Pin Bar: Min. pomer knôt/telo | **4** | 4.0 |
| Pin Bar: Max. poloha tela v rozsahu (%) | **20** | 20 |
| Pin Bar: Min. celkový rozsah sviečky (body) | **2** | 2 |
| Engulfing: Min. celkový rozsah sviečky (body) | **2** | 2 |
| Engulfing: Dĺžka priemeru rozsahu (bary) | **10** | 10 |
| Engulfing: Násobok priemerného rozsahu | **2** | 2.0 |
| Engulfing: Max. barov po dotyku zóny | **3** | 3 |
| Pin Bar/Engulfing: Typ príkazu | **Market** | Market |
| Zapnúť trailing stop | **⬜ VYP** | ⬜ VYP |
| Aktivácia trailingu (R-násobok rizika) | **1** | 1.0 |
| Trailing vzdialenosť (R-násobok rizika) | **0.5** | 0.5 |
| PickMyTrade: frekvencia update SL (% z trailing vzdialenosti) | _nechaj tak_ | 25 |
| Zapnut detekciu SD zon | **✅ ZAP** | ✅ ZAP |
| Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | **✅ ZAP**  ← | ⬜ VYP |
| Obchoduj z likviditných zón (sweep) | **✅ ZAP**  ← | ⬜ VYP |
| Risk:Reward pomer | **0.5**  ← | 1.0 |
| Smer obchodov | **Both** | Both |

### ⚙️ Základné nastavenia

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Obchoduj len Pondelok-Piatok | **✅ ZAP** | ✅ ZAP |
| Zapnut obchodovanie (strategia posiela ordre) | **✅ ZAP** | ✅ ZAP |
| Zatvor vsetky pozicie na konci session | **⬜ VYP**  ← | ✅ ZAP |

### 📦 SD Zony

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zapnut hladanie gapu vnutri zony | **✅ ZAP** | ✅ ZAP |
| SD zona - detekcny TF (z akeho TF sa hlada pattern) | **3**  ← | 5 |
| Platnost zony (hodiny) | **6** | 6 |
| Max SD zon | **200** | 200 |
| Snap casu zony na TF grid | **Floor** | Floor |
| Invaliduj zonu pri vyplneni orderu | **✅ ZAP** | ✅ ZAP |
| Zapnúť volume filter (SD zóny) | **⬜ VYP** | ⬜ VYP |
| Aj blokovať slabé (nízky volume) zóny | **⬜ VYP** | ⬜ VYP |
| Volume: priemer za N sviečok | **20** | 20 |
| Volume: min. násobok priemeru pre 'silnú' zónu | **1.5** | 1.5 |
| Max barov dozadu pre IMB | **30**  ← | 20 |
| Max vzdialenost IMB od zony (ticky) | **100** | 100 |
| Min. velkost imbalance (body/points) | **6**  ← | 2.5 |

### 🌏 Session 1 (Azia)

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zapnúť | **⬜ VYP** | ⬜ VYP |
| Časové pásmo | **Europe/Prague** | Europe/Prague |
| SD zona zaciatok (H) | **1** | 1 |
| M | **0** | 0 |
| SD zona koniec (H) | **9** | 9 |
| M | **0** | 0 |
| Trade zaciatok (H) | **2** | 2 |
| M | **0** | 0 |
| Trade koniec (H) | **5** | 5 |
| M | **0** | 0 |

### 📘 Session 2

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zapnúť | **✅ ZAP** | ✅ ZAP |
| Časové pásmo | **America/New_York** | America/New_York |
| SD zona zaciatok (H) | **5**  ← | 10 |
| M | **0** | 0 |
| SD zona koniec (H) | **11** | 11 |
| M | **0** | 0 |
| Trade zaciatok (H) | **10** | 10 |
| M | **0** | 0 |
| Trade koniec (H) | **15** | 15 |
| M | **45** | 45 |

### 📙 Session 3

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zapnúť | **⬜ VYP**  ← | ✅ ZAP |
| Časové pásmo | **Europe/London** | Europe/London |
| SD zona zaciatok (H) | **8** | 8 |
| M | **0** | 0 |
| SD zona koniec (H) | **11**  ← | 10 |
| M | **0** | 0 |
| Trade zaciatok (H) | **8** | 8 |
| M | **0** | 0 |
| Trade koniec (H) | **12**  ← | 11 |
| M | **0** | 0 |

### 📈 Market Structure

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zobraz strukturu trhu (BOS/CHoCH) | **✅ ZAP** | ✅ ZAP |
| Swing lookback (barov na kazdu stranu) | **5** | 5 |
| Obchoduj len v smere struktury (BOS/CHoCH filter) | **⬜ VYP** | ⬜ VYP |

### 📏 Support/Resistance

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zobraz support/resistance | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre S/R (barov na kazdu stranu) | **10** | 10 |
| Zhlukovanie urovni (body/points) | **15** | 15 |
| Min. pocet dotykov aby sa uroven zobrazila | **2** | 2 |
| Max pocet zobrazenych urovni | **10** | 10 |
| Zobrazuj urovne len za poslednych X dni | **5** | 5 |
| Sýtosť farby zóny (%) | **30** | 30 |

### 💧 Likvidita (Sweep)

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zobraz liquidity sweep (stop hunt) | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre likviditu (barov na kazdu stranu) | **10** | 10 |
| Min. velkost prepichnutia (body/points) | **5** | 5 |
| Potvrdenie navratu do X barov | **2** | 2 |
| Sila pivotu - okolie (barov) | **50** | 50 |

### 🌊 Elliott Waves

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zobraz Elliott Waves (zapnut/vypnut) | **⬜ VYP**  ← | ✅ ZAP |
| Swing lookback pre zigzag (barov na kazdu stranu) | **8** | 8 |
| Min. velkost vlny (body/points) | **20** | 20 |
| Zobraz cislovanie vln (0-1-2-3-4-5) | **✅ ZAP** | ✅ ZAP |
| Zobraz projekciu dalsej vlny (cielova zona) | **✅ ZAP** | ✅ ZAP |
| O kolko barov dopredu kreslit projekcnu zonu | **40** | 40 |
| Farba ciar a popisov vln | **#334155** | #334155 |

### 🎨 Vizualizacia

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Zobraz imbalance sviecky | **✅ ZAP** | ✅ ZAP |
| Zobraz dashboard panel | **✅ ZAP** | ✅ ZAP |
| Pozicia panelu | **Top Right** | Top Right |
| Pocet statistickych dlazdic (Obchody, Seria, ...) | **6** | 6 |
| Zobraz tabulku obchodov v paneli (Entry/SL/TP) | **⬜ VYP** | ⬜ VYP |
| Pocet riadkov v tabulke obchodov (max 20) | **20** | 20 |
| Zobraz pokročilý diagnostický panel | **⬜ VYP** | ⬜ VYP |
| Počet riadkov v diagnostickom paneli | **8** | 8 |
| Pozícia diagnostického panelu | **Bottom Right** | Bottom Right |

### 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| IMB model: Max. barov na výstup zo zóny | **5**  ← | 10 |
| IMB model: Max. barov na potvrdenie | **10**  ← | 15 |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | **0**  ← | 1 |
| IMB model: Max. barov na retest | **3**  ← | 1 |
| Rezerva (aktuálne nepoužívané) | **10** | 10 |
| Max. barov čakania na vyplnenie orderu | **5**  ← | 10 |
| Alert: cena opustila zónu (skorý signál) | **⬜ VYP** | ⬜ VYP |
| Alert: cena sa vrátila na vstupnú úroveň | **⬜ VYP** | ⬜ VYP |
| Alert: order umiestnený (E/SL/TP) | **⬜ VYP** | ⬜ VYP |
| SL: lookback barov od aktualnej sviecky | **20**  ← | 10 |
| SL: buffer (ticky) | **6**  ← | 2 |

### 💰 Veľkosť pozície a riziko

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Max strata ($, 0 = vypnute) | **1000**  ← | 350 |
| Hodnota jedneho ticku ($) | **0.5** | 0.5 |
| Max ziskovych tradov za den | **5** | 5 |

### 🔗 PickMyTrade

| Nastavenie (presne ako v paneli Inputs) | Nastav na | Default |
|---|---|---|
| Token | _nechaj tak_ |  |
| Account ID | _nechaj tak_ |  |
| Strategy name | _nechaj tak_ |  |
| 'order_type' hodnota pre MARKET príkaz | _nechaj tak_ | MKT |

---

## Čo v TradingView nastaviť nejde

Tri polia profilu Pine skript **nemá** — sú to rozšírenia portu:

| Pole | V profile | Čo s tým v TradingView |
|---|---|---|
| **Min. vzdialenosť SL od vstupu** | **0,25 %** | nedá sa — obchody s tesným stopom sa **nepreskočia** |
| Hodnota ticku ($) | 0,5 | Pine si ju berie zo `syminfo`, nezadáva sa |
| Páka | 1,0 | Pine páku nemá |

**To prvé má dôsledok, nie je to formalita.** `minSlDistance = 0,25 %` bola jedna z troch
zmien, ktoré držali pokles na polovici oproti súrodencom. TradingView teda urobí **viac
obchodov** a s **väčším poklesom** než tu nameraných 670 $. Keď sa počty obchodov rozídu,
toto je prvé miesto, kam sa pozrieť.

Pine vstupy `trailFreqPct` a štyri `pmt*` (webhook na brokera) port vedome nemá — nechaj
ich tak, na signály nemajú vplyv.

## Na čo nezabudnúť pred spustením

- graf musí byť **MNQ**, timeframe **3m**
- obchoduje sa **len Session 2** (New York): zóny od 5:00, obchody 10:00–15:45 NY
- **Session 1 aj Session 3 sú vypnuté** — Session 3 je v Pine defaultne zapnutá, na to sa
  ľahko zabudne a sama od seba pridá obchody, ktoré v tomto meraní nie sú
- **Zatváranie pozícií na konci seansy je vypnuté** (default je zapnuté)

## Hranica, ktorá k tomuto číslu patrí

Pri RRR 0,5 je **bod zlomu 66,7 % winrate** — prehrávaš dvakrát toľko, koľko vyhrávaš.
Rezerva je ~14 percentuálnych bodov a pokles winrate o 14 bodov pošle výsledok na nulu.
Merané je to na **jednom roku**; na piatich referenčných oknách overené nie je.
