# IBS pri RRR 0,5 **bez S/R úrovní a bez likvidity**

Áno, máme — a dokonca niekoľko. Spoločné majú to, že `enableSrTrading` aj
`enableLqTrading` sú **vypnuté**: obchoduje sa čisto z SD zón a imbalance, nič iné.

| Profil | WR posledný rok | WR 5 rokov | Obchodov/rok | Ziskový | Pozn. |
|---|---|---|---|---|---|
| **NOCNE_TESTY_B_stabilita** | **80,33 %** | 71,81 % | 232 | **5/5** | ADX filter + minSlDistance 0,13 |
| NOCNE_TESTY_A_max_winrate | 80,50 % | 71,65 % | 305 | 4/5 | ADX filter, 2023/24 PF 0,97 |
| NOCNE_TESTY_C_kompromis | 74,75 % | 70,32 % | 263 | 5/5 | viac obchodov, nižší WR |
| **SD_IMB_vitaz_5z5_406obch** | — | 69,82 % | **406** | **5/5** | bez filtra, ide aj do TradingView |
| SD_IMB_80wr_378obch_1rok | 80,16 % | — | 378 | 2/5 | **preučené, nepoužívať** |

Všetko MNQ (Databento CME futures), 3m graf, RRR 0,5, emulátor MultiCharts, bez nákladov.

---

## 1. NOCNE_TESTY_B_stabilita — najvyšší winrate so stabilitou

**80,33 % za posledný rok, 71,81 % za päť rokov, 232 obchodov ročne, zisková 5/5.**
PF 1,97. Z behu `20260917-025501-38692e`.

Čo ju drží: **ADX filter** (`tradeDirection = Indicator`) — bez neho by sa pravidlá
pre smer vôbec neuplatnili — plus minimálna vzdialenosť SL 0,13 %.

> **Do TradingView sa táto nedá prepísať celá.** ADX filter aj `minSlDistance` sú
> rozšírenia portu, Pine ich nemá. V TradingView by z nej ostal iný profil.

### Kompletné nastavenia (40 sa líši od Pine defaultu, značka ←)

#### 🎯 Obchodovanie

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| IMB entry (imbalance/gap) | **✅ ZAP** | ✅ ZAP |
| Pin Bar entry | **✅ ZAP**  ← | ⬜ VYP |
| Engulfing entry | **✅ ZAP**  ← | ⬜ VYP |
| Pin Bar: Min. pomer knôt/telo | **5**  ← | 4.0 |
| Pin Bar: Max. poloha tela v rozsahu (%) | **20** | 20 |
| Pin Bar: Min. celkový rozsah sviečky (body) | **2** | 2 |
| Engulfing: Min. celkový rozsah sviečky (body) | **6**  ← | 2 |
| Engulfing: Dĺžka priemeru rozsahu (bary) | **10** | 10 |
| Engulfing: Násobok priemerného rozsahu | **2** | 2.0 |
| Engulfing: Max. barov po dotyku zóny | **3** | 3 |
| Pin Bar/Engulfing: Typ príkazu | **Market** | Market |
| Zapnúť trailing stop | **⬜ VYP** | ⬜ VYP |
| Aktivácia trailingu (R-násobok rizika) | **1** | 1.0 |
| Trailing vzdialenosť (R-násobok rizika) | **0.5** | 0.5 |
| PickMyTrade: frekvencia update SL (% z trailing vzdialenosti) | _nechaj tak_ | 25 |
| Zapnut detekciu SD zon | **✅ ZAP** | ✅ ZAP |
| Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | **⬜ VYP** | ⬜ VYP |
| Obchoduj z likviditných zón (sweep) | **⬜ VYP** | ⬜ VYP |
| Risk:Reward pomer | **0.5**  ← | 1.0 |
| Smer obchodov | **Indicator**  ← | Both |

#### ⚙️ Základné nastavenia

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Obchoduj len Pondelok-Piatok | **✅ ZAP** | ✅ ZAP |
| Zapnut obchodovanie (strategia posiela ordre) | **✅ ZAP** | ✅ ZAP |
| Zatvor vsetky pozicie na konci session | **⬜ VYP**  ← | ✅ ZAP |

#### 📦 SD Zony

| Nastavenie | Hodnota | Pine default |
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
| Max vzdialenost IMB od zony (ticky) | **40**  ← | 100 |
| Min. velkost imbalance (body/points) | **9**  ← | 2.5 |

#### 🌏 Session 1 (Azia)

| Nastavenie | Hodnota | Pine default |
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

#### 📘 Session 2

| Nastavenie | Hodnota | Pine default |
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

#### 📙 Session 3

| Nastavenie | Hodnota | Pine default |
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

#### 📈 Market Structure

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz strukturu trhu (BOS/CHoCH) | **✅ ZAP** | ✅ ZAP |
| Swing lookback (barov na kazdu stranu) | **5** | 5 |
| Obchoduj len v smere struktury (BOS/CHoCH filter) | **⬜ VYP** | ⬜ VYP |

#### 📏 Support/Resistance

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz support/resistance | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre S/R (barov na kazdu stranu) | **10** | 10 |
| Zhlukovanie urovni (body/points) | **15** | 15 |
| Min. pocet dotykov aby sa uroven zobrazila | **2** | 2 |
| Max pocet zobrazenych urovni | **10** | 10 |
| Zobrazuj urovne len za poslednych X dni | **5** | 5 |
| Sýtosť farby zóny (%) | **30** | 30 |

#### 💧 Likvidita (Sweep)

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz liquidity sweep (stop hunt) | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre likviditu (barov na kazdu stranu) | **5**  ← | 10 |
| Min. velkost prepichnutia (body/points) | **10**  ← | 5 |
| Potvrdenie navratu do X barov | **1**  ← | 2 |
| Sila pivotu - okolie (barov) | **50** | 50 |

#### 🌊 Elliott Waves

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz Elliott Waves (zapnut/vypnut) | **⬜ VYP**  ← | ✅ ZAP |
| Swing lookback pre zigzag (barov na kazdu stranu) | **8** | 8 |
| Min. velkost vlny (body/points) | **20** | 20 |
| Zobraz cislovanie vln (0-1-2-3-4-5) | **✅ ZAP** | ✅ ZAP |
| Zobraz projekciu dalsej vlny (cielova zona) | **✅ ZAP** | ✅ ZAP |
| O kolko barov dopredu kreslit projekcnu zonu | **40** | 40 |
| Farba ciar a popisov vln | **#334155** | #334155 |

#### 🎨 Vizualizacia

| Nastavenie | Hodnota | Pine default |
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

#### 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| IMB model: Max. barov na výstup zo zóny | **1**  ← | 10 |
| IMB model: Max. barov na potvrdenie | **10**  ← | 15 |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | **4**  ← | 1 |
| IMB model: Max. barov na retest | **3**  ← | 1 |
| Rezerva (aktuálne nepoužívané) | **10** | 10 |
| Max. barov čakania na vyplnenie orderu | **2**  ← | 10 |
| Alert: cena opustila zónu (skorý signál) | **⬜ VYP** | ⬜ VYP |
| Alert: cena sa vrátila na vstupnú úroveň | **⬜ VYP** | ⬜ VYP |
| Alert: order umiestnený (E/SL/TP) | **⬜ VYP** | ⬜ VYP |
| SL: lookback barov od aktualnej sviecky | **10** | 10 |
| SL: buffer (ticky) | **0**  ← | 2 |

#### 💰 Veľkosť pozície a riziko

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Max strata ($, 0 = vypnute) | **1000**  ← | 350 |
| Hodnota jedneho ticku ($) | **0.5** | 0.5 |
| Max ziskovych tradov za den | **5** | 5 |

#### 🔗 PickMyTrade

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Token | _nechaj tak_ |  |
| Account ID | _nechaj tak_ |  |
| Strategy name | _nechaj tak_ |  |
| 'order_type' hodnota pre MARKET príkaz | _nechaj tak_ | MKT |

#### 🧩 Len v Testeri — Pine tieto vstupy nemá

| Nastavenie | Hodnota |
|---|---|
| ADX/DMI: DI Length (`adxDiLength`) | **14** |
| ADX/DMI: podfarbiť graf podľa stavu (`adxShowState`) | **✅ ZAP** |
| ADX/DMI: ADX Smoothing (`adxSmoothing`) | **7** |
| ADX/DMI: prah trendu (pod = do strany) (`adxThreshold`) | **12** |
| ADX/DMI: TF výpočtu (`adxTimeframe`) | **60** |
| ATR dĺžka pre jednotku „atr“ (`atrLen`) | **14** |
| Indikátor: ADX/DMI (`indAdx`) | **✅ ZAP** |
| Indikátor: Supertrend (`indSupertrend`) | **⬜ VYP** |
| Pine sizing (1 kontrakt/BTC, ako TradingView) (`legacyPineSizing`) | **⬜ VYP** |
| Páka (`leverage`) | **1** |
| Min. vzdialenosť SL od vstupu (`minSlDistance`) | **0.13** |
| Pravidlo: ADX dole → (`ruleAdxDown`) | **Both** |
| Pravidlo: ADX do strany → (`ruleAdxSide`) | **No trade** |
| Pravidlo: ADX hore → (`ruleAdxUp`) | **Both** |
| Pravidlo: Supertrend dole → (`ruleStDown`) | **Short only** |
| Pravidlo: Supertrend dole + ADX dole → (`ruleStDownAdxDown`) | **Short only** |
| Pravidlo: Supertrend dole + ADX do strany → (`ruleStDownAdxSide`) | **No trade** |
| Pravidlo: Supertrend dole + ADX hore → (`ruleStDownAdxUp`) | **No trade** |
| Pravidlo: Supertrend hore → (`ruleStUp`) | **Long only** |
| Pravidlo: Supertrend hore + ADX dole → (`ruleStUpAdxDown`) | **No trade** |
| Pravidlo: Supertrend hore + ADX do strany → (`ruleStUpAdxSide`) | **No trade** |
| Pravidlo: Supertrend hore + ADX hore → (`ruleStUpAdxUp`) | **Long only** |
| Supertrend: ATR Period (`stAtrPeriod`) | **14** |
| Supertrend: Change ATR Calculation Method (`stChangeAtr`) | **✅ ZAP** |
| Supertrend: Highlighter (`stHighlighting`) | **✅ ZAP** |
| Supertrend: ATR Multiplier (`stMultiplier`) | **3.5** |
| Supertrend: Show Buy/Sell Signals (`stShowSignals`) | **✅ ZAP** |
| Supertrend: Source (`stSource`) | **hl2** |
| Supertrend: TF výpočtu (`stTimeframe`) | **240** |
---

## 2. SD_IMB_vitaz_5z5_406obch — najviac obchodov, ide aj do TradingView

**69,82 % za päť rokov, 406 obchodov ročne, zisková 5/5.** Prop riziko 0,35 %/obchod.
Z behu `20260916-145448-ed9884`.

Nižší winrate, ale skoro dvojnásobok obchodov a **žiadny indikátorový filter**
(`tradeDirection = Both`, takže Supertrend/ADX pravidlá sú neúčinné aj keď sú v profile
vyplnené). Do TradingView sa dá prepísať celá okrem `minSlDistance = 0,06 %`.

### Kompletné nastavenia (40 sa líši od Pine defaultu, značka ←)

#### 🎯 Obchodovanie

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| IMB entry (imbalance/gap) | **✅ ZAP** | ✅ ZAP |
| Pin Bar entry | **✅ ZAP**  ← | ⬜ VYP |
| Engulfing entry | **✅ ZAP**  ← | ⬜ VYP |
| Pin Bar: Min. pomer knôt/telo | **5**  ← | 4.0 |
| Pin Bar: Max. poloha tela v rozsahu (%) | **20** | 20 |
| Pin Bar: Min. celkový rozsah sviečky (body) | **2** | 2 |
| Engulfing: Min. celkový rozsah sviečky (body) | **6**  ← | 2 |
| Engulfing: Dĺžka priemeru rozsahu (bary) | **10** | 10 |
| Engulfing: Násobok priemerného rozsahu | **2** | 2.0 |
| Engulfing: Max. barov po dotyku zóny | **3** | 3 |
| Pin Bar/Engulfing: Typ príkazu | **Market** | Market |
| Zapnúť trailing stop | **⬜ VYP** | ⬜ VYP |
| Aktivácia trailingu (R-násobok rizika) | **1** | 1.0 |
| Trailing vzdialenosť (R-násobok rizika) | **0.5** | 0.5 |
| PickMyTrade: frekvencia update SL (% z trailing vzdialenosti) | _nechaj tak_ | 25 |
| Zapnut detekciu SD zon | **✅ ZAP** | ✅ ZAP |
| Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny) | **⬜ VYP** | ⬜ VYP |
| Obchoduj z likviditných zón (sweep) | **⬜ VYP** | ⬜ VYP |
| Risk:Reward pomer | **0.5**  ← | 1.0 |
| Smer obchodov | **Both** | Both |

#### ⚙️ Základné nastavenia

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Obchoduj len Pondelok-Piatok | **✅ ZAP** | ✅ ZAP |
| Zapnut obchodovanie (strategia posiela ordre) | **✅ ZAP** | ✅ ZAP |
| Zatvor vsetky pozicie na konci session | **⬜ VYP**  ← | ✅ ZAP |

#### 📦 SD Zony

| Nastavenie | Hodnota | Pine default |
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
| Max vzdialenost IMB od zony (ticky) | **40**  ← | 100 |
| Min. velkost imbalance (body/points) | **7**  ← | 2.5 |

#### 🌏 Session 1 (Azia)

| Nastavenie | Hodnota | Pine default |
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

#### 📘 Session 2

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zapnúť | **✅ ZAP** | ✅ ZAP |
| Časové pásmo | **America/New_York** | America/New_York |
| SD zona zaciatok (H) | **18**  ← | 10 |
| M | **0** | 0 |
| SD zona koniec (H) | **17**  ← | 11 |
| M | **0** | 0 |
| Trade zaciatok (H) | **8**  ← | 10 |
| M | **30**  ← | 0 |
| Trade koniec (H) | **13**  ← | 15 |
| M | **0**  ← | 45 |

#### 📙 Session 3

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zapnúť | **⬜ VYP**  ← | ✅ ZAP |
| Časové pásmo | **America/New_York**  ← | Europe/London |
| SD zona zaciatok (H) | **14**  ← | 8 |
| M | **0** | 0 |
| SD zona koniec (H) | **16**  ← | 10 |
| M | **0** | 0 |
| Trade zaciatok (H) | **14**  ← | 8 |
| M | **0** | 0 |
| Trade koniec (H) | **17**  ← | 11 |
| M | **0** | 0 |

#### 📈 Market Structure

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz strukturu trhu (BOS/CHoCH) | **✅ ZAP** | ✅ ZAP |
| Swing lookback (barov na kazdu stranu) | **5** | 5 |
| Obchoduj len v smere struktury (BOS/CHoCH filter) | **⬜ VYP** | ⬜ VYP |

#### 📏 Support/Resistance

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz support/resistance | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre S/R (barov na kazdu stranu) | **10** | 10 |
| Zhlukovanie urovni (body/points) | **15** | 15 |
| Min. pocet dotykov aby sa uroven zobrazila | **2** | 2 |
| Max pocet zobrazenych urovni | **10** | 10 |
| Zobrazuj urovne len za poslednych X dni | **5** | 5 |
| Sýtosť farby zóny (%) | **30** | 30 |

#### 💧 Likvidita (Sweep)

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz liquidity sweep (stop hunt) | **✅ ZAP** | ✅ ZAP |
| Swing lookback pre likviditu (barov na kazdu stranu) | **5**  ← | 10 |
| Min. velkost prepichnutia (body/points) | **10**  ← | 5 |
| Potvrdenie navratu do X barov | **1**  ← | 2 |
| Sila pivotu - okolie (barov) | **50** | 50 |

#### 🌊 Elliott Waves

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Zobraz Elliott Waves (zapnut/vypnut) | **⬜ VYP**  ← | ✅ ZAP |
| Swing lookback pre zigzag (barov na kazdu stranu) | **8** | 8 |
| Min. velkost vlny (body/points) | **20** | 20 |
| Zobraz cislovanie vln (0-1-2-3-4-5) | **✅ ZAP** | ✅ ZAP |
| Zobraz projekciu dalsej vlny (cielova zona) | **✅ ZAP** | ✅ ZAP |
| O kolko barov dopredu kreslit projekcnu zonu | **40** | 40 |
| Farba ciar a popisov vln | **#334155** | #334155 |

#### 🎨 Vizualizacia

| Nastavenie | Hodnota | Pine default |
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

#### 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| IMB model: Max. barov na výstup zo zóny | **1**  ← | 10 |
| IMB model: Max. barov na potvrdenie | **10**  ← | 15 |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | **0**  ← | 1 |
| IMB model: Max. barov na retest | **3**  ← | 1 |
| Rezerva (aktuálne nepoužívané) | **10** | 10 |
| Max. barov čakania na vyplnenie orderu | **3**  ← | 10 |
| Alert: cena opustila zónu (skorý signál) | **⬜ VYP** | ⬜ VYP |
| Alert: cena sa vrátila na vstupnú úroveň | **⬜ VYP** | ⬜ VYP |
| Alert: order umiestnený (E/SL/TP) | **⬜ VYP** | ⬜ VYP |
| SL: lookback barov od aktualnej sviecky | **15**  ← | 10 |
| SL: buffer (ticky) | **2** | 2 |

#### 💰 Veľkosť pozície a riziko

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Max strata ($, 0 = vypnute) | **1000**  ← | 350 |
| Hodnota jedneho ticku ($) | **0.5** | 0.5 |
| Max ziskovych tradov za den | **5** | 5 |

#### 🔗 PickMyTrade

| Nastavenie | Hodnota | Pine default |
|---|---|---|
| Token | _nechaj tak_ |  |
| Account ID | _nechaj tak_ |  |
| Strategy name | _nechaj tak_ |  |
| 'order_type' hodnota pre MARKET príkaz | _nechaj tak_ | MKT |

#### 🧩 Len v Testeri — Pine tieto vstupy nemá

| Nastavenie | Hodnota |
|---|---|
| ADX/DMI: DI Length (`adxDiLength`) | **14** |
| ADX/DMI: podfarbiť graf podľa stavu (`adxShowState`) | **✅ ZAP** |
| ADX/DMI: ADX Smoothing (`adxSmoothing`) | **14** |
| ADX/DMI: prah trendu (pod = do strany) (`adxThreshold`) | **20** |
| ADX/DMI: TF výpočtu (`adxTimeframe`) | **60** |
| ATR dĺžka pre jednotku „atr“ (`atrLen`) | **14** |
| Indikátor: ADX/DMI (`indAdx`) | **⬜ VYP** |
| Indikátor: Supertrend (`indSupertrend`) | **✅ ZAP** |
| Pine sizing (1 kontrakt/BTC, ako TradingView) (`legacyPineSizing`) | **⬜ VYP** |
| Páka (`leverage`) | **1** |
| Min. vzdialenosť SL od vstupu (`minSlDistance`) | **0.06** |
| Pravidlo: ADX dole → (`ruleAdxDown`) | **Short only** |
| Pravidlo: ADX do strany → (`ruleAdxSide`) | **No trade** |
| Pravidlo: ADX hore → (`ruleAdxUp`) | **Long only** |
| Pravidlo: Supertrend dole → (`ruleStDown`) | **Short only** |
| Pravidlo: Supertrend dole + ADX dole → (`ruleStDownAdxDown`) | **Short only** |
| Pravidlo: Supertrend dole + ADX do strany → (`ruleStDownAdxSide`) | **No trade** |
| Pravidlo: Supertrend dole + ADX hore → (`ruleStDownAdxUp`) | **No trade** |
| Pravidlo: Supertrend hore → (`ruleStUp`) | **Long only** |
| Pravidlo: Supertrend hore + ADX dole → (`ruleStUpAdxDown`) | **No trade** |
| Pravidlo: Supertrend hore + ADX do strany → (`ruleStUpAdxSide`) | **No trade** |
| Pravidlo: Supertrend hore + ADX hore → (`ruleStUpAdxUp`) | **Long only** |
| Supertrend: ATR Period (`stAtrPeriod`) | **10** |
| Supertrend: Change ATR Calculation Method (`stChangeAtr`) | **✅ ZAP** |
| Supertrend: Highlighter (`stHighlighting`) | **✅ ZAP** |
| Supertrend: ATR Multiplier (`stMultiplier`) | **3** |
| Supertrend: Show Buy/Sell Signals (`stShowSignals`) | **✅ ZAP** |
| Supertrend: Source (`stSource`) | **hl2** |
| Supertrend: TF výpočtu (`stTimeframe`) | **60** |
---

## Bod zlomu, ktorý k RRR 0,5 patrí

Pri pomere 0,5 je **bod zlomu 66,7 % winrate** — prehrávaš dvakrát toľko, koľko vyhrávaš.

- `NOCNE_TESTY_B` má na piatich rokoch 71,81 % → rezerva **5,1 bodu**
- `SD_IMB_vitaz_5z5` má 69,82 % → rezerva **3,1 bodu**

To je podstatne tesnejšie než tých 14 bodov, ktoré ukazoval jednoročný profil
`MNQ_R05_WR80_najlepsi_pomer`. Tam bolo 80,5 % zmeraných na jednom roku; na piatich
oknách sa tieto čísla dostanú na 70 % a rezerva sa scvrkne. **Je to reálnejší obraz,
nie horší výsledok.**
