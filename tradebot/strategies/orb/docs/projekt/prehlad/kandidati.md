# Kandidáti na ďalšiu prácu

Zoznam nastavení, ktoré stoja za ďalšie overenie. **Nie je to výber na obchodovanie** —
všetko je z posledného roka a čaká to na päť okien.

Zoradené podľa **pomeru zisk/pokles**, nie podľa zisku. Pri prop účte rozhoduje, koľko
zarobíš na jednotku prepadu, nie absolútne číslo.

Zdroj: PC1, 13 745 pokusov, stav 18. 9. 2026.

| # | Trh | TF | Seansa | RRR | SL | Obch. | WR | PF | Zisk | Na obchod | Pokles | Zisk/pokles |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **BTC** | 3m | london | 1,5 | break_candle | 270 | 33,3 % | 2,14 | 204,6 R | **0,758 R** | 12,0 R | **17,1** |
| 2 | BTC | 3m | london | 1,5 | atr | 185 | 29,2 % | 2,06 | 138,7 R | 0,750 R | **9,0 R** | 15,4 |
| 3 | BTC | 3m | london | 3,0 | break_candle | **461** | 37,3 % | 1,77 | **221,8 R** | 0,481 R | 15,0 R | 14,8 |
| 4 | BTC | 3m | london | 1,5 | range_pct | 392 | 48,7 % | 1,65 | 120,0 R | 0,306 R | 9,2 R | 13,0 |
| 5 | BTC | 3m | london | 2,5 | break_candle | 467 | 39,4 % | 1,62 | 175,4 R | 0,376 R | 13,5 R | 13,0 |
| 6 | BTC | 3m | london | 1,5 | mid | 392 | 49,0 % | 1,66 | 119,7 R | 0,305 R | 9,3 R | 12,9 |
| 7 | BTC | 3m | london | 3,0 | break_candle | 477 | 41,5 % | 1,62 | 174,4 R | 0,366 R | 13,9 R | 12,5 |
| 8 | **MNQ** | 15m | both | 2,5 | atr | 292 | 40,8 % | 1,68 | 116,5 R | 0,399 R | 9,4 R | 12,4 |
| 9 | MNQ | 15m | both | 2,0 | atr | 154 | 52,0 % | 2,14 | 84,5 R | 0,548 R | 7,0 R | 12,0 |
| 10 | BTC | 5m | london | 3,0 | opposite | 375 | 37,9 % | 1,55 | 123,2 R | 0,329 R | 10,7 R | 11,5 |

## Ako to čítať

**BTC berie sedem miest z desiatich** — a vždy **3m graf, londýnska seansa**. Pri siedmich
rôznych nastaveniach to nie je náhoda; ten trh a to okno sú pre ORB priaznivé.

**Zlato sa do desiatky nedostalo.** Najlepšie malo pomer ~9,5. Má síce najnižší absolútny
pokles (6,67 R), ale aj najnižší zisk.

**Riadok 9 je pasca.** Najkrajšie čísla v tabuľke (WR 52 %, PF 2,14), ale 154 obchodov je
tesne nad hranicou, pod ktorou sa výsledky ani nezobrazujú — pri menších vzorkách vychádzali
expectancy až 1,0 R z čistej náhody. Tomuto riadku verím najmenej.

## Tri typy kandidáta

| Ak chceš | Riadok | Prečo |
|---|---|---|
| **najvyššiu expectancy** | 1 | 0,758 R na obchod, PF 2,14 |
| **frekvenciu** | 3 | 461 obchodov, najvyšší zisk 221,8 R |
| **pokoj** | 2 | najnižší pokles 9,0 R |

## Čo s nimi ďalej

1. **Päť referenčných okien** — bez toho sú to čísla z jedného roka
2. **Pretestovať s `entryMode = stop`** — opravené 18. 9., predtým každý taký beh padol.
   Pri ORB je vstup na prerazení prirodzenejší než na zavretí sviečky.
3. **Nulltest** — odlíšiteľné od náhody?
4. **Prop simulácia** až nakoniec, keď prejdú body 1–3
