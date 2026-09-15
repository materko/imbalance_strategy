# 0,5 nastavenia

Kompletný zoznam nastavení profilu **`MNQ_R05_WR80_najlepsi_pomer`** — IBS s pomerom
Risk:Reward 0,5 na MNQ. Uložené 2026-09-14 na vyžiadanie, aby sa dalo kedykoľvek vrátiť.

## Čo to je

| | |
|---|---|
| Stratégia | IBS Imbalance Breakout |
| Trh | MNQ/USD (Databento CME futures) |
| Timeframe | 3m |
| Merané na | 20250904-20260904 (jeden rok) |
| Winrate | **80,5 %** |
| Risk:Reward | 0,5 |
| Očakávanie | +0,24R na obchod |
| Obchodov | 82 (6,8 mesačne) |
| Max drawdown | 670 $ pri riziku 300 $/obchod |
| Najdlhšia séria strát | 2 |
| Ziskových mesiacov | 10 z 12 |

> **Bod zlomu pri RRR 0,5 je 66,7 % winrate.** Pri tomto pomere prehrávaš dvakrát toľko,
> koľko vyhrávaš, takže pod dvoma tretinami úspešnosti je to stratové. Tento profil má
> rezervu ~14 percentuálnych bodov — ale pokles winrate o 14 bodov ho pošle na nulu.

> **Merané na jednom roku.** Pred nasadením overiť na piatich referenčných oknách:
> `python -m tester.webapp.cli checkup --strategy ibs --profile MNQ_R05_WR80_najlepsi_pomer --pair MNQ/USD --timeframe 3m`

## Čo robí väčšinu práce

Tri zmeny, ktoré winrate zdvihli najviac (merané 2026-09-14):

| Zmena | Efekt |
|---|---|
| Min. veľkosť imbalance 2,5 → **6** | +1,8 bodu winrate |
| SL lookback 10 → **20** | +1,6 bodu winrate |
| Min. vzdialenosť SL 0 → **0,25 %** | polovičný drawdown oproti súrodencom |

Základ pri RRR 0,5 bol 75,9 %, s týmito zmenami 80,5 %.

## Kompletný zoznam (114 nastavení)

Hviezdička `*` = líši sa od Pine defaultu.

### 🎯 Obchodovanie

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| IMB entry (imbalance/gap) | **zapnuté** | zapnuté |  |
| Pin Bar entry | **zapnuté** | vypnuté | * |
| Engulfing entry | **vypnuté** | vypnuté |  |
| Pin Bar: Min. pomer knôt/telo | **4.0** | 4.0 |  |
| Pin Bar: Max. poloha tela v rozsahu (%) | **20.0** | 20.0 |  |
| Pin Bar: Min. celkový rozsah sviečky (body) | **2.0** | 2.0 |  |
| Engulfing: Min. celkový rozsah sviečky (body) | **2.0** | 2.0 |  |
| Engulfing: Dĺžka priemeru rozsahu (bary) | **10** | 10 |  |
| Engulfing: Násobok priemerného rozsahu | **2.0** | 2.0 |  |
| Engulfing: Max. barov po dotyku zóny | **3** | 3 |  |
| Pin Bar/Engulfing: Typ príkazu | **Market** | Market |  |
| Zapnúť trailing stop | **vypnuté** | vypnuté |  |
| Aktivácia trailingu (R-násobok rizika) | **1.0** | 1.0 |  |
| Trailing vzdialenosť (R-násobok rizika) | **0.5** | 0.5 |  |
| Zapnut detekciu SD zon | **zapnuté** | zapnuté |  |
| Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | **zapnuté** | vypnuté | * |
| Obchoduj z likviditných zón (sweep) | **zapnuté** | vypnuté | * |
| Risk:Reward pomer | **0.5** | 1.0 | * |
| Smer obchodov | **Both** | Both |  |

### ⚙️ Základné nastavenia

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Obchoduj len Pondelok-Piatok | **zapnuté** | zapnuté |  |
| Zapnut obchodovanie (strategia posiela ordre) | **zapnuté** | zapnuté |  |
| Zatvor vsetky pozicie na konci session | **vypnuté** | zapnuté | * |

### 📦 SD Zony

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zapnut hladanie gapu vnutri zony | **zapnuté** | zapnuté |  |
| SD zona - detekcny TF (z akeho TF sa hlada pattern) | **3** | 5 | * |
| Platnost zony (hodiny) | **6** | 6 |  |
| Max SD zon | **200** | 200 |  |
| Snap casu zony na TF grid | **Floor** | Floor |  |
| Invaliduj zonu pri vyplneni orderu | **zapnuté** | zapnuté |  |
| Zapnúť volume filter (SD zóny) | **vypnuté** | vypnuté |  |
| Aj blokovať slabé (nízky volume) zóny | **vypnuté** | vypnuté |  |
| Volume: priemer za N sviečok | **20** | 20 |  |
| Volume: min. násobok priemeru pre 'silnú' zónu | **1.5** | 1.5 |  |
| Max barov dozadu pre IMB | **30** | 20 | * |
| Max vzdialenost IMB od zony (ticky) | **100.0** | 100.0 |  |
| Min. velkost imbalance (body/points) | **6** | 2.5 | * |

### 🌏 Session 1 (Azia)

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zapnúť | **vypnuté** | vypnuté |  |
| Časové pásmo | **Europe/Prague** | Europe/Prague |  |
| SD zona zaciatok (H) | **1** | 1 |  |
| M | **0** | 0 |  |
| SD zona koniec (H) | **9** | 9 |  |
| M | **0** | 0 |  |
| Trade zaciatok (H) | **2** | 2 |  |
| M | **0** | 0 |  |
| Trade koniec (H) | **5** | 5 |  |
| M | **0** | 0 |  |

### 📘 Session 2

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zapnúť | **zapnuté** | zapnuté |  |
| Časové pásmo | **America/New_York** | America/New_York |  |
| SD zona zaciatok (H) | **5** | 10 | * |
| M | **0** | 0 |  |
| SD zona koniec (H) | **11** | 11 |  |
| M | **0** | 0 |  |
| Trade zaciatok (H) | **10** | 10 |  |
| M | **0** | 0 |  |
| Trade koniec (H) | **15** | 15 |  |
| M | **45** | 45 |  |

### 📙 Session 3

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zapnúť | **vypnuté** | zapnuté | * |
| Časové pásmo | **Europe/London** | Europe/London |  |
| SD zona zaciatok (H) | **8** | 8 |  |
| M | **0** | 0 |  |
| SD zona koniec (H) | **11** | 10 | * |
| M | **0** | 0 |  |
| Trade zaciatok (H) | **8** | 8 |  |
| M | **0** | 0 |  |
| Trade koniec (H) | **12** | 11 | * |
| M | **0** | 0 |  |

### 📈 Market Structure

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zobraz strukturu trhu (BOS/CHoCH) | **zapnuté** | zapnuté |  |
| Swing lookback (barov na kazdu stranu) | **5** | 5 |  |
| Obchoduj len v smere struktury (BOS/CHoCH filter) | **vypnuté** | vypnuté |  |

### 📏 Support/Resistance

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zobraz support/resistance | **zapnuté** | zapnuté |  |
| Swing lookback pre S/R (barov na kazdu stranu) | **10** | 10 |  |
| Zhlukovanie urovni (body/points) | **15.0** | 15.0 |  |
| Min. pocet dotykov aby sa uroven zobrazila | **2** | 2 |  |
| Max pocet zobrazenych urovni | **10** | 10 |  |
| Zobrazuj urovne len za poslednych X dni | **5** | 5 |  |
| Sýtosť farby zóny (%) | **30** | 30 |  |

### 💧 Likvidita (Sweep)

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zobraz liquidity sweep (stop hunt) | **zapnuté** | zapnuté |  |
| Swing lookback pre likviditu (barov na kazdu stranu) | **10** | 10 |  |
| Min. velkost prepichnutia (body/points) | **5.0** | 5.0 |  |
| Potvrdenie navratu do X barov | **2** | 2 |  |
| Sila pivotu - okolie (barov) | **50** | 50 |  |

### 🌊 Elliott Waves

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zobraz Elliott Waves (zapnut/vypnut) | **vypnuté** | zapnuté | * |
| Swing lookback pre zigzag (barov na kazdu stranu) | **8** | 8 |  |
| Min. velkost vlny (body/points) | **20.0** | 20.0 |  |
| Zobraz cislovanie vln (0-1-2-3-4-5) | **zapnuté** | zapnuté |  |
| Zobraz projekciu dalsej vlny (cielova zona) | **zapnuté** | zapnuté |  |
| O kolko barov dopredu kreslit projekcnu zonu | **40** | 40 |  |
| Farba ciar a popisov vln | **#334155** | #334155 |  |

### 🎨 Vizualizacia

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Zobraz imbalance sviecky | **zapnuté** | zapnuté |  |
| Zobraz dashboard panel | **zapnuté** | zapnuté |  |
| Pozicia panelu | **Top Right** | Top Right |  |
| Pocet statistickych dlazdic (Obchody, Seria, ...) | **6** | 6 |  |
| Zobraz tabulku obchodov v paneli (Entry/SL/TP) | **vypnuté** | vypnuté |  |
| Pocet riadkov v tabulke obchodov (max 20) | **20** | 20 |  |
| Zobraz pokročilý diagnostický panel | **vypnuté** | vypnuté |  |
| Počet riadkov v diagnostickom paneli | **8** | 8 |  |
| Pozícia diagnostického panelu | **Bottom Right** | Bottom Right |  |

### 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| IMB model: Max. barov na výstup zo zóny | **5** | 10 | * |
| IMB model: Max. barov na potvrdenie | **10** | 15 | * |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | **0** | 1.0 | * |
| IMB model: Max. barov na retest | **3** | 1 | * |
| Rezerva (aktuálne nepoužívané) | **10** | 10 |  |
| Max. barov čakania na vyplnenie orderu | **5** | 10 | * |
| Alert: cena opustila zónu (skorý signál) | **vypnuté** | vypnuté |  |
| Alert: cena sa vrátila na vstupnú úroveň | **vypnuté** | vypnuté |  |
| Alert: order umiestnený (E/SL/TP) | **vypnuté** | vypnuté |  |
| SL: lookback barov od aktualnej sviecky | **20** | 10 | * |
| SL: buffer (ticky) | **6** | 2.0 | * |

### 💰 Veľkosť pozície a riziko

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Max strata ($, 0 = vypnute) | **1000** | 350.0 | * |
| Max ziskovych tradov za den | **5** | 5 |  |
| Hodnota jedneho ticku ($) | **0.5** | — | * |

### 🧩 Rozšírenia portu

| Nastavenie | Hodnota | Default | |
|---|---|---|---|
| Pine sizing (1 kontrakt/BTC, ako TradingView) | **vypnuté** | vypnuté |  |
| ATR dĺžka pre jednotku „atr“ | **14** | 14 |  |
| Min. vzdialenosť SL od vstupu | **0.25 pct** | 0.0 | * |
| Páka | **1.0** | 1.0 |  |

*Spolu 114 nastavení.*

## Súvisiace profily

| Profil | WR | Obch./mes | Očak. | Max DD | Séria strát |
|---|---|---|---|---|---|
| **MNQ_R05_WR80_najlepsi_pomer** (tento) | 80,5 % | 6,8 | +0,24R | 670 | 2 |
| MNQ_R05_WR80_najviac | 80,8 % | 10,4 | +0,21R | 1 079 | 3 |
| MNQ_R05_WR80_najzisk | 80,3 % | 10,6 | +0,22R | 1 118 | 3 |
| MNQ_R05_WR797_jednoduchy | 79,7 % | 10,2 | +0,21R | 1 122 | 3 |
