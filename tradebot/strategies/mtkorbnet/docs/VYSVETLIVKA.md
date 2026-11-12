# MTK ORB (MGC) — ako funguje

> V jednej vete: na zlate sa vezme rozsah prvých 15 minút New Yorku a ide sa po jeho prieraze, ale len v smere ranného gapu a len keď rozsah nie je nezvyčajne široký.

## Pôvod
Rozbor otvorenia New Yorku 11. 11. 2026 (MNQ, ES, MGC, 1m dáta 2010–2026, ~20 typov vzorcov). Jediný silný opakujúci sa vzorec bol prieraz rozsahu 9:30–9:45 na MGC; samotný prieraz od 2023 slabne, v smere gapu a pri nie širokom rozsahu drží: 73 obch./rok, WR 58 %, PF 1,33, zisk v 15 zo 16 rokov (hrubý test, vstup na úrovni prierazu).

## Ako vznikne obchod (MGC, New York)
1. **Rozsah (OR)** — high a low sviečok 9:30–9:45 NY.
2. **Gap** — otvorenie 9:30 proti zavretiu seansy 9:30–16:00 predošlého dňa. Hore = len longy, dole = len shorty (`gapFilter` 1).
3. **Šírka** — keď je OR širší ako 1,25 × medián posledných 60 dní, v ten deň sa neobchoduje (`maxOrWidthMult`).
4. **Vstup** — prvá sviečka, ktorá zavrie za OR v povolenom smere; market.

## Stop, cieľ, koniec
- **Stop** na druhej strane OR, **cieľ** 1 × riziko (RR 1).
- Bez vstupu po 16:00, otvorená pozícia sa o 16:00 zavrie.

## Slovníček
- **Gap** — rozdiel medzi včerajším zavretím seansy a dnešným otvorením.
- **OR (opening range)** — rozsah prvých minút seansy.
