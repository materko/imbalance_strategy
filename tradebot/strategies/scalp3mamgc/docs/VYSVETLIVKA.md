# Scalping 3MA (MGC) — ako funguje

> V jednej vete: tá istá stratégia ako **Scalping 3MA**, len s nastaveniami na zlato (MGC futures).

Profily sú najlepšie z víkendového hľadania na MGC (2.–5. 10. 2026): v zisku všetkých 5 rokov 21/22 – 25/26, aj v roku, ktorý hľadanie nevidelo — WK 159 (RR 0,9; PF 1,23 · 1,32 · 1,33 · 1,32 · 1,30), WK 161 (RR 1,2; 1,44 · 1,39 · 1,34 · 1,21 · 1,26), WK 156 (3m, RR 2,0; 1,33 · 1,42 · 1,21 · 1,28 · 1,14) a WK 169 (RR 1,4; 1,33 · 1,32 · 1,27 · 1,21 · 1,03). Testované **bez poplatkov**; pred živým nasadením preveriť podľa smernice s nákladmi.

Pôvodná stratégia v jednej vete: obchoduje sa len v smere trendu, ktorý ukazujú tri kĺzavé priemery, RSI ho musí potvrdiť a vstupným signálom je fraktál.


Podľa videa Money Knowledge („5 minútová scalping stratégia“).

## Ako vznikne obchod
1. **Trend:** cena nad všetkými tromi priemermi (SMMA 20, 60, 200) = rastúci → len long; pod všetkými = klesajúci → len short. Medzi nimi sa neobchoduje.
2. **RSI** nad 50 pre long, pod 50 pre short.
3. **Fraktál** (Williams) — lokálny vrchol / dno z 5 sviečok — je spúšťač.
4. Vstup market; odporúčaný je jeden obchod denne.

## Stop a cieľ
- Stop 5 pipov (video, EURUSD), alebo v ATR, alebo za fraktál; cieľ RR 2.
- Po zisku 1R sa stop posunie na vstup; obchod sa zavrie, keď RSI prejde cez 50 proti nemu.

## Slovníček
- **SMMA** — vyhladený kĺzavý priemer.
- **RSI** — ukazovateľ sily pohybu (0–100); nad 50 prevažujú kupci.
- **Fraktál** — sviečka s vyšším high (nižším low) ako dve sviečky na každú stranu.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
