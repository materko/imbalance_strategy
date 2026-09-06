# Archív profilov (2026-09-05)

Tieto profily boli do 2026-09-05 v `tradebot/configs/ibs/` a webapp ich ponúkala v zozname
východiskových profilov. Boli to medzikroky vývoja a experimenty; každú kombináciu si
tester nastaví vo formulári alebo cez `--set`, a história behov ju drží. V `tradebot/configs/ibs/`
ostali len referenčné profily pre golden testy proti TradingView a pre MultiCharts.

Súbory tu sú **nezmenené** a dajú sa ďalej načítať cestou — všade, kde sa berie názov
profilu, funguje aj cesta k súboru:

```bash
python -m tradebot.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timerange 20250904-20260904 --note "..."
TRADEBOT_PROFILE=docs/profily_archiv/ibs/btcusdt_3m_binance_hyper.json ./platforms/freqtrade/scripts/hyperopt.sh 20250904-20260904 200
```

Staršie dokumenty v `docs/` sa na ne odkazujú pôvodnými názvami — sú to záznamy meraní,
nemenili sa.

## Premenované referenčné profily (ostávajú v `tradebot/configs/ibs/`)

| Starý názov | Nový názov | Na čo |
|---|---|---|
| `btcusdt_3m_binance_tv` | `golden_binance_btcusdt_3m` | Referenčný golden test proti TradingView — Binance BTCUSDT.P 3m (1 BTC, RR 1, trailing) |
| `btcusd_3m_coinbase` | `golden_coinbase_btcusd_3m` | Referenčný golden test proti TradingView — Coinbase BTCUSD 3m (len MultiCharts a testy, Freqtrade Coinbase nemá) |
| `mnq_3m` | `multicharts_mnq_3m` | MultiCharts MNQ futures 3m — 1:1 s Pine jednotkami, základ pre futures a akcie |

## Archivované profily

### `btcusdt_3m_binance`  (btcusdt_binance)

BINANCE BTC/USDT perpetual (USDs-M), 3m - EXEKUCNY profil pre Freqtrade futures. Rozdiel oproti mnq_3m/btcusd_3m_coinbase: velkostne parametre su prepnute na jednotky, ktore davaju zmysel mimo MNQ (ARCHITECTURE_port.md 3b).  POZOR - ATR nasobky nizsie su STARTOVACIE ODHADY, nie odmerane hodnoty. Ladit hyperoptom az ked bude engine hotovy a golden test na Coinbase profile bude sediet s TradingView.  Tick-based parametre: Binance tick je 0.1 vs Coinbase 0.01, takze povodne hodnoty by boli 10x vedla. slBufferTicks a state2ConfirmTicks su nastavene na 1 Binance tick (0.1) - povodny prepocet by dal 0.02 resp. 0.01, co je pod tickom a teda nevykonatelne.  tickDollarValue tu zamerne CHYBA - engine pouziva InstrumentSpec.point_value.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `pbMinRangePoints` | `0.2 atr` |
| `engMinRangePoints` | `0.2 atr` |
| `enableTrailing` | `True` |
| `sess2ZoneStartH` | `8` |
| `srClusterPoints` | `0.5 atr` |
| `liqSweepMinWick` | `0.3 atr` |
| `showElliott` | `False` |
| `ewMinWavePoints` | `2.0 atr` |
| `imbMaxDistTicks` | `1.0 abs` |
| `minImbSizePoints` | `0.25 atr` |
| `state2ConfirmTicks` | `0.1 abs` |
| `slBufferTicks` | `0.1 abs` |
| `tradeDirection` | `Long only` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set pbMinRangePoints=0.2@atr --set engMinRangePoints=0.2@atr --set enableTrailing=true --set sess2ZoneStartH=8 --set srClusterPoints=0.5@atr --set liqSweepMinWick=0.3@atr --set showElliott=false --set ewMinWavePoints=2.0@atr --set imbMaxDistTicks=1.0@abs --set minImbSizePoints=0.25@atr --set state2ConfirmTicks=0.1@abs --set slBufferTicks=0.1@abs --set tradeDirection="Long only"
```

### `btcusdt_3m_binance_hyper`  (btcusdt_binance)

BINANCE BTCUSDT.P, 3m - VYCHODISKO PRE HYPEROPT so SIZINGOM AKO V TRADINGVIEW.  Nastavenia podla manualneho prieskumu v TradingView na BTCUSD (2026-09-04): RR 2.5, Long only, vsetky tri entry modely (IMB + Pin Bar + Engulfing), S/R zony ON, likviditne zony ON. enableImbEntry sa neuvadza - je to Pine default (true), profily maju len odchylky.  legacyPineSizing + tickDollarValue 0.5 su tu ZAMERNE, aby bol experiment porovnatelny s TradingView. Na BTC to dava qty = 1 BTC pri kazdom realnom SL (floor(350 / (SLdist/0.1 * 0.5)) = 0 -> max(1,0) = 1), takze maxLossDollar sa neuplatni a riziko na obchod je rovne SL vzdialenosti v dolaroch - presne to, co robil TradingView strategy tester.  leverage=20: 1 BTC je pri cene 120k notional 120k USDT. Bez paky by sa to do penazenky nezmestilo a stake by sa orezal.  POZOR - dve veci, ktore treba vediet:   2. Prahy v jednotke atr su STARTOVACIE ODHADY - presne to, co ma hyperopt doladit.  enableSrTrading a enableLqTrading su OVERENE proti TradingView (2026-09-04): po ich zapnuti sa pocet obchodov zmenil z 5 (3W/2L) na 6 (4W/2L) rovnako v TradingView aj v engine - viz test_sr_a_likviditne_zony_sedia_s_tradingview.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `pbMinRangePoints` | `0.2 atr` |
| `engMinRangePoints` | `0.2 atr` |
| `enableTrailing` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `srClusterPoints` | `0.5 atr` |
| `liqSweepMinWick` | `0.3 atr` |
| `showElliott` | `False` |
| `ewMinWavePoints` | `2.0 atr` |
| `imbMaxDistTicks` | `1.0 abs` |
| `minImbSizePoints` | `0.25 atr` |
| `state2ConfirmTicks` | `0.1 abs` |
| `rrRatio` | `2.5` |
| `slBufferTicks` | `0.1 abs` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |
| `leverage` | `20.0` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set pbMinRangePoints=0.2@atr --set engMinRangePoints=0.2@atr --set enableTrailing=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set srClusterPoints=0.5@atr --set liqSweepMinWick=0.3@atr --set showElliott=false --set ewMinWavePoints=2.0@atr --set imbMaxDistTicks=1.0@abs --set minImbSizePoints=0.25@atr --set state2ConfirmTicks=0.1@abs --set rrRatio=2.5 --set slBufferTicks=0.1@abs --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true --set leverage=20.0
```

### `btcusdt_3m_binance_opt`  (btcusdt_binance)

BINANCE BTCUSDT.P, 3m - VYSLEDOK HYPEROPTU (epocha 288 z 300).  Ladene na okne 2025-09-05 az 2026-09-04 (365 dni), loss IBSHyperOptLoss (Calmar so spodnym limitom na pocet obchodov), sizing legacyPineSizing aby bol experiment porovnatelny s TradingView.  Vysledok NA OKNE, KDE SA LADILO (teda optimisticky):   103 obchodov, +34.8 %, win rate 44.7 %, max DD 24.7 %, PF 1.24  POZOR: cisla mimo tohto okna su v docs/HYPEROPT_btcusdt_2026-09-04.md. Priestor ma 10 parametrov a strategia robi ~150 obchodov za rok, takze pretrenovanie je realne - bez pohladu na out-of-sample vysledky sa tomuto profilu nedaju verit.  enableSrTrading a enableLqTrading su OVERENE proti TradingView (2026-09-04): po ich zapnuti sa pocet obchodov zmenil z 5 (3W/2L) na 6 (4W/2L) rovnako v TradingView aj v engine - viz test_sr_a_likviditne_zony_sedia_s_tradingview.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `pbMinRangePoints` | `0.72 atr` |
| `engMinRangePoints` | `0.93 atr` |
| `enableTrailing` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `srClusterPoints` | `0.21 atr` |
| `liqSweepMinWick` | `0.59 atr` |
| `showElliott` | `False` |
| `ewMinWavePoints` | `2.0 atr` |
| `imbMaxDistTicks` | `1.0 abs` |
| `minImbSizePoints` | `0.43 atr` |
| `state2ConfirmTicks` | `0.1 abs` |
| `rrRatio` | `1.7` |
| `slBufferTicks` | `0.1 abs` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |
| `leverage` | `20.0` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set pbMinRangePoints=0.72@atr --set engMinRangePoints=0.93@atr --set enableTrailing=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set srClusterPoints=0.21@atr --set liqSweepMinWick=0.59@atr --set showElliott=false --set ewMinWavePoints=2.0@atr --set imbMaxDistTicks=1.0@abs --set minImbSizePoints=0.43@atr --set state2ConfirmTicks=0.1@abs --set rrRatio=1.7 --set slBufferTicks=0.1@abs --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true --set leverage=20.0
```

### `btcusdt_3m_binance_struct`  (btcusdt_binance)

BINANCE BTCUSDT.P 3m - najlepsia konfiguracia zo systematickeho hladania (2026-09-04).  Rozdiely oproti btcusdt_3m_binance_tv: rrRatio 5, trailing vypnuty, slLookback 20, zapnuty struktury filter (BOS/CHoCH) a obchodovanie z S/R aj likviditnych zon. Vsetky tri entry modely zapnute.  POZOR - toto NIE JE odporucanie na obchodovanie. Priemerny break-even poplatok je 0,045 % na stranu (spolu cez pat rokov 0,040 %) proti 0,05 %, ktore berie Binance; dva z piatich rokov su po poplatkoch ziskove a sucet za pat rokov je prakticky nula. Detaily v docs/FILTRE_vstupu_2026-09-04.md, cisla po opravach adaptera v docs/OPRAVY_adapter_2026-09-05.md.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `useStructureFilter` | `True` |
| `showElliott` | `False` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set useStructureFilter=true --set showElliott=false --set rrRatio=5.0 --set slLookback=20 --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true
```

### `btcusdt_3m_binance_ny`  (btcusdt_binance)

BINANCE BTCUSDT.P 3m - najlepsia najdena konfiguracia (2026-09-05).  Rozdiely oproti btcusdt_3m_binance_tv: rrRatio 5, trailing vypnuty, slLookback 20, strukturny filter (BOS/CHoCH), obchodovanie z S/R aj likviditnych zon, a VYPNUTA londynska seansa - tam stratégia edge nema (break-even -0,0007 % za pat rokov), len riedi vysledok a plati poplatky.  Break-even poplatok 0,088 % na stranu proti 0,05 %, ktore berie Binance ako taker. Styri z piatich rokov su po realnych poplatkoch ziskove, spolu +17,0 %, max DD 7,1 %. Detaily v docs/SEANSY_2026-09-05.md; cisla po opravach adaptera (timeout limitky) v docs/OPRAVY_adapter_2026-09-05.md.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `showElliott` | `False` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set showElliott=false --set rrRatio=5.0 --set slLookback=20 --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true
```

### `btcusdt_3m_binance_ny_sl`  (btcusdt_binance)

BINANCE BTCUSDT.P 3m - NY profil + filter tesneho SL (2026-09-05).  Rozdiel oproti btcusdt_3m_binance_ny: minSlDistance 0,20 % ceny. Obchod, ktoreho SL je blizsie nez 0,2 % od vstupu, sa preskoci (SKIP: SL PRILIS TESNY). Rozsirenie portu, Pine ho nema - dovod su poplatky: zisk obchodu rastie s velkostou R, poplatok je vzdy percento z nominalu, takze tesne SL maju najhorsi pomer edge k poplatku.  Pat rokov, bez poplatkov: 149 obchodov namiesto 215 pri ROVNAKOM hrubom zisku (+22 907 vs +22 221 USDT pri 1 BTC), break-even 0,141 % namiesto 0,088 % na stranu. S poplatkami 0,05 %: +23,2 % za pat rokov namiesto +17,0 %, styri z piatich rokov ziskove, max DD 6,7 %. Prah 0,15 aj 0,25 % davaju ten isty smer (plato, nie spicka). Detaily v docs/OPTIMALIZACIA_2026-09-05.md.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `showElliott` | `False` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |
| `minSlDistance` | `0.2` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set showElliott=false --set rrRatio=5.0 --set slLookback=20 --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true --set minSlDistance=0.2
```

### `btcusdt_3m_binance_ny_sl_risk1`  (btcusdt_binance)

BINANCE BTC/USDT.P 3m - btcusdt_3m_binance_ny_sl s REALNYM risk-based sizingom namiesto 1 BTC/ETH.  maxLossDollar 100 = 1 % z dry_run_wallet 10 000 (pevna suma, nie percento z aktualneho zostatku). legacyPineSizing vypnuty, qty = maxLossDollar / SL vzdialenost. Paka 10 je len preto, aby sa pozicia pri SL 0,2 % (nominal ~50 000) zmestila na ucet - bez nej by Freqtrade stake orezal a riziko na obchod by bolo v skutocnosti mensie (viď warning 'stake orezany' v logu). Vysledky v docs/OPTIMALIZACIA_2026-09-05.md, sekcia 6.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `showElliott` | `False` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `maxLossDollar` | `100.0` |
| `tradeDirection` | `Long only` |
| `minSlDistance` | `0.2` |
| `leverage` | `10.0` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set showElliott=false --set rrRatio=5.0 --set slLookback=20 --set maxLossDollar=100.0 --set tradeDirection="Long only" --set minSlDistance=0.2 --set leverage=10.0
```

### `ethusdt_3m_binance_ny`  (ethusdt_binance)

BINANCE ETH/USDT.P 3m - ta ista strategia ako btcusdt_3m_binance_ny, prenesena na ETH.  POZOR - prahy NIE su prevzate v bodoch, ale prepocitane na ATR. Pine ich ma v absolutnych bodoch a na BTC znamenaju skoro nic (minImbSizePoints 2,5 = 0,037 ATR), kym na ETH by tie iste cisla znamenali ~0,9 ATR a zablokovali by takmer kazdy signal. Porovnanie by potom nemeralo strategiu, ale prisnost filtra.  Prepocet je z BTC 3m 2021-2026: median ATR(14) = 67,63 bodu, median cena 60 051. Detaily v docs/ETH_2026-09-05.md.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `pbMinRangePoints` | `0.03 atr` |
| `engMinRangePoints` | `0.03 atr` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `srClusterPoints` | `0.222 atr` |
| `liqSweepMinWick` | `0.074 atr` |
| `showElliott` | `False` |
| `imbMaxDistTicks` | `0.148 atr` |
| `minImbSizePoints` | `0.037 atr` |
| `state2ConfirmTicks` | `0.0015 atr` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `slBufferTicks` | `0.003 atr` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set pbMinRangePoints=0.03@atr --set engMinRangePoints=0.03@atr --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set srClusterPoints=0.222@atr --set liqSweepMinWick=0.074@atr --set showElliott=false --set imbMaxDistTicks=0.148@atr --set minImbSizePoints=0.037@atr --set state2ConfirmTicks=0.0015@atr --set rrRatio=5.0 --set slLookback=20 --set slBufferTicks=0.003@atr --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true
```

### `ethusdt_3m_binance_ny_sl`  (ethusdt_binance)

BINANCE ETH/USDT.P 3m - ethusdt_3m_binance_ny + filter tesneho SL (minSlDistance 0,20 % ceny).  Nezavisle overenie filtra, ktory bol najdeny na BTC (btcusdt_3m_binance_ny_sl): na ETH sa NIC neladilo, prah 0,20 % je prevzaty. Pat rokov bez poplatkov: 164 obchodov namiesto 203 pri rovnakom hrubom zisku, break-even 0,096 % namiesto 0,056 % na stranu, lepsi v styroch rokoch z piatich (piaty rovnaky). S poplatkami 0,05 % vsetkych pat rokov ziskovych. Detaily v docs/OPTIMALIZACIA_2026-09-05.md.  Prahy v ATR su prevzate z ethusdt_3m_binance_ny (viz jeho komentar). Spusta sa cez --pairs ETH/USDT:USDT, ETH nie je vo whiteliste.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `pbMinRangePoints` | `0.03 atr` |
| `engMinRangePoints` | `0.03 atr` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `srClusterPoints` | `0.222 atr` |
| `liqSweepMinWick` | `0.074 atr` |
| `showElliott` | `False` |
| `imbMaxDistTicks` | `0.148 atr` |
| `minImbSizePoints` | `0.037 atr` |
| `state2ConfirmTicks` | `0.0015 atr` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `slBufferTicks` | `0.003 atr` |
| `tradeDirection` | `Long only` |
| `tickDollarValue` | `0.5` |
| `legacyPineSizing` | `True` |
| `minSlDistance` | `0.2` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set pbMinRangePoints=0.03@atr --set engMinRangePoints=0.03@atr --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set srClusterPoints=0.222@atr --set liqSweepMinWick=0.074@atr --set showElliott=false --set imbMaxDistTicks=0.148@atr --set minImbSizePoints=0.037@atr --set state2ConfirmTicks=0.0015@atr --set rrRatio=5.0 --set slLookback=20 --set slBufferTicks=0.003@atr --set tradeDirection="Long only" --set tickDollarValue=0.5 --set legacyPineSizing=true --set minSlDistance=0.2
```

### `ethusdt_3m_binance_ny_sl_risk1`  (ethusdt_binance)

BINANCE ETH/USDT.P 3m - ethusdt_3m_binance_ny_sl s REALNYM risk-based sizingom namiesto 1 BTC/ETH.  maxLossDollar 100 = 1 % z dry_run_wallet 10 000 (pevna suma, nie percento z aktualneho zostatku). legacyPineSizing vypnuty, qty = maxLossDollar / SL vzdialenost. Paka 10 je len preto, aby sa pozicia pri SL 0,2 % (nominal ~50 000) zmestila na ucet - bez nej by Freqtrade stake orezal a riziko na obchod by bolo v skutocnosti mensie (viď warning 'stake orezany' v logu). Spusta sa cez --pairs ETH/USDT:USDT. Vysledky v docs/OPTIMALIZACIA_2026-09-05.md, sekcia 6.

Odchýlky od Pine defaultov:

| Parameter | Hodnota |
|---|---|
| `enablePinBarEntry` | `True` |
| `enableEngulfingEntry` | `True` |
| `pbMinRangePoints` | `0.03 atr` |
| `engMinRangePoints` | `0.03 atr` |
| `enableSrTrading` | `True` |
| `enableLqTrading` | `True` |
| `sess2ZoneStartH` | `8` |
| `sess3On` | `False` |
| `useStructureFilter` | `True` |
| `srClusterPoints` | `0.222 atr` |
| `liqSweepMinWick` | `0.074 atr` |
| `showElliott` | `False` |
| `imbMaxDistTicks` | `0.148 atr` |
| `minImbSizePoints` | `0.037 atr` |
| `state2ConfirmTicks` | `0.0015 atr` |
| `rrRatio` | `5.0` |
| `slLookback` | `20` |
| `slBufferTicks` | `0.003 atr` |
| `maxLossDollar` | `100.0` |
| `tradeDirection` | `Long only` |
| `minSlDistance` | `0.2` |
| `leverage` | `10.0` |

Ako `--set` pre CLI:

```
--set enablePinBarEntry=true --set enableEngulfingEntry=true --set pbMinRangePoints=0.03@atr --set engMinRangePoints=0.03@atr --set enableSrTrading=true --set enableLqTrading=true --set sess2ZoneStartH=8 --set sess3On=false --set useStructureFilter=true --set srClusterPoints=0.222@atr --set liqSweepMinWick=0.074@atr --set showElliott=false --set imbMaxDistTicks=0.148@atr --set minImbSizePoints=0.037@atr --set state2ConfirmTicks=0.0015@atr --set rrRatio=5.0 --set slLookback=20 --set slBufferTicks=0.003@atr --set maxLossDollar=100.0 --set tradeDirection="Long only" --set minSlDistance=0.2 --set leverage=10.0
```

