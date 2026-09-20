# ORB — priebezne vysledky

aktualizovane 2026-09-18 03:44, pokusov 13745

**Vsetky cisla su v R** (nasobok rizika na obchod), spocitane z jednotlivych obchodov. Staršie tabulky, kde bol zisk v percentach uctu, boli zavadzajuce — backtester klampuje velkost pozicie na 1 kontrakt, takze siroky stop znamenal vacsiu dolarovu stratu a vyzeral lepsie, nez bol.

**Poradie v tabulke nie je podla stlpca „na obchod".** Zoradene je podla spodnej hranice spolahlivosti (`na obchod - smerodajna chyba`), aby nastavenie so 150 obchodmi nemohlo prebit nastavenie s 300 len tym, ze malo stastie na mensej vzorke. Nastavenia pod 150 obchodov za rok sa nezobrazuju vobec — pri takej vzorke je vysledok nahoda, nie edge.

Vsetky nastavenia zatvaraju poziciu na konci seansy; nic nedrzi cez noc.

## MNQ (Nasdaq, Databento)

| TF | seansa | vstup | RRR | SL | obchodov | winrate | PF | zisk | na obchod | max pokles |
|---|---|---|---|---|---|---|---|---|---|---|
| 15m | both | close | 2.0 | atr | 417 | 32.13 % | 1.599 | 168.89 R | 0.405 R | 19.25 R |
| 15m | both | close | 2.0 | atr | 154 | 51.95 % | 2.141 | 84.46 R | 0.5485 R | 7.01 R |
| 15m | both | close | 2.5 | atr | 292 | 40.75 % | 1.676 | 116.47 R | 0.3989 R | 9.41 R |
| 15m | both | close | 3.0 | atr | 292 | 36.64 % | 1.63 | 116.08 R | 0.3975 R | 10.98 R |
| 15m | both | close | 2.0 | atr | 292 | 44.18 % | 1.671 | 108.86 R | 0.3728 R | 10.22 R |
| 15m | both | close | 1.8 | atr | 292 | 48.29 % | 1.672 | 101.53 R | 0.3477 R | 10.5 R |
| 15m | both | close | 2.5 | break_candle | 295 | 47.12 % | 1.664 | 99.93 R | 0.3388 R | 11.2 R |
| 15m | both | close | 2.5 | mid | 327 | 46.79 % | 1.626 | 94.71 R | 0.2896 R | 8.38 R |
| 15m | both | close | 2.5 | range_pct | 392 | 44.9 % | 1.512 | 105.17 R | 0.2683 R | 11.0 R |
| 15m | both | close | 1.5 | atr | 292 | 51.03 % | 1.563 | 80.46 R | 0.2756 R | 9.92 R |
| 15m | both | close | 2.5 | mid | 327 | 49.85 % | 1.596 | 84.97 R | 0.2599 R | 7.86 R |
| 15m | both | close | 2.0 | mid | 393 | 47.07 % | 1.476 | 94.33 R | 0.24 R | 11.0 R |
| 15m | both | close | 2.5 | range_pct | 370 | 52.16 % | 1.574 | 88.79 R | 0.24 R | 7.94 R |
| 15m | both | close | 2.5 | atr | 370 | 41.35 % | 1.451 | 96.64 R | 0.2612 R | 20.94 R |
| 15m | both | close | 2.0 | break_candle | 259 | 49.42 % | 1.611 | 76.57 R | 0.2956 R | 11.82 R |

## XAU/USD (zlato, Dukascopy)

| TF | seansa | vstup | RRR | SL | obchodov | winrate | PF | zisk | na obchod | max pokles |
|---|---|---|---|---|---|---|---|---|---|---|
| 30m | london | close | 3.0 | atr | 167 | 49.1 % | 1.779 | 63.4 R | 0.3796 R | 6.67 R |
| 30m | london | close | 2.5 | atr | 167 | 49.1 % | 1.771 | 62.67 R | 0.3753 R | 6.55 R |
| 30m | london | close | 2.0 | atr | 167 | 50.3 % | 1.699 | 55.75 R | 0.3338 R | 6.0 R |
| 30m | london | close | 1.8 | atr | 167 | 50.3 % | 1.639 | 50.99 R | 0.3053 R | 6.0 R |
| 30m | london | close | 3.0 | opposite | 162 | 40.12 % | 1.544 | 51.7 R | 0.3192 R | 12.44 R |
| 30m | london | close | 2.5 | opposite | 180 | 46.11 % | 1.553 | 50.3 R | 0.2794 R | 9.48 R |
| 30m | london | close | 1.5 | atr | 167 | 51.5 % | 1.524 | 40.97 R | 0.2453 R | 6.51 R |
| 30m | london | close | 1.8 | opposite | 180 | 48.33 % | 1.496 | 43.62 R | 0.2423 R | 8.14 R |
| 15m | london | close | 3.0 | opposite | 179 | 40.22 % | 1.467 | 47.28 R | 0.2641 R | 12.6 R |
| 30m | london | close | 1.5 | opposite | 180 | 50.0 % | 1.485 | 41.4 R | 0.23 R | 7.08 R |
| 30m | london | close | 3.0 | break_candle | 178 | 35.39 % | 1.422 | 47.63 R | 0.2676 R | 13.42 R |
| 30m | london | close | 2.0 | opposite | 180 | 46.67 % | 1.463 | 41.71 R | 0.2317 R | 9.48 R |
| 5m | london | close | 3.0 | opposite | 202 | 37.13 % | 1.383 | 47.28 R | 0.2341 R | 15.01 R |
| 15m | london | close | 3.0 | break_candle | 157 | 63.69 % | 1.636 | 29.13 R | 0.1855 R | 8.37 R |
| 15m | london | close | 2.5 | opposite | 181 | 40.88 % | 1.371 | 37.37 R | 0.2065 R | 12.6 R |

## BTC (Binance futures)

| TF | seansa | vstup | RRR | SL | obchodov | winrate | PF | zisk | na obchod | max pokles |
|---|---|---|---|---|---|---|---|---|---|---|
| 3m | london | close | 1.5 | break_candle | 270 | 33.33 % | 2.137 | 204.62 R | 0.7578 R | 12.0 R |
| 3m | london | close | 3.0 | break_candle | 461 | 37.31 % | 1.77 | 221.82 R | 0.4812 R | 15.0 R |
| 3m | london | close | 1.5 | atr | 185 | 29.19 % | 2.059 | 138.7 R | 0.7497 R | 9.0 R |
| 3m | london | close | 3.0 | atr | 488 | 35.04 % | 1.619 | 196.09 R | 0.4018 R | 20.0 R |
| 2m | london | close | 1.5 | break_candle | 433 | 23.56 % | 1.611 | 201.93 R | 0.4664 R | 20.79 R |
| 2m | london | close | 1.5 | atr | 425 | 17.18 % | 1.582 | 204.72 R | 0.4817 R | 24.57 R |
| 3m | london | close | 2.5 | break_candle | 467 | 39.4 % | 1.622 | 175.38 R | 0.3755 R | 13.5 R |
| 3m | london | close | 3.0 | break_candle | 477 | 41.51 % | 1.625 | 174.41 R | 0.3656 R | 13.91 R |
| 5m | london | close | 1.5 | break_candle | 223 | 33.63 % | 1.769 | 112.62 R | 0.505 R | 14.67 R |
| 5m | london | close | 3.0 | break_candle | 409 | 33.99 % | 1.505 | 135.51 R | 0.3313 R | 27.0 R |
| 3m | london | close | 3.0 | opposite | 346 | 39.6 % | 1.596 | 118.86 R | 0.3435 R | 13.87 R |
| 3m | london | close | 3.0 | mid | 412 | 36.65 % | 1.511 | 130.43 R | 0.3166 R | 15.98 R |
| 3m | london | close | 1.5 | mid | 392 | 48.98 % | 1.66 | 119.72 R | 0.3054 R | 9.26 R |
| 3m | london | close | 1.5 | range_pct | 392 | 48.72 % | 1.654 | 119.98 R | 0.3061 R | 9.23 R |
| 5m | london | close | 3.0 | opposite | 375 | 37.87 % | 1.547 | 123.19 R | 0.3285 R | 10.72 R |

