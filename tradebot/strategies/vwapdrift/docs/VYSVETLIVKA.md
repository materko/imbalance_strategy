# VWAP Session 1.0 — ako funguje

> V jednej vete: keď VWAP (priemerná cena dňa) jasne stúpa, stratégia čaká na prvý návrat ceny k nemu a kupuje (pri klesajúcom VWAP predáva).

Predvolené pravidlá sú podľa videa Mattea Contiho („video“ režim); dá sa prepnúť na vlastné nastavenia („custom“).

## Ako vznikne obchod (režim video)
1. **VWAP** od 9:30 New York z 15m sviečok, graf 5m.
2. Každých 15 minút otázka **„je trend?“** — long: cena nad VWAP, VWAP za 15 min stúpa, cena za hodinu aspoň +0,1 % (short zrkadlovo). Prvú hodinu sa neobchoduje.
3. **Spúšťač:** prvá sviečka proti trendu (pri longu červená) po kladnej odpovedi → market na otvorení ďalšej.

## Stop a cieľ
- Long: stop 80 bodov, cieľ 40; short: stop 80, cieľ 50.
- Max. 4 obchody a 2 straty za deň, po 15:30 žiadny nový obchod, o 15:55 sa všetko zatvorí.

## Režim custom
Drift = sklon VWAP v ATR, cena musí najprv odísť od VWAP, vstup na pullback k VWAP rôznymi spôsobmi (zavretie, limitka, reakčná sviečka, pin bar, engulfing), stop za pullback / VWAP / ATR.

## Slovníček
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia); ukazuje „férovú“ cenu dňa podľa obchodovaného objemu.
- **Drift** — sklon VWAP: stúpa = deň kupcov, klesá = deň predajcov.
- **Pullback** — dočasný návrat ceny proti trendu.
