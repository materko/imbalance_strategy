# DAILY OPEN 1.0 — ako funguje

> V jednej vete: o polnoci sa zapamätá cena; keď ju ráno trh prerazí smerom hore o 30 bodov, stratégia kúpi a drží do konca dňa.

Podľa videa Ali Caseyho (StatOasis, „Easy Nasdaq Scalping Strategy“). NQ / MNQ, 1h graf.

## Ako vznikne obchod
1. **Úroveň** = zavretie sviečky, ktorá končí o polnoci New York.
2. Od **8:00** New York: keď je cena nad úrovňou + 30 bodov → **long** (stop order na tej cene, alebo zavretie sviečky nad ňou).
3. Voliteľne: prieraz nad úroveň už v noci (pred 8:00); voliteľne aj short zrkadlovo pod úrovňou. Jeden obchod za deň.

## Stop a cieľ
- Stop 50 bodov (1 000 $ na NQ), bez cieľa — výstup o **16:00** New York.
- Dá sa nastaviť aj cieľ v bodoch a iný čas výstupu.

## Čo z testov vieme
Podľa videa zarába od roku 2007; na MNQ 2020–2026 je pôvodné nastavenie len slabo ziskové (PF ~1,08). Vysoký win rate dávajú len nastavenia s malým cieľom a veľkým stopom — to je rizikové.

## Slovníček
- **Stop order** — nákup, keď cena dosiahne zadanú úroveň (prieraz).
- **PF (profit factor)** — zisky delené stratami; nad 1 = zisková stratégia.
