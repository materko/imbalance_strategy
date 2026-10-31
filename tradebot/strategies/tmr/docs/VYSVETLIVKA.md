# T-MEAN REVERSION 1.0 — ako funguje

> V jednej vete: keď piatok zavrie v strate, v pondelok popoludní sa kúpi a v stredu večer predá — stavka na odraz po slabom konci týždňa.

Prepis Rust stratégie „T-Mean Reversion“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026. Len long, časy UTC.

## Kedy vstúpi
- **Červený piatok:** denná sviečka piatku (kalendárny deň UTC) zavrela pod svojím otvorením.
- Potom v **pondelok o 17:00 UTC** (12:00 NY v zime) long trhom. Raz za týždeň, len bez pozície.

## Kedy vystúpi
- V **stredu o 20:00 UTC** sa pozícia zavrie.

## Stop a cieľ
- Predloha **nemá stop ani cieľ**. Port má len poistku 10 % od vstupu (dá sa nastaviť `stopPct`).

## Na čo pozor
- Je to kalendárny jav: obchod raz za týždeň a len po červenom piatku, teda **okolo 20–25 obchodov za rok** — hranicu smernice 150 obchodov za rok z princípu nesplní.

## Slovníček
- **Mean reversion** — stavka na návrat ceny po prudkom pohybe.
