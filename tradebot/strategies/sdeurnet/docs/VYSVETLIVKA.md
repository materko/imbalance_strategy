# SD ZÓNY EURUSD (C# jadro) — ako funguje

> V jednej vete: tá istá stratégia ako **SD ZÓNY EURUSD 1.0**, len s jadrom v C#, aby bežala v NinjaTraderi a MetaTraderi 5 (6E / M6E).

Signály sú bar po bare zhodné s Python predlohou (`tester/tests/test_csharp_parity_6e.py`). Riziko na obchod 500 $.

## Ako vznikne zóna
1. **Báza** — 1 až 4 hodinové sviečky na lokálnom vrchole (supply) alebo dne (demand).
2. **Odchod** — aspoň 1 ATR do 8 hodín bez prerazenia bázy; zóna platí až potom.
3. **Kvalita** — len zóny z noci (18:00–2:00 New York).

## Ako vznikne obchod
- V Londýne (2:00–11:00 NY) limitka na hrane najbližšej nedotknutej zóny, len pri prvom návrate.
- Stop za zónou + 0,25 ATR + 1 tick, cieľ 1,5 R, najdlhšie 48 h.

## Slovníček
- **Supply / demand zóna** — miesto prudkého odchodu ceny nadol / nahor.
- **ATR** — priemerný rozsah sviečky.
