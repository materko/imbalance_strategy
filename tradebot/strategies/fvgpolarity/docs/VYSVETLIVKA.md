# FVG POLARITY — ako funguje

> V jednej vete: keď vznikne medzera (FVG), stratégia hneď otvorí obchod smerom k nej a drží ho, kým sa cena medzery nedotkne.

Podľa zadania s nákresom; 15m graf, MNQ.

## Ako vznikne obchod
1. Na každej sviečke sa pozrie na posledné tri:
   - **medvedia medzera** (low 1. sviečky nad high 3.) leží nad cenou → **long** k nej,
   - **býčia medzera** leží pod cenou → **short** k nej.
2. Vstup market na zavretí 3. sviečky (vyplní sa na otvorení ďalšej). Kým obchod beží, ďalšie medzery sa neobchodujú.

## Stop a cieľ
- **Cieľ** = dotyk medzery (bližšia hrana, stred alebo vzdialená hrana).
- **Stop** v bodoch od vstupu (default 20).

## Čo môžeš nastaviť
- Min. veľkosť medzery, kam do medzery mieri cieľ, stop v bodoch.

## Slovníček
- **Imbalance (FVG)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“.
