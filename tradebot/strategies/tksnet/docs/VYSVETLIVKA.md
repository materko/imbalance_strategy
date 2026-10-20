# TKS 1.0 (C# jadro) — ako funguje

> V jednej vete: presne tá istá stratégia ako **TKS 1.0 (NQ Kompas)**, len jadro (Kompas aj pravidlá) je v C#, aby bežala aj naživo v NinjaTraderi a MetaTraderi 5.

Obchody sú sviečku po sviečke zhodné s TKS 1.0 (overuje to test parity bar po bare aj na nastaveniach, ktoré prešli smernicou). Filter trendu a volatility, potvrdenie sviečkou a limitku robí C# jadro samo, takže naživo platia rovnako ako v testoch.


## NQ Kompas
Číslo 0–100 počas seansy New York (9:30–16:00) z toho, čo na 6 rokoch MNQ predpovedalo trend dňa: o koľko je pohyb od otvorenia nad bežným pre túto minútu, kde je cena v nočnom range, či kupujúci alebo predávajúci tlačia (kde sviečky zatvárajú × objem) a koľko času je cena nad VWAP.

## Ako vznikne obchod
1. Kompas zavrie **pod spodnou hranicou** (napr. 35) **3 sviečky po sebe** → **short** market.
2. Zrkadlovo **nad hornou hranicou** (napr. 65) → **long**.
3. Ďalší signál až keď Kompas od hranice odíde; vždy len jedna pozícia.

## Stop, cieľ a koniec dňa
- **Stop** na najbližší swing high (short) / swing low (long) za cenou.
- **Cieľ** = RR × vzdialenosť stopu (zadanie 1:1).
- Pozícia sa drží do stopu alebo cieľa (voliteľne zavrieť o 16:00).

## Slovníček
- **Swing high / low** — lokálny vrchol / dno potvrdené sviečkami na oboch stranách.
- **VWAP** — priemerná cena dňa vážená objemom.
