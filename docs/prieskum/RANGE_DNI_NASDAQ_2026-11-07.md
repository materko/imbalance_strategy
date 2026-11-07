# Rangeový deň na Nasdaqu (MNQ) — prieskum 7. 11. 2026

Dáta: MNQ 1m Databento, RTH 9:30–16:00 NY, 1 264 dní (10/2021–9/2026). Ladenie do 4. 9. 2025, odložený rok potom.
Skripty: features.py (denné črty o 10:30), fade.py (fade okrajov IB), vwapfade.py (návrat k VWAP).

## Ako často je range deň
- Range deň (zavretie v strednej polovici rozsahu dňa, deň nerozšíril IB viac ako 1,8×): 26 % dní v ladení, 35 % v odloženom roku.
- Trendový deň (zavretie v krajných 15 % a rozšírenie > 2× IB): 16 %.
- Samostatné ukazovatele známe o 10:30 (gap, poloha otvorenia voči včerajšej value area, nočný rozsah, objem prvej hodiny,
  kríženia VWAP, deň v týždni) predpovedajú range deň slabo (rozdiely 5–10 p. b.) a v odloženom roku nestabilne.

## Čo funguje
1. **Fade predĺženia IB pri vyváženom IB** — keď IB (9:30–10:30) zavrie blízko svojho stredu (|poloha − 0,5| < 0,25),
   short limitkou na IBH + 0,5–0,6·IBw (long zrkadlovo), stop 0,15–0,35·IBw, cieľ druhý okraj IB alebo stred.
   PF po rokoch (a=0,5, s=0,25, cieľ opačný okraj): 1,05 · 2,18 · 1,26 · 1,62 · **1,31** (odložený rok), ~65 obch/rok.
   **Slabina:** plató len v stope a cieli; vstup 0,4 alebo 0,75·IBw už nefunguje → krehké.
2. **Návrat k VWAP pri úzkom IB** (IB < 0,86 × priemer 20 dní) — zavretie 0,3·ATR od VWAP po 10:30, stop 0,15–0,5·ATR,
   cieľ VWAP: PF 1,14 · 1,1 · 1,21 · 1,83 · **1,09–1,27** (odložený rok), ~73 obch/rok; plató v stope.
3. Bez filtra dňa nefunguje ani jedno (PF ≈ 1,0 a v odloženom roku pod 1).

## Záver
Edge existuje, ale je stredný (PF 1,2–1,4) a pri fade IB krehký. Obe pravidlá spolu dajú ~130 obchodov za rok
(pod hranicou 150). Ďalší krok: napísať stratégiu „RANGE DEŇ 1.0“ (oba režimy, filter dňa), pustiť smernicu
(emulátor, typ vstupu, plató, odložený rok, iný trh) a až potom posúdiť.

## Pokračovanie (7. 11. večer) — pravidlo 80 % (Market Profile) — NAJSILNEJŠIE
Skripty rule80.py, rule80b.py. Pravidlo: RTH otvorí mimo včerajšej value area (70 % objemu), prvé zavretie 30m sviečky
späť vo VA → obchod smerom dovnútra; stop za extrémom dňa od otvorenia (+ s·šírky VA), cieľ POC alebo opačný okraj VA,
posledný vstup 12:00–14:00, výstup najneskôr 15:55.

| variant (MNQ) | 21/22 | 22/23 | 23/24 | 24/25 | 25/26 (odložený) | obch/rok | WR |
|---|---|---|---|---|---|---|---|
| cieľ POC, s 0,1, vstup do 12:00 | 1,34 | 1,38 | 1,37 | 3,83 | **1,31** | 43 | 75 % |
| cieľ POC, s 0,1, vstup do 13:00 | 1,30 | 1,46 | 1,36 | 2,66 | **1,41** | 48 | 74 % |
| cieľ opačný okraj VA, s 0, do 12:00 | 1,50 | 1,66 | 1,16 | 2,44 | **1,34** | 61 | 63 % |

- Plató: všetky susedné nastavenia (stop 0–0,25, vstup 11:30–14:00, cieľ POC / okraj VA) ziskové vo všetkých 5 rokoch.
- Iný zdroj dát (NAS100 Dukascopy, krok 8): cieľ POC PF 1,41–1,57, 4 z 5 rokov v pluse → jav je skutočný, nie artefakt dát.
- ES a MGC: nefunguje (PF ≈ 1,0) — jav je špecifický pre Nasdaq.
- 15m sviečky na návrat horšie, 30m najlepšie. Obchodov 40–70 za rok (pod hranicou 150).
