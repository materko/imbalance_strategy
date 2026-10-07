# ORBNet Opening Range Breakout (C# jadro) — ako funguje

> V jednej vete: presne tá istá stratégia ako **ORB**, len jadro je v C# pre NinjaTrader a MetaTrader 5.

Obchody sú sviečku po sviečke zhodné s ORB (overuje to test parity).

## Ako vznikne obchod
1. **Opening range.** Prvých N minút po otvorení seansy (napr. 15 min od 9:30 New York) tvorí range — jeho najvyššia a najnižšia cena.
2. **Filtre.** Range nesmie byť príliš úzky ani široký.
3. **Prieraz.** V obchodnom okne sviečka **zavrie** nad high rangu (long) alebo pod low (short), voliteľne o rezervu.
4. **Vstup** hneď na zavretí, alebo až po návrate k prerazenej hranici (retest).

## Stop a cieľ
- Stop na opačnej strane rangu, v strede rangu alebo v ATR; cieľ RR alebo násobok rangu.
- Na konci seansy sa pozícia zatvorí.

## Čo môžeš nastaviť
- Seansy (New York, Londýn — každá má vlastný range), dĺžku rangu, filtre šírky, typ vstupu, stop, cieľ, max. obchodov za deň.
- **EMA** ako voliteľná vrstva: filter smeru prierazu, vynechanie dňa, výstup pri návrate cez priemer.

## Slovníček
- **Opening range** — rozpätie prvých N minút seansy.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
