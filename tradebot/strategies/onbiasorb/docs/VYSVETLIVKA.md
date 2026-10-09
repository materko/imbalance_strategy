# Overnight Bias ORB — ako funguje

> V jednej vete: podľa toho, kde je cena pri otvorení vzhľadom na nočný pohyb, sa určí smer dňa a obchoduje sa prerazenie prvej 15-minútovej sviečky v tom smere.

## Ako vznikne obchod (long aj short, 15m graf NQ / MNQ)
1. **Overnight range:** najvyššia a najnižšia cena od polnoci do 8:30 CT (9:30 New York).
2. **Bias dňa:** kde je open o 8:30 v tomto rangu — horná tretina = len long, dolná tretina = len short, stred = v ten deň sa neobchoduje.
3. **Opening range:** prvá 15-minútová sviečka 8:30–8:45 CT.
4. **Signál** (od 9:00 CT): sviečka zavrie nad high opening rangu (long) alebo pod jeho low (short), v smere biasu, a ADX je nad 20.
5. Vstup na otvorení ďalšej sviečky, najviac jeden obchod za deň.

## Stop, cieľ a koniec dňa
- Stop = 30 % priemerného denného pohybu (ATR za 15 seáns), cieľ = 3 × stop.
- O 14:30 CT sa otvorená pozícia zatvorí.

## Pôvod
Doslovný prepis Pine skriptu podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).

## Slovníček
- **Overnight range** — rozpätie ceny v noci pred otvorením burzy; ukazuje, kam sa trh posunul ešte pred hlavnou seansou.
- **Opening range** — rozpätie prvých minút seansy; jeho prerazenie potvrdzuje smer.
- **ADX** — sila trendu (0–100); nad 20 je trh v trende, nie v bočnom pohybe.
- **ATR** — priemerný denný pohyb; stop podľa neho sa prispôsobí tomu, ako veľmi sa trh hýbe.
