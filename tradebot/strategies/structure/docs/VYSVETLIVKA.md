# Market Structure BOS / CHoCH — ako funguje

> V jednej vete: stratégia sleduje vrcholy a dná trhu; keď cena zavrie za posledným vrcholom alebo dnom, je to signál pokračovania (BOS) alebo otočky trendu (CHoCH).

## Ako vznikne obchod
1. **Swingy.** Swing vrchol je sviečka, ktorej high je vyššie ako high niekoľkých sviečok vľavo aj vpravo (dno zrkadlovo). Swing sa dá potvrdiť až keď prejdú sviečky vpravo — stratégia ho skôr nepoužije (žiadny pohľad do budúcnosti).
2. **Štruktúra.**
   - **BOS (break of structure)** — v rastúcom trende sviečka **zavrie** nad posledným swing vrcholom → trend pokračuje.
   - **CHoCH (change of character)** — v rastúcom trende sviečka zavrie pod posledným swing dnom → trend sa otáča.
   - Rozhoduje zatvorenie sviečky, nie dotyk knôtom.
3. **Vstup** podľa režimu: obchod v smere BOS, v smere CHoCH, alebo protitrendový **sweep** (cena prejde za swing a vráti sa).

## Stop a cieľ
- Stop za swing (+ rezerva v ATR), cieľ RR.
- Výstup aj na ďalšej štruktúrnej udalosti v smere obchodu alebo po max. počte sviečok.

## Čo môžeš nastaviť
- Koľko sviečok vľavo / vpravo tvorí swing, režim vstupu, RR, typ výstupu, max. dĺžka obchodu.

## Slovníček
- **Swing** — lokálny vrchol alebo dno.
- **BOS / CHoCH** — prieraz štruktúry v smere trendu / proti nemu (otočka).
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe. Prahy v ATR fungujú rovnako na pokojnom aj divokom trhu.
