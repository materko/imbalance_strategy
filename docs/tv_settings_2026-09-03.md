# TradingView nastavenia — IBS Imbalance Breakout Strategy
**Zdroj:** screenshoty z panelu nastavení, BTCUSD 3m (Coinbase), 2026-09-03
**Použi ako referenciu pri portovaní do Python/Freqtrade — cieľ je rovnaké vykreslovanie a rovnaké obchody.**

> ⚠️ **Dôležité:** screenshoty sú z **plnej (SK) verzie** stratégie (obsahuje Pin Bar/Engulfing entry,
> Elliott Waves, Support/Resistance, Liquidity sweep, Market Structure).
> Priložený súbor [`imbalance_strategy_SD_IMB.pine`](../imbalance_strategy_SD_IMB.pine) je **C4 "stripped" build (EN)** —
> obsahuje LEN SD zóny + IMB entry model. Sekcie nižšie označené `[NIE JE V C4]` v tom súbore neexistujú.

---

## 🎯 Obchodovanie

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| IMB entry (imbalance/gap) | ✅ zap | `enableImbEntry` |
| Pin Bar entry `[NIE JE V C4]` | ✅ zap | — |
| Engulfing entry `[NIE JE V C4]` | ⬜ vyp | — |
| Pin Bar: Min. pomer knôt/telo `[NIE JE V C4]` | 4 | — |
| Pin Bar: Max. poloha tela v rozsahu (%) `[NIE JE V C4]` | 20 | — |
| Pin Bar: Min. celkový rozsah sviečky (body) `[NIE JE V C4]` | 2 | — |
| Engulfing: Min. celkový rozsah sviečky (body) `[NIE JE V C4]` | 2 | — |
| Engulfing: Dĺžka priemeru rozsahu (bary) `[NIE JE V C4]` | 10 | — |
| Engulfing: Násobok priemerného rozsahu `[NIE JE V C4]` | 2 | — |
| Engulfing: Max. barov po dotyku zóny `[NIE JE V C4]` | 3 | — |
| Pin Bar/Engulfing: Typ príkazu `[NIE JE V C4]` | Market | — |
| Zapnúť trailing stop | ✅ zap | `enableTrailing` (default v C4 = false) |
| Aktivácia trailingu (R-násobok rizika) | 1 | `trailActivationR` |
| Trailing vzdialenosť (R-násobok rizika) | 0.5 | `trailOffsetR` |
| PickMyTrade: frekvencia update SL (% z trailing vzd.) | 25 | `trailFreqPct` |
| Zapnúť detekciu SD zón | ✅ zap | `enableZoneDetection` |
| Obchoduj z S/R úrovní `[NIE JE V C4]` | ⬜ vyp | — |
| Obchoduj z likviditných zón (sweep) `[NIE JE V C4]` | ⬜ vyp | — |
| Risk:Reward pomer | 1 | `rrRatio` |
| Smer obchodov | **Long only** | `tradeDirection` (default v C4 = "Both") |

## ⚙️ Základné nastavenia

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Obchoduj len Pondelok–Piatok | ✅ zap | `weekdaysOnly` |
| Zapnúť obchodovanie (stratégia posiela ordre) | ✅ zap | `enableTrading` |
| Zatvor všetky pozície na konci session | ✅ zap | `closeAtSessionEnd` |

## 📦 SD zóny

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Zapnúť hľadanie gapu vnútri zóny | ✅ zap | `enableGapDetection` |
| SD zóna – detekčný TF | **5** | `zoneDetectionTF` |
| Platnosť zóny (hodiny) | 6 | `zoneValidHours` |
| Max SD zón | 200 | `maxSdZones` |
| Snap času zóny na TF grid | Floor | `snapMode` |
| Invaliduj zónu pri vyplnení orderu | ✅ zap | `invalidateOnFill` |
| Zapnúť volume filter (SD zóny) | ⬜ vyp | `useVolumeFilter` |
| Aj blokovať slabé (nízky volume) zóny | ⬜ vyp | `volumeFilterBlockTrading` |
| Volume: priemer za N sviečok | 20 | `volSmaLen` |
| Volume: min. násobok priemeru pre „silnú" zónu | 1.5 | `volMultiplier` |
| Max barov dozadu pre IMB | 20 | `imbLookback` |
| Max vzdialenosť IMB od zóny (ticky) | 100 | `imbMaxDistTicks` |
| Min. veľkosť imbalance (body/points) | 2.5 | `minImbSizePoints` |

## 🌏 Session 1 (Ázia) — **vypnutá**

| | |
|---|---|
| Zapnúť | ⬜ vyp (`sess1On`) |
| Časové pásmo | Europe/Prague |
| SD zóna | 01:00 → 09:00 |
| Trade | 02:00 → 05:00 |

## 📘 Session 2 — zapnutá

| | |
|---|---|
| Zapnúť | ✅ zap (`sess2On`) |
| Časové pásmo | America/New_York |
| SD zóna | **08:00 → 11:00** (pozn.: default v C4 = 10:00 → 11:00) |
| Trade | 10:00 → 15:45 |

## 📙 Session 3 — zapnutá

| | |
|---|---|
| Zapnúť | ✅ zap (`sess3On`) |
| Časové pásmo | Europe/London |
| SD zóna | 08:00 → 10:00 |
| Trade | 08:00 → 11:00 |

## 📐 Market Structure `[NIE JE V C4]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz štruktúru trhu (BOS/CHoCH) | ✅ zap |
| Swing lookback (barov na každú stranu) | 5 |
| Obchoduj len v smere štruktúry (BOS/CHoCH filter) | ⬜ vyp |

## 📏 Support/Resistance `[NIE JE V C4]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz support/resistance | ✅ zap |
| Swing lookback pre S/R | 10 |
| Zhlukovanie úrovní (body/points) | 15 |
| Min. počet dotykov aby sa úroveň zobrazila | 2 |
| Max počet zobrazených úrovní | 10 |
| Zobrazuj úrovne len za posledných X dní | 5 |
| Sýtosť farby zóny (%) | 30 |

## 💧 Likvidita (sweep) `[NIE JE V C4]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz liquidity sweep (stop hunt) | ✅ zap |
| Swing lookback pre likviditu | 10 |
| Min. veľkosť prepichnutia (body/points) | 5 |
| Potvrdenie návratu do X barov | 2 |
| Sila pivotu – okolie (barov) | 50 |

## 🌊 Elliott Waves `[NIE JE V C4]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz Elliott Waves | ⬜ vyp |
| Swing lookback pre zigzag | 8 |
| Min. veľkosť vlny (body/points) | 20 |
| Zobraz číslovanie vĺn (0-1-2-3-4-5) | ✅ zap |
| Zobraz projekciu ďalšej vlny (cieľová zóna) | ✅ zap |
| O koľko barov dopredu kresliť projekčnú zónu | 40 |
| Farba čiar a popisov vĺn | tmavomodrá (navy) |

## 🎨 Vizualizácia

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Zobraz imbalance sviečky | ✅ zap | `showImbalance` |
| Zobraz dashboard panel | ✅ zap | `showDashboard` |
| Pozícia panelu | Top Right | `dashPos` |
| Počet štatistických dlaždíc | 6 | `dashboardRows` |
| Zobraz tabuľku obchodov v paneli (Entry/SL/TP) | ⬜ vyp | `showTradeLog` |
| Počet riadkov v tabuľke obchodov (max 20) | 20 | `tradeLogRows` |
| Zobraz pokročilý diagnostický panel | ⬜ vyp | `showDebugTable` |
| Počet riadkov v diagnostickom paneli | 8 | `debugTableRows` |
| Pozícia diagnostického panelu | Bottom Right | `debugPos` |

## 🔧 Pokročilé (časovanie vstupu, SL)

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| IMB model: Max. barov na výstup zo zóny | 10 | `state1MaxBars` |
| IMB model: Max. barov na potvrdenie | 15 | `state2MaxBars` |
| IMB model: Potvrdenie (ticky nad/pod IMB telom) | 1 | `state2ConfirmTicks` |
| IMB model: Max. barov na retest | 1 | `state3MaxBars` |
| Rezerva (aktuálne nepoužívané) | 10 | `state4MaxBars` (mŕtvy parameter) |
| Max. barov čakania na vyplnenie orderu | 10 | `state5MaxBars` |
| Alert: cena opustila zónu (skorý signál) | ⬜ vyp | `alertOnState2` |
| Alert: cena sa vrátila na vstupnú úroveň | ⬜ vyp | `alertOnState3` |
| Alert: order umiestnený (E/SL/TP) | ⬜ vyp | `alertOnState4` |
| SL: lookback barov od aktuálnej sviečky | 10 | `slLookback` |
| SL: buffer (ticky) | 2 | `slBufferTicks` |

## 💰 Position Size & Risk — *nebolo na screenshotoch, hodnoty z kódu / dashboardu*

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Max strata ($, 0 = vypnuté) | 350 (potvrdené dashboardom „RISK / OBCHOD: $350") | `maxLossDollar` |
| Hodnota jedného ticku ($) | 0.5 (default z kódu — **overiť pre BTCUSD**) | `tickDollarValue` |
| Max výherných obchodov za deň | 5 (default z kódu) | `maxDailyWins` |

## 🔗 PickMyTrade
Token / Account ID / Strategy name — prázdne (nepoužité pri backteste).
