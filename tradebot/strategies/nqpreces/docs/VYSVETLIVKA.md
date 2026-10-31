# NQ PRECISION 1.0 — ako funguje

_Variant na ES: logika a parametre sú tie isté ako v `nqprec` (MNQ); prahy v ATR sa prispôsobia trhu sami, prahy v bodoch treba nastaviť v profile._

> V jednej vete: o 9:59:55 NY sa pozrie, či je cena nad alebo pod rozpätím 9:30–9:45, a na pár minút ide týmto smerom s malým cieľom a veľkým stopom.

Prepis Rust stratégie „NQ Precision Bot“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026. Predloha beží na tickoch, port na 1m sviečkach.

## Rozpätie
- **Opening range** = high a low sviečok 9:30–9:45 NY.

## Kedy vstúpi
- Jediná **snímka o 10:00 NY** (predloha 9:59:55; na 1m = zavretie sviečky 9:59): cena nad rozpätím → long, pod → short, vnútri → v ten deň nič.
- **Filtre:** objem poslednej sviečky voči priemeru dňa (RVOL 0,5–1,5) a krátke ATR voči dlhému (1,0–2,5) musia byť v pásme.

## Stop a cieľ
- **Stop 2,2 × ATR**, **cieľ 0,3 × ATR** — cieľ je veľmi blízko, stratégia stavia na vysokej úspešnosti.
- Po **8 minútach** sa pozícia zavrie, ak ju dovtedy nezavrel stop ani cieľ.

## Slovníček
- **ATR** — priemerný rozsah sviečky (14 sviečok).
- **RVOL** — relatívny objem.
