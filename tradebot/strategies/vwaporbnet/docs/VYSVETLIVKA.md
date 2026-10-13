# VWAP ORB 1.5 (C# jadro) — ako funguje

> V jednej vete: presne tá istá stratégia ako **VWAP ORB 1.5**, len jadro je v C#, aby bežala aj naživo v NinjaTraderi a MetaTraderi 5.

Obchody sú sviečku po sviečke zhodné s VWAP ORB 1.5 (overuje to test parity bar po bare aj na všetkých nastaveniach, ktoré prešli smernicou). Filter trendu a volatility, potvrdenie sviečkou a limitku robí C# jadro samo, takže naživo platia rovnako ako v testoch.

Jediné, čo C# verzia nemá: **stop posúvaný s VWAP** (`SL na dotyk VWAP`, `TP na cross VWAP`) — beh s ním odmietne.

## Ako vznikne obchod
1. **Opening range** z New York rangu od 9:30 (15:30 nášho času).
2. **Prieraz:** sviečka zavrie nad high rangu (long) / pod low (short).
3. **Potvrdenie VWAP** podľa nastavenia:
   - `break` — aj VWAP je nad high rangu (pod low),
   - `direction` — VWAP smeruje rovnako ako prieraz.
4. Vstup market na zavretí prvej sviečky, kde platí oboje (voliteľne len na samotnej prerazovacej sviečke).

## Stop a cieľ
- Stop na opačnej strane rangu; voliteľne stop na VWAP, ktorý sa s ním posúva.
- Cieľ RR, alebo držať, kým cena neprerazí VWAP proti obchodu, alebo čo príde skôr; voliteľne TP pri prechode VWAP v zisku.

## Čo môžeš nastaviť
- Všetko z ORB (range, seansy, filtre) plus pravidlo VWAP, stop na VWAP, typ výstupu.

## Slovníček
- **Opening range** — rozpätie prvých minút seansy.
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia); ukazuje „férovú“ cenu dňa podľa obchodovaného objemu.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
