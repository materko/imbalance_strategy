# LONDON LIQUIDITY IFVG 1.0 — ako funguje

_Variant na ES: logika a parametre sú tie isté ako v `lliq` (MNQ); prahy v ATR sa prispôsobia trhu sami, prahy v bodoch treba nastaviť v profile._

> V jednej vete: večer sa čaká, kým cena vyberie high alebo low popoludňajšej seansy a vráti sa, a vstúpi sa proti tomu výberu, keď cena prerazí opačný FVG.

Prepis Rust stratégie „London Liquidity / IFVG by Shujat“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026.

## Seansa
- High a low sviečok **13:00–19:00 NY** (napriek menu predlohy je to popoludnie New Yorku, nie Londýn).

## Sweep (LS)
- Medzi **19:15 a 23:45 NY** cena zavrie nad high seansy a potom sa vráti pod neho sviečkou s veľkým telom (telo > 50 % sviečky) → sweep hore, hľadá sa short. Zrkadlovo pri low → long.

## Kedy vstúpi
- **IFVG:** FVG (medzera medzi sviečkami) z popoludnia alebo po sweepe, ktorý cena **zavretím prerazí proti jeho smeru**. Po sweepe hore musí ísť o býčí FVG prerazený nadol → short; po sweepe dole medvedí FVG prerazený nahor → long.
- Jeden obchod za deň, trhom na zavretí.

## Stop a cieľ
- **Stop** 1,5 × ATR (alebo za swing posledných 5 sviečok), **cieľ** 1,5 × ATR (alebo opačná strana seansy, alebo RR).

## Slovníček
- **FVG** — medzera medzi high sviečky a low sviečky o dve ďalej, ktorú prostredná sviečka nevyplnila.
- **Sweep** — výber likvidity: krátke prerazenie úrovne a návrat.
