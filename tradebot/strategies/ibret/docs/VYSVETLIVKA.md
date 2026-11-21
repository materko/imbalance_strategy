# IB RETRACE 1.0 — Initial Balance Max Retracement — ako funguje

> V jednej vete: keď cena po prvej hodine New Yorku zavrie za Initial Balance, stratégia počká na návrat späť do IB a vstúpi v smere prierazu so stopom za úrovňou, hlbšie než ktorú sa cena v ~70 % dní nevracia.

Podľa videa IB Lab „Max Retracement Price“ (používateľ 20. 11. 2026). Video dáva štatistiku, nie hotové pravidlá vstupu
a výstupu — tie sú navrhnuté tu a všetky úrovne sú parametre. **Úrovne sú zatiaľ dočasné (z videa)**, presné čísla
prinesie štatistika návratu ceny a podľa nej sa nastavia.

## Initial Balance (IB) a úrovne
- **IB** = high a low prvej hodiny seansy New York: **9:30–10:30 NY** (15:30–16:30 u nás).
- Úrovne sú **zlomky šírky IB od prerazenej hrany**, rovnako ako čiary v IB Lab:
  - long (prieraz hore): `0` = IB high, `0,5` = stred IB, `1` = IB low,
  - short (prieraz dole): `0` = IB low, `0,5` = stred IB, `1` = IB high.
- **Max retracement** (IB Lab) = najhlbší návrat ceny proti prierazu od prierazu do 16:00. Vo videu: v 70 % dní
  long (pondelok) najviac 0,60–0,69, short (utorok, single break) najviac 0,70–0,79.

## Prieraz
- Prieraz = **prvé zavretie sviečky za IB** po 10:30. Rozhoduje vždy prvý prieraz dňa — keď nesedí s nastavením,
  v ten deň sa neobchoduje.
- Sviečka prierazu sa musí otvoriť v okne **`breakFrom`–`breakTo`** (predvolene 10:30–11:25; IB Lab filtruje časy
  potvrdenia 10:30, 10:35, 10:40 …), v povolený **deň v týždni** a v povolenom smere.
- Voliteľne šírka IB v bodoch (`minIbPoints`, `maxIbPoints`).

## Vstup
- **pullback** (predvolene): hneď po prieraze **limitka na úrovni `entryRetr`** (0,25 = štvrtina IB späť dovnútra).
- **breakout**: market na zavretí sviečky prierazu.
- Limitka sa **zruší**, keď:
  - príde čas `lastEntry` (predvolene 13:30 — vo videu medián času max retracementu),
  - cena prerazí **druhú stranu IB** (deň už nie je „single break“),
  - cena dôjde do **cieľa bez návratu** (pohyb ušiel).
- Jeden obchod za deň.

## Stop a cieľ
- **Stop na úrovni `slRetr`** (predvolene 0,8 IB) + `slBufferTicks` — za úrovňou max retracementu zo štatistiky.
- **Cieľ**: extenzia `tpExt` × IB za prerazenou hranou (predvolene +0,5; vo videu medián max extenzie +0,59),
  alebo `rr` × stop.
- Obchod s pomerom cieľ / stop pod **`minRR`** (0,5) sa vynechá.
- Pri `closeAtEnd` sa pozícia zavrie na zavretí sviečky o **16:00 NY** (`exitTime`).

Príklad s defaultmi pri longu: vstup 0,25 IB pod IB high, stop 0,8 IB pod IB high (riziko 0,55 IB),
cieľ 0,5 IB nad IB high (zisk 0,75 IB) → RR ≈ 1,36.

## Slovníček
- **IB (Initial Balance)** — rozsah prvej hodiny seansy.
- **Single break / true day** — deň, keď sa prerazí len jedna strana IB.
- **Extenzia** — ako ďaleko za prerazenú hranu cena dôjde, v násobkoch IB.
- **C# jadro** — `ibretnet` (NinjaTrader 8, MetaTrader 5), zhoda s touto predlohou bar po bare.
