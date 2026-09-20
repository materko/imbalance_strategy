# NOCNE_TESTY_B_stabilita — nastavenia zo stratégie

Všetkých **127 nastavení** tak, ako ich definuje stratégia IBS a ako ich ukazuje
formulár vo webapp — rovnaké poradie, rovnaké názvy. Jeden zoznam, bez delenia na
„Pine" a „rozšírenia portu".

IBS Imbalance Breakout · **MNQ/USD (Databento CME futures)** · **3m** · **RRR 0,5**

| | |
|---|---|
| Winrate posledný rok | **80,33 %** |
| Winrate 5 rokov | **71,81 %** |
| Obchodov | 244 za posledný rok / 232 ročne cez 5 rokov |
| Profit factor | 1,97 |
| Zisková | **5 z 5 referenčných okien** |
| S/R úrovne + likvidita (sweep) | **vypnuté** |
| Merané na | 20250904–20260904, emulátor MultiCharts, bez nákladov |
| Beh | `20260917-025501-38692e` |

**Najdôležitejší jediný riadok: `Smer obchodov = Indicator`.** Keď tam ostane `Both`,
pravidlá ADX sa vôbec neuplatnia — aj keď sú vyplnené — a z profilu sa ticho stane niečo
iné. Celý jeho edge je v pravidle **„ADX do strany → No trade"**: neobchoduje sa, keď
trh stojí.

**Bod zlomu pri RRR 0,5 je 66,7 % winrate.** Na piatich rokoch má profil 71,81 %, teda
rezervu 5,1 percentuálneho bodu.

## Načítanie v Testeri

Vo webapp je pod menom **NOCNE_TESTY_B_stabilita**. Z CLI:

```bash
.venv/bin/python -m tester.webapp.cli run --strategy ibs --profile NOCNE_TESTY_B_stabilita --pair MNQ/USD --timeframe 3m --timerange 20250904-20260904 --note "kontrola B"
```


## Rýchla verzia — čo sa líši od defaultu stratégie

Zo 127 nastavení sa líši **51**. Zvyšok nechaj tak.

| Skupina | Nastavenie | Z | Na |
|---|---|---|---|
| 🎯 Obchodovanie | Pin Bar entry | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | Engulfing entry | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | Pin Bar: Min. pomer knôt/telo | 4 | **5** |
| 🎯 Obchodovanie | Engulfing: Min. celkový rozsah sviečky (body) | 2 | **6** |
| 🎯 Obchodovanie | Risk:Reward pomer | 1 | **0.5** |
| 🎯 Obchodovanie | Smer obchodov | Both | **Indicator** |
| 🎯 Obchodovanie | Indikátor: Supertrend | ✅ ZAP | **⬜ VYP** |
| 🎯 Obchodovanie | Supertrend: TF výpočtu | 60 | **240** |
| 🎯 Obchodovanie | Supertrend: ATR Period | 10 | **14** |
| 🎯 Obchodovanie | Supertrend: ATR Multiplier | 3 | **3.5** |
| 🎯 Obchodovanie | Indikátor: ADX/DMI | ⬜ VYP | **✅ ZAP** |
| 🎯 Obchodovanie | ADX/DMI: ADX Smoothing | 14 | **7** |
| 🎯 Obchodovanie | ADX/DMI: prah trendu (pod = do strany) | 20 | **12** |
| 🎯 Obchodovanie | Pravidlo: ADX hore → | Long only | **Both** |
| 🎯 Obchodovanie | Pravidlo: ADX dole → | Short only | **Both** |
| ⚙️ Základné nastavenia | Zatvor vsetky pozicie na konci session | ✅ ZAP | **⬜ VYP** |
| 📦 SD Zony | SD zona - detekcny TF (z akeho TF sa hlada pattern) | 5 | **3** |
| 📦 SD Zony | Platnost zony (hodiny) | 6 | **2** |
| 📦 SD Zony | Max barov dozadu pre IMB | 20 | **5** |
| 📦 SD Zony | Max vzdialenost IMB od zony (ticky) | 100 ticks | **40** |
| 📦 SD Zony | Min. velkost imbalance (body/points) | 2.5 | **9** |
| 🌏 Session 1 (Azia) | Zapnúť | ⬜ VYP | **✅ ZAP** |
| 🌏 Session 1 (Azia) | Časové pásmo | Europe/Prague | **America/New_York** |
| 🌏 Session 1 (Azia) | SD zona zaciatok (H) | 1 | **0** |
| 🌏 Session 1 (Azia) | SD zona koniec (H) | 9 | **3** |
| 🌏 Session 1 (Azia) | Trade zaciatok (H) | 2 | **0** |
| 🌏 Session 1 (Azia) | Trade koniec (H) | 5 | **3** |
| 📘 Session 2 | SD zona zaciatok (H) | 10 | **18** |
| 📘 Session 2 | SD zona koniec (H) | 11 | **17** |
| 📘 Session 2 | Trade zaciatok (H) | 10 | **9** |
| 📘 Session 2 | M | 0 | **30** |
| 📘 Session 2 | Trade koniec (H) | 15 | **16** |
| 📘 Session 2 | M | 45 | **0** |
| 📙 Session 3 | Časové pásmo | Europe/London | **America/New_York** |
| 📙 Session 3 | SD zona zaciatok (H) | 8 | **14** |
| 📙 Session 3 | SD zona koniec (H) | 10 | **16** |
| 📙 Session 3 | Trade zaciatok (H) | 8 | **14** |
| 📙 Session 3 | Trade koniec (H) | 11 | **17** |
| 💧 Likvidita (Sweep) | Swing lookback pre likviditu (barov na kazdu stranu) | 10 | **5** |
| 💧 Likvidita (Sweep) | Min. velkost prepichnutia (body/points) | 5 | **10** |
| 💧 Likvidita (Sweep) | Potvrdenie navratu do X barov | 2 | **1** |
| 🌊 Elliott Waves | Zobraz Elliott Waves (zapnut/vypnut) | ✅ ZAP | **⬜ VYP** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na výstup zo zóny | 10 | **1** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na potvrdenie | 15 | **10** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Potvrdenie (ticky nad/pod IMB telom) | 1 ticks | **4** |
| 🔧 Pokročilé (časovanie vstupu, SL) | IMB model: Max. barov na retest | 1 | **3** |
| 🔧 Pokročilé (časovanie vstupu, SL) | Max. barov čakania na vyplnenie orderu | 10 | **2** |
| 🔧 Pokročilé (časovanie vstupu, SL) | SL: buffer (ticky) | 2 ticks | **0** |
| 💰 Veľkosť pozície a riziko | Max strata ($, 0 = vypnute) | 350 | **1000** |
| 💰 Veľkosť pozície a riziko | Hodnota jedneho ticku ($) | — | **0.5** |
| 🧩 Rozšírenia portu | Min. vzdialenosť SL od vstupu | 0 pct | **0.13** |

---

## Úplný zoznam

### 🎯 Obchodovanie

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| IMB entry (imbalance/gap) | **✅ ZAP** | ✅ ZAP |
| Pin Bar entry | **✅ ZAP**  ← | ⬜ VYP |
| Engulfing entry | **✅ ZAP**  ← | ⬜ VYP |
| Pin Bar: Min. pomer knôt/telo | **5**  ← | 4 |
| Pin Bar: Max. poloha tela v rozsahu (%) | **20** | 20 |
| Pin Bar: Min. celkový rozsah sviečky (body) | **2** | 2 |
| Engulfing: Min. celkový rozsah sviečky (body) | **6**  ← | 2 |
| Engulfing: Dĺžka priemeru rozsahu (bary) | **10** | 10 |
| Engulfing: Násobok priemerného rozsahu | **2** | 2 |
| Engulfing: Max. barov po dotyku zóny | **3** | 3 |
| Pin Bar/Engulfing: Typ príkazu | **Market** | Market |
| Zapnúť trailing stop | **⬜ VYP** | ⬜ VYP |
| Aktivácia trailingu (R-násobok rizika) | **1** | 1 |
| Trailing vzdialenosť (R-násobok rizika) | **0.5** | 0.5 |
| Zapnut detekciu SD zon | **✅ ZAP** | ✅ ZAP |
| Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | **⬜ VYP** | ⬜ VYP |
| Obchoduj z likviditných zón (sweep) | **⬜ VYP** | ⬜ VYP |
| Risk:Reward pomer | **0.5**  ← | 1 |
| Smer obchodov | **Indicator**  ← | Both |
| Indikátor: Supertrend | **⬜ VYP**  ← | ✅ ZAP |
| Supertrend: TF výpočtu | **240**  ← | 60 |
| Supertrend: ATR Period | **14**  ← | 10 |
| Supertrend: Source | **hl2** | hl2 |
| Supertrend: ATR Multiplier | **3.5**  ← | 3 |
| Supertrend: Change ATR Calculation Method | **✅ ZAP** | ✅ ZAP |
| Supertrend: Show Buy/Sell Signals | **✅ ZAP** | ✅ ZAP |
| Supertrend: Highlighter | **✅ ZAP** | ✅ ZAP |
| Indikátor: ADX/DMI | **✅ ZAP**  ← | ⬜ VYP |
| ADX/DMI: TF výpočtu | **60** | 60 |
| ADX/DMI: DI Length | **14** | 14 |
| ADX/DMI: ADX Smoothing | **7**  ← | 14 |
| ADX/DMI: prah trendu (pod = do strany) | **12**  ← | 20 |
| ADX/DMI: podfarbiť graf podľa stavu | **✅ ZAP** | ✅ ZAP |
| Pravidlo: Supertrend hore → | **Long only** | Long only |
| Pravidlo: Supertrend dole → | **Short only** | Short only |
| Pravidlo: ADX hore → | **Both**  ← | Long only |
| Pravidlo: ADX dole → | **Both**  ← | Short only |
| Pravidlo: ADX do strany → | **No trade** | No trade |
| Pravidlo: Supertrend hore + ADX hore → | **Long only** | Long only |
| Pravidlo: Supertrend hore + ADX do strany → | **No trade** | No trade |
| Pravidlo: Supertrend hore + ADX dole → | **No trade** | No trade |
| Pravidlo: Supertrend dole + ADX hore → | **No trade** | No trade |
| Pravidlo: Supertrend dole + ADX do strany → | **No trade** | No trade |
| Pravidlo: Supertrend dole + ADX dole → | **Short only** | Short only |

### ⚙️ Základné nastavenia

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Obchoduj len Pondelok-Piatok | **✅ ZAP** | ✅ ZAP |
| Zapnut obchodovanie (strategia posiela ordre) | **✅ ZAP** | ✅ ZAP |
| Zatvor vsetky pozicie na konci session | **⬜ VYP**  ← | ✅ ZAP |

### 📦 SD Zony

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zapnut hladanie gapu vnutri zony | **✅ ZAP** | ✅ ZAP |
| SD zona - detekcny TF (z akeho TF sa hlada pattern) | **3**  ← | 5 |
| Platnost zony (hodiny) | **2**  ← | 6 |
| Max SD zon | **200** | 200 |
| Snap casu zony na TF grid | **Floor** | Floor |
| Invaliduj zonu pri vyplneni orderu | **✅ ZAP** | ✅ ZAP |
| Zapnúť volume filter (SD zóny) | **⬜ VYP** | ⬜ VYP |
| Aj blokovať slabé (nízky volume) zóny | **⬜ VYP** | ⬜ VYP |
| Volume: priemer za N sviečok | **20** | 20 |
| Volume: min. násobok priemeru pre 'silnú' zónu | **1.5** | 1.5 |
| Max barov dozadu pre IMB | **5**  ← | 20 |
| Max vzdialenost IMB od zony (ticky) | **40**  ← | 100 ticks |
| Min. velkost imbalance (body/points) | **9**  ← | 2.5 |

### 🌏 Session 1 (Azia)

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zapnúť | **✅ ZAP**  ← | ⬜ VYP |
| Časové pásmo | **America/New_York**  ← | Europe/Prague |
| SD zona zaciatok (H) | **0**  ← | 1 |
| M | **0** | 0 |
| SD zona koniec (H) | **3**  ← | 9 |
| M | **0** | 0 |
| Trade zaciatok (H) | **0**  ← | 2 |
| M | **0** | 0 |
| Trade koniec (H) | **3**  ← | 5 |
| M | **0** | 0 |

### 📘 Session 2

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zapnúť | **✅ ZAP** | ✅ ZAP |
| Časové pásmo | **America/New_York** | America/New_York |
| SD zona zaciatok (H) | **18**  ← | 10 |
| M | **0** | 0 |
| SD zona koniec (H) | **17**  ← | 11 |
| M | **0** | 0 |
| Trade zaciatok (H) | **9**  ← | 10 |
| M | **30**  ← | 0 |
| Trade koniec (H) | **16**  ← | 15 |
| M | **0**  ← | 45 |

### 📙 Session 3

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zapnúť | **✅ ZAP** | ✅ ZAP |
| Časové pásmo | **America/New_York**  ← | Europe/London |
| SD zona zaciatok (H) | **14**  ← | 8 |
| M | **0** | 0 |
| SD zona koniec (H) | **16**  ← | 10 |
| M | **0** | 0 |
| Trade zaciatok (H) | **14**  ← | 8 |
| M | **0** | 0 |
| Trade koniec (H) | **17**  ← | 11 |
| M | **0** | 0 |

### 📈 Market Structure

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zobraz strukturu trhu (BOS/CHoCH) | **✅ ZAP** | ✅ ZAP |
| Swing lookback (barov na kazdu stranu) | **5** | 5 |
| Obchoduj len v smere struktury (BOS/CHoCH filter) | **⬜ VYP** | ⬜ VYP |

### 📏 Support/Resistance

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zobraz support/resistance | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre S/R (barov na kazdu stranu) | **10** | 10 |
| Zhlukovanie urovni (body/points) | **15** | 15 |
| Min. pocet dotykov aby sa uroven zobrazila | **2** | 2 |
| Max pocet zobrazenych urovni | **10** | 10 |
| Zobrazuj urovne len za poslednych X dni | **5** | 5 |
| Sýtosť farby zóny (%) | **30** | 30 |

### 💧 Likvidita (Sweep)

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zobraz liquidity sweep (stop hunt) | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre likviditu (barov na kazdu stranu) | **5**  ← | 10 |
| Min. velkost prepichnutia (body/points) | **10**  ← | 5 |
| Potvrdenie navratu do X barov | **1**  ← | 2 |
| Sila pivotu - okolie (barov) | **50** | 50 |

### 🌊 Elliott Waves

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zobraz Elliott Waves (zapnut/vypnut) | **⬜ VYP**  ← | ✅ ZAP |
| Swing lookback pre zigzag (barov na kazdu stranu) | **8** | 8 |
| Min. velkost vlny (body/points) | **20** | 20 |
| Zobraz cislovanie vln (0-1-2-3-4-5) | **✅ ZAP** | ✅ ZAP |
| Zobraz projekciu dalsej vlny (cielova zona) | **✅ ZAP** | ✅ ZAP |
| O kolko barov dopredu kreslit projekcnu zonu | **40** | 40 |
| Farba ciar a popisov vln | **#334155** | #334155 |

### 🎨 Vizualizacia

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Zobraz imbalance sviecky | **✅ ZAP** | ✅ ZAP |

### 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| IMB model: Max. barov na výstup zo zóny | **1**  ← | 10 |
| IMB model: Max. barov na potvrdenie | **10**  ← | 15 |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | **4**  ← | 1 ticks |
| IMB model: Max. barov na retest | **3**  ← | 1 |
| Max. barov čakania na vyplnenie orderu | **2**  ← | 10 |
| SL: lookback barov od aktualnej sviecky | **10** | 10 |
| SL: buffer (ticky) | **0**  ← | 2 ticks |

### 💰 Veľkosť pozície a riziko

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Max strata ($, 0 = vypnute) | **1000**  ← | 350 |
| Max ziskovych tradov za den | **5** | 5 |
| Hodnota jedneho ticku ($) | **0.5**  ← | — |

### 🧩 Rozšírenia portu

| Nastavenie | Hodnota | Default stratégie |
|---|---|---|
| Pine sizing (1 kontrakt/BTC, ako TradingView) | **⬜ VYP** | ⬜ VYP |
| ATR dĺžka pre jednotku „atr“ | **14** | 14 |
| Min. vzdialenosť SL od vstupu | **0.13**  ← | 0 pct |
| Páka | **1** | 1 |
