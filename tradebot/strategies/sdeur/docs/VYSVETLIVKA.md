# SD ZÓNY EURUSD 1.0 — ako funguje

> V jednej vete: z miesta, odkiaľ cena v noci prudko odišla (zóna ponuky alebo dopytu), sa pri prvom návrate v londýnskej seanse vstúpi limitkou proti návratu, so stopom kúsok za zónou.

Zadanie 26. 10. 2026 na Euro FX futures (6E): kvalitné zóny z 5m–1h grafu, limitka na hrane, stop za zónou, cieľ 1 : 1 až 1 : 3.

## Ako vznikne zóna
1. **Báza** — 1 až 4 hodinové sviečky (knôt po knôt), ktoré sú najvyšším (supply) alebo najnižším (demand) miestom posledných hodín.
2. **Odchod** — cena od bázy odíde aspoň o 1 ATR do 8 hodín a bázu predtým neprerazí. Zóna platí až od zavretia sviečky, ktorá odchod dokončila.
3. **Kvalita** — len zóny z noci (posledná sviečka bázy 18:00–2:00 New York = Ázia), voliteľne výška zóny od–do.

## Ako vznikne obchod
- V okne vstupu (default 2:00–11:00 NY = Londýn) čaká limitka na **najbližšej** nedotknutej zóne — na jej bližšej hrane (alebo v hĺbke zóny).
- Zóna sa obchoduje len pri **prvom návrate**: keď sa jej cena dotkne mimo okna, minie sa bez obchodu.
- **Stop** za vzdialenejšou hranou + rezerva (0,25 ATR) + 1 tick, **cieľ** RR × riziko (default 1,5), najdlhšie 48 h.

## Slovníček
- **Supply zóna** — miesto, odkiaľ cena prudko klesla (predávajúci); pri návrate sa predáva.
- **Demand zóna** — miesto, odkiaľ cena prudko stúpla (kupujúci); pri návrate sa kupuje.
- **ATR** — priemerný rozsah sviečky; prahy v ATR sedia na pokojnom aj rušnom trhu.
- **6E** — CME Euro FX futures (125 000 EUR), 1 pip = 12,5 $; menší M6E má 1 pip = 1,25 $.
