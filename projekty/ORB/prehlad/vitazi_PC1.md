# Víťazi z PC1 — presné nastavenia

Beh na Mac mini, **13 745 pokusov**, stav k 18. 9. 2026 03:44.
Posledný rok, všetko v R, `minSlDistance = 0,2 %` natvrdo, R orezané na 10.

Poradie určuje **spodná hranica spoľahlivosti** (`exp − sd/√n`), nie samotná expectancy —
aby vzorka so 150 obchodmi neprebila vzorku so 400 len šťastím.

---

## Prehľad

| Trh | TF | Seansa | Vstup | Obch. | WR | PF | Na obchod | Max pokles | Skóre |
|---|---|---|---|---|---|---|---|---|---|
| **BTC/USDT:USDT** | 3m | london | close | 270 | 33,3 % | **2,137** | **0,758 R** | 12,0 R | **9,55** |
| **MNQ/USD** | 15m | both | close | **417** | 32,1 % | 1,599 | 0,405 R | 19,25 R | 6,13 |
| **XAU/USD** | 30m | london | close | 167 | 49,1 % | 1,779 | 0,380 R | **6,67 R** | 3,39 |

Zisk celkom: BTC 204,62 R · MNQ 168,89 R · XAU 63,4 R.

**Čo si všimnúť:** na BTC aj zlate vyhráva **londýnska** seansa, nie newyorská. Na MNQ obe.
Vstup `close` vyhral všade — ale `stop` sa vtedy **nedal otestovať** (chyba, dnes opravená).

---

## MNQ/USD — 15m, obe seansy

Najviac obchodov (417) a druhá najlepšia expectancy. Najhorší pokles zo všetkých troch (19,25 R).

| Parameter | Default | **Víťaz** |
|---|---|---|
| Dĺžka NY rangu | 15 | **30 min** |
| Koniec londýnskej seansy | 16 | **13** |
| Okno na vstup | 90 | **240 min** |
| Max obchodov na seansu | 1 | **4** |
| Šírka rangu | 0,15–1,5 % | **0,1–0,75 %** |
| Buffer prerazenia | 0,05 ATR | **0,1 ATR** |
| SL režim | opposite | **atr**, násobok **0,75**, buffer **0** |
| Cieľ | rr 1,5 | **atr, násobok 3,0** |
| ATR dĺžka | 14 | **21** |
| Volume filter | vypnutý | **zapnutý** |
| Len Po–Pi | áno | **nie** |
| minSlDistance | 0 | **0,2 %** |

## XAU/USD — 30m, len Londýn

Najmenší pokles (6,67 R) a najvyšší winrate (49,1 %), ale len 167 obchodov — tesne nad
hranicou 150, pod ktorou sa výsledky nezobrazujú.

| Parameter | Default | **Víťaz** |
|---|---|---|
| Seansy | both | **len london** |
| Dĺžka NY rangu | 15 | **30 min** |
| Okno na vstup | 90 | **60 min** |
| Buffer prerazenia | 0,05 ATR | **0** |
| Poloha zavretia | 50 % | **0 %** (bez filtra) |
| Šírka rangu — min | 0,15 % | **0,1 %** |
| SL režim | opposite | **atr**, násobok **1,5**, buffer **0,25** |
| RRR | 1,5 | **3,0** |
| ATR dĺžka | 14 | **21** |
| minSlDistance | 0 | **0,2 %** |

## BTC/USDT:USDT — 3m, len Londýn

Najlepšia expectancy (0,758 R) aj PF (2,137). Jediný trh, kde sizing funguje správne —
dá sa obchodovať zlomok kontraktu. Pozor: `ext = 4` znamená, že štyri obchody narazili
na strop R = 10.

| Parameter | Default | **Víťaz** |
|---|---|---|
| Seansy | both | **len london** |
| Dĺžka londýnskeho rangu | 15 | **60 min** |
| Dĺžka NY rangu | 15 | **30 min** |
| Koniec londýnskej seansy | 16 | **13** |
| Okno na vstup | 90 | **120 min** |
| Max obchodov na seansu | 1 | **4** |
| Šírka rangu | 0,15–1,5 % | **0–2,0 %** (bez dolnej hranice) |
| Poloha zavretia | 50 % | **0 %** |
| Buffer prerazenia | 0,05 ATR | **0,2 ATR** |
| SL režim | opposite | **break_candle**, buffer **0,05** |
| Cieľ | rr 1,5 | **measured, násobok 1,5** |
| Volume násobok | 1,5 | **2,0** |
| ATR dĺžka | 14 | **21** |
| minSlDistance | 0 | **0,2 %** |

---

## Čo majú spoločné

Naprieč všetkými tromi trhmi sa zhodujú štyri veci — to je silnejší signál než ktorýkoľvek
jednotlivý víťaz:

| | |
|---|---|
| **ATR dĺžka 21** namiesto 14 | všetky tri |
| **30-minútový NY range** namiesto 15 | všetky tri |
| **minSlDistance 0,2 %** | všetky tri (ale to je nastavené natvrdo, nie výsledok ladenia) |
| **SL nie je `opposite`** | všetky tri — dve `atr`, jedna `break_candle` |

Naopak sa rozchádzajú v cieli: MNQ `atr`, XAU `rr`, BTC `measured`.
