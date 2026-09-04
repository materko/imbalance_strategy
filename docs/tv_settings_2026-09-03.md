# TradingView nastavenia — IBS Imbalance Breakout Strategy
**Zdroj:** screenshoty z panelu nastaveni, BTCUSD 3m (Coinbase), 2026-09-03
**Pouzi ako referenciu pri portovani do Python/Freqtrade — ciel je rovnake vykreslovanie a rovnake obchody.**

> Tieto nastavenia zodpovedaju **plnej verzii** [`imbalance_strategy_FULL.pine`](../imbalance_strategy_FULL.pine)
> (Pine v5, 2539 riadkov, 115 inputov, slovenske nazvy) — to je referencny subor pre port.
>
> Polozky oznacene `[len FULL]` **neexistuju** v stripped builde
> [`imbalance_strategy_SD_IMB.pine`](../imbalance_strategy_SD_IMB.pine) (Pine v6, 80 inputov, len SD zony + IMB entry).

## ⚠️ Rozdiely: nastavenia na grafe vs. defaulty v kóde

Toto je presne to, čo používateľ prestavil oproti `input.*` defaultom v `imbalance_strategy_FULL.pine`.
**Pri porte použi ĽAVÝ stĺpec (hodnotu z grafu), nie default.**

| Pine premenná | Default v kóde | **Na grafe (screenshot)** |
|---|---|---|
| `enablePinBarEntry` | `false` | **`true`** (Pin Bar entry zapnutý) |
| `enableTrailing` | `false` | **`true`** (trailing stop zapnutý) |
| `tradeDirection` | `"Both"` | **`"Long only"`** |
| `sess2ZoneStartH` | `10` | **`8`** (SD zóna Session 2 začína o 08:00 NY) |
| `showElliott` | `true` | **`false`** (Elliott Waves vypnuté — len vizuál) |

Všetky ostatné inputy sú na defaultoch z kódu.

---

## 🎯 Obchodovanie

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| IMB entry (imbalance/gap) | ✅ zap | `enableImbEntry` |
| Pin Bar entry `[len FULL]` | ✅ zap | `enablePinBarEntry` (default `false`!) |
| Engulfing entry `[len FULL]` | ⬜ vyp | `enableEngulfingEntry` |
| Pin Bar: Min. pomer knôt/telo `[len FULL]` | 4 | `pbWickToBodyRatio` |
| Pin Bar: Max. poloha tela v rozsahu (%) `[len FULL]` | 20 | `pbBodyPositionPct` |
| Pin Bar: Min. celkový rozsah sviečky (body) `[len FULL]` | 2 | `pbMinRangePoints` |
| Engulfing: Min. celkový rozsah sviečky (body) `[len FULL]` | 2 | `engMinRangePoints` |
| Engulfing: Dĺžka priemeru rozsahu (bary) `[len FULL]` | 10 | `engSizeAvgLen` |
| Engulfing: Násobok priemerného rozsahu `[len FULL]` | 2 | `engSizeMultiplier` |
| Engulfing: Max. barov po dotyku zóny `[len FULL]` | 3 | `engTouchWindowBars` |
| Pin Bar/Engulfing: Typ príkazu `[len FULL]` | Market | `pbEngOrderType` |
| Zapnúť trailing stop | ✅ zap | `enableTrailing` (default v kode = false) |
| Aktivácia trailingu (R-násobok rizika) | 1 | `trailActivationR` |
| Trailing vzdialenosť (R-násobok rizika) | 0.5 | `trailOffsetR` |
| ~~PickMyTrade: frekvencia update SL~~ | ~~25~~ | `trailFreqPct` — **neportuje sa** |
| Zapnúť detekciu SD zón | ✅ zap | `enableZoneDetection` |
| Obchoduj z S/R úrovní `[len FULL]` | ⬜ vyp | `enableSrTrading` |
| Obchoduj z likviditných zón (sweep) `[len FULL]` | ⬜ vyp | `enableLqTrading` |
| Risk:Reward pomer | 1 | `rrRatio` |
| Smer obchodov | **Long only** | `tradeDirection` (default v kode = "Both") |

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
| SD zóna | **08:00 → 11:00** (pozn.: default v kode = 10:00 → 11:00) |
| Trade | 10:00 → 15:45 |

## 📙 Session 3 — zapnutá

| | |
|---|---|
| Zapnúť | ✅ zap (`sess3On`) |
| Časové pásmo | Europe/London |
| SD zóna | 08:00 → 10:00 |
| Trade | 08:00 → 11:00 |

## 📐 Market Structure `[len FULL]`

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Zobraz štruktúru trhu (BOS/CHoCH) | ✅ zap | `showMarketStructure` |
| Swing lookback (barov na každú stranu) | 5 | `structureSwingLen` |
| Obchoduj len v smere štruktúry (BOS/CHoCH filter) | ⬜ vyp | `useStructureFilter` |

## 📏 Support/Resistance `[len FULL]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz support/resistance | ✅ zap |
| Swing lookback pre S/R | 10 |
| Zhlukovanie úrovní (body/points) | 15 |
| Min. počet dotykov aby sa úroveň zobrazila | 2 |
| Max počet zobrazených úrovní | 10 |
| Zobrazuj úrovne len za posledných X dní | 5 |
| Sýtosť farby zóny (%) | 30 |

## 💧 Likvidita (sweep) `[len FULL]`

| Nastavenie | Hodnota |
|---|---|
| Zobraz liquidity sweep (stop hunt) | ✅ zap |
| Swing lookback pre likviditu | 10 |
| Min. veľkosť prepichnutia (body/points) | 5 |
| Potvrdenie návratu do X barov | 2 |
| Sila pivotu – okolie (barov) | 50 |

## 🌊 Elliott Waves `[len FULL]`

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

## 💰 Veľkosť pozície a riziko — *nebolo na screenshotoch, hodnoty = defaulty z kódu*

| Nastavenie | Hodnota | Pine premenná |
|---|---|---|
| Max strata ($, 0 = vypnuté) | 350 (potvrdené dashboardom „RISK / OBCHOD: $350") | `maxLossDollar` |
| Hodnota jedného ticku ($) | 0.5 — **overiť pre BTCUSD** | `tickDollarValue` |
| Max výherných obchodov za deň | 5 | `maxDailyWins` |

## 🔗 PickMyTrade — **neportuje sa**

Rozhodnutie z 2026-09-04: PickMyTrade sa už nebude používať. Freqtrade aj MultiCharts
posielajú ordre priamo, žiadny webhook medzi tým nie je.

Do Pythonu teda nejde päť Pine vstupov: `pmtToken`, `pmtAccountId`, `pmtStratName`,
`pmtMarketOrderType` a `trailFreqPct` (ten bol podľa vlastného Pine tooltipu použiteľný
len pre PickMyTrade — `strategy.exit` v TradingView pre neho nemá ekvivalent).

Zoznam je aj v `ibs/tests/test_pine_parity.py` ako `REMOVED_INPUTS`, takže test parity
vie, že chýbajú zámerne, a zároveň stráži, aby sa nevrátili.

---

## Mapovanie Pine premenných pre `[len FULL]` moduly

Pre vernú replikáciu kreslenia v Pythone:

| Modul | Pine premenné (v poradí ako v paneli) |
|---|---|
| 📈 Market Structure | `showMarketStructure`, `structureSwingLen`, `useStructureFilter` |
| 📏 Support/Resistance | `showSR`, `srSwingLen`, `srClusterPoints`, `srMinTouches`, `srMaxLevels`, `srLookbackDays`, `srZoneSaturationPct` |
| 💧 Likvidita (Sweep) | `showLiqSweep`, `liqSweepLen`, `liqSweepMinWick`, `liqSweepConfirmBars`, `liqStrengthLen` |
| 🌊 Elliott Waves | `showElliott`, `ewSwingLen`, `ewMinWavePoints`, `ewShowLabels`, `ewShowProjection`, `ewProjExtendBars`, `ewLineColor` |
| 🎯 Pin Bar / Engulfing entry | `enablePinBarEntry`, `enableEngulfingEntry`, `pbWickToBodyRatio`, `pbBodyPositionPct`, `pbMinRangePoints`, `engMinRangePoints`, `engSizeAvgLen`, `engSizeMultiplier`, `engTouchWindowBars`, `pbEngOrderType` |
| 🎯 Zdroj obchodu | `enableZoneDetection` (SD), `enableSrTrading` (S/R), `enableLqTrading` (likvidita) — všetky idú cez spoločný vstupný bod `f_pushZone()` |
