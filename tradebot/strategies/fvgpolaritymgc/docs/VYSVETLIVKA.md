# FVG POLARITY (MGC) — ako funguje

> V jednej vete: tá istá stratégia ako **FVG POLARITY**, len s nastaveniami na zlato (MGC futures) — keď vznikne FVG, ďalšia sviečka otvorí obchod smerom k medzere a drží ho, kým sa cena medzery nedotkne.

Profily sú 2 najlepšie z víkendového hľadania na MGC (5. 10. 2026): WK 161 (RR 1,13, v zisku 4 z 5 rokov) a WK 221 (RR 0,9). Testované **bez poplatkov** a so stopom len 2 body (20 $) — náklady ~0,3–0,45 bodu na obchod sú podstatná časť rizika, pred živým nasadením preveriť podľa smernice s nákladmi.


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
