# Pine indikátory

Samostatné TradingView skripty, ktoré nepatria k žiadnej portovanej stratégii —
nemajú balík v `tradebot/strategies/`, nebežia v backteste a neplatí pre ne parita
s configom. Sú tu preto, aby sa nestratili a aby bolo vidieť, z čoho sa prípadný
budúci port vychádza.

Pine zdroje portovaných stratégií sú inde: `tradebot/strategies/<kľúč>/docs/sources/`.

| súbor | čo robí |
|---|---|
| [big7_basket_ema.pine](big7_basket_ema.pine) | smer Nasdaqu: vážený kôš Big 7 + SOXX + QQQ zlúčené do skóre −100…+100, signály LONG / SELL a varovania na úzky ťah — vysvetlivky k panelu sú v [big7_vysvetlivky.md](big7_vysvetlivky.md) |
| [big7_do_ibs.pine](big7_do_ibs.pine) | ten istý výpočet ako blok do IBS stratégie (Pine v6) — filter smeru obchodov; postup vloženia je v [big7_do_ibs.md](big7_do_ibs.md) |
| [ibs_big7.pine](ibs_big7.pine) | celá IBS Imbalance Breakout Strategy (v6) s už vloženým blokom Big 7 — na priame nahradenie skriptu v Pine editore |

## Prečo Big 7 nebeží v našom Testeri

Kôš potrebuje sedem samostatných akciových feedov (NVDA, MSFT, AAPL, AMZN, GOOGL,
META, TSLA). V `data_archive/tester/` sú dnes len indexy, meny, komodity a krypto —
jednotlivé akcie tam nie sú, takže sa to nedá prehrať ani vo Freqtrade, ani
v emulátore MultiCharts.

Keby to raz malo ísť do backtestu, poradie krokov je:

1. stiahnuť sedem CFD na akcie z Dukascopy a prehnať ich `tester.dukas_import`
   (obal `./dukas-import.sh`) — importér ich rozdelí po rokoch do archívu,
2. dopísať ich do `tradebot/core/instruments_dukascopy.json`,
3. postaviť z toho stratégiu podľa [docs/STRATEGIE.md](../STRATEGIE.md); kôš by
   bol siedmimi informatívnymi feedmi cez `informative_tfs` + `htf_feeder`,
   rovnako ako IBS berie detekčný TF.

Je to dátová robota, nie indikátorová — bez tých siedmich feedov sa na tom nedá
zmerať vôbec nič.
