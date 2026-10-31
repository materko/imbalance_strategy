# WILLIAMS %R LONG 1.0 — ako funguje

_Variant na ES: logika a parametre sú tie isté ako v `wpr` (MNQ); prahy v ATR sa prispôsobia trhu sami, prahy v bodoch treba nastaviť v profile._

> V jednej vete: keď je cena pri dne posledných 14 sviečok (Williams %R pod −90), kúpi sa a predá pri prvom odraze.

Prepis Rust stratégie „Williams %R Long“ (roboquant.dev, sama port Pine v6), ktorú poslal používateľ 29. 10. 2026. Len long.

## Kedy vstúpi
- **Williams %R(14)** zavrie pod **−90** (cena pri spodku rozpätia posledných 14 sviečok) → long trhom.
- Po obchode ďalší vstup až keď %R najprv vystúpi nad −90 a znova spadne (nie opakovane v tom istom prepade).

## Kedy vystúpi
- Sviečka **zavrie nad high predošlej sviečky**, alebo %R vystúpi na **−30** (predvolene hociktoré z toho).

## Stop a cieľ
- Predloha **nemá stop**. Port má len poistku 10 % od vstupu (`stopPct`). Cieľ je výstup podľa pravidiel vyššie.

## Slovníček
- **Williams %R** — kde je zavretie v rozpätí posledných N sviečok: 0 = na vrchu, −100 = na spodku.
