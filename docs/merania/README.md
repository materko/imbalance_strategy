# Merania

Datované dokumenty s číslami. Pravidlo: každé meranie má výsledky **po rokoch** na piatich
referenčných oknách (`20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
`20240904-20250904`, `20250904-20260904`), nie len súčet — jeden rok o stratégii nič
nepovie. Kľúčová metrika je **break-even poplatok** (% na stranu): koľko smie burza brať,
aby beh vyšiel na nulu. Binance taker berie 0,05 %.

Chronologicky:

| dokument | o čom |
|---|---|
| [BACKTEST_rok_btcusdt_2026-09-04](BACKTEST_rok_btcusdt_2026-09-04.md) | rok s reálnymi poplatkami, prečo ich RR 1 neunesie |
| [BACKTEST_rok_rr25_all3_2026-09-04](BACKTEST_rok_rr25_all3_2026-09-04.md) | RR 2,5, tri entry modely, trailing |
| [SWEEP_rr_a_tf_2026-09-04](SWEEP_rr_a_tf_2026-09-04.md) | RR pomer a timeframe grafu |
| [HYPEROPT_btcusdt_2026-09-04](HYPEROPT_btcusdt_2026-09-04.md) | široký hyperopt overfituje |
| [HYPEROPT_uzky_2026-09-04](HYPEROPT_uzky_2026-09-04.md) | úzky hyperopt nenašiel nič |
| [HYPOTEZA_koniec_seansy_2026-09-04](HYPOTEZA_koniec_seansy_2026-09-04.md) | kde vznikajú straty |
| [FILTRE_vstupu_2026-09-04](FILTRE_vstupu_2026-09-04.md) | štruktúrny a volume filter |
| [SEANSY_2026-09-05](SEANSY_2026-09-05.md) | NY má edge, Londýn nie; hodiny neladiť |
| [PAKA_2026-09-05](PAKA_2026-09-05.md) | páka mení mierku, nie edge |
| [EXEKUCIA_maker_taker_2026-09-05](EXEKUCIA_maker_taker_2026-09-05.md) | koľko príkazov by ležalo v knihe |
| [OPTIMALIZACIA_2026-09-05](OPTIMALIZACIA_2026-09-05.md) | filter tesného SL, regime filtre, časový stop, ETH, ATR vs %, risk sizing |
| [NAS100_dukas_simulator_2026-09-06](NAS100_dukas_simulator_2026-09-06.md) | NAS100 z Dukascopy: simulátor, MultiCharts a emulátor vedľa seba |

Súhrn, kam sa merania dopracovali, je v [README repozitára](../../README.md) v sekcii
„Kde sme s výsledkami". Parita s TradingView (nie meranie edge) je v
[GOLDEN_binance_2026-08-24](../GOLDEN_binance_2026-08-24.md),
[AUDIT_pine_2026-09-05](../AUDIT_pine_2026-09-05.md) a
[OPRAVY_adapter_2026-09-05](../OPRAVY_adapter_2026-09-05.md).
