# SIGMA BREAKOUT 1.0 — ako funguje

> V jednej vete: okolo otvorenia New Yorku sa nakreslí pásmo bežného pohybu pre každú minútu dňa a keď ho cena zavretím opustí, ide sa jej smerom až do konca dňa.

Prepis Rust stratégie „Sigma Breakout“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026. Podobná našej NOA.

## Pásmo
- **Referencia** = cena otvorenia 9:30 NY (alebo VWAP od 9:30).
- **Sigma** = o koľko sa cena v tú istú minútu (napr. 11:05) bežne vzdialila od otvorenia — priemer za posledných **14 dní**.
- Pásmo = referencia ± sigma.

## Kedy vstúpi
- Sviečka **zavrie nad pásmom** → long, **pod pásmom** → short. Opačný prieraz pozíciu **otočí**.

## Kedy vystúpi
- O **16:00 NY** sa zavrie všetko.

## Stop a cieľ
- Predloha predvolene **bez stopu** (port: poistka 10 %); cieľ nemá — výstup je otočka alebo 16:00.

## Slovníček
- **VWAP** — priemerná cena vážená objemom od 9:30 NY.
