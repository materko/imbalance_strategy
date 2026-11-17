# TKS 1.0 6E (C# jadro) — ako funguje

_Variant na 6E s jadrom v C# (NinjaTrader 8, MT5): logika a parametre sú tie isté ako v `tks` (MNQ). Kompas je pomerový (únik zo šumu v násobkoch bežného pohybu, poloha v nočnom range, tlak, čas nad VWAP) a škála tlaku vychádza na 6E ako na MNQ, takže kód sa nemení. Euro žije hlavne v Londýne, preto Kompas na 6E počíta seansu Londýn 3:00–11:30 NY (9:00–17:30 SK; `sessOpenMin` 180, `sessCloseMin` 690) a „noc“ je Ázia 18:00–3:00; minúty okna vstupov sa rátajú od 3:00. Nastavenia z MNQ sú len východisko — vlastné hľadá ladenie a smernica na 6E._

> V jednej vete: keď NQ Kompas (trend dňa na Nasdaqu) zostane tri sviečky po sebe pod spodnou hranicou, ide sa short, nad hornou long — stop za najbližší swing, cieľ v pomere k riziku.

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
