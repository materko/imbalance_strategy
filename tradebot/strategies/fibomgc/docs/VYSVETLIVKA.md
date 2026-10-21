# Fibo 1.0 (MGC) — ako funguje

> V jednej vete: tá istá stratégia ako **Fibo 1.0**, len s nastaveniami na zlato (MGC futures).

Profily sú najlepšie z víkendového hľadania na MGC (2.–5. 10. 2026): v zisku všetkých 5 rokov 21/22 – 25/26, aj v roku, ktorý hľadanie nevidelo — WK 155 (RR 0,9; PF po rokoch 25/26 1,50 · 24/25 1,21 · 23/24 1,77 · 22/23 1,30 · 21/22 1,21) a WK 166 (RR 1,0; 1,55 · 1,30 · 1,46 · 1,21 · 1,09). Testované **bez poplatkov**; pred živým nasadením preveriť podľa smernice s nákladmi.

Pôvodná stratégia v jednej vete: po silnom pohybe (noha) sa cena často vracia k Fibonacciho úrovniam (38,2 / 50 / 61,8 / 78,6 %); tam stratégia čaká na potvrdzovaciu sviečku a ide v smere pôvodného pohybu.


Podľa videa The Trading Geek; je to základ pre väčšiu stratégiu.

## Ako vznikne obchod
1. **Noha** medzi swing dnom a vrcholom na vlastnom TF, dostatočne dlhá (ATR); voliteľne musí prekonať predošlý vrchol (jasný trend).
2. **Návrat:** cena sa vracia; setup padá, keď prejde začiatok nohy alebo pokračuje bez vstupu.
3. **Vstup**, keď je návrat v pásme medzi zapnutými úrovňami (alebo pri niektorej z nich) a príde IBS imbalance alebo pin bar v smere nohy.

## Stop a cieľ
- Stop za začiatok nohy alebo za extrém návratu, cieľ extenzia nohy (−27 %) alebo RR.

## Slovníček
- **Fibonacciho úrovne** — percentá návratu pohybu (0 % = koniec nohy, 100 % = začiatok).
- **Extenzia** — cieľ za koncom nohy (napr. −27 % = o 27 % dĺžky nohy ďalej).
- **Imbalance (FVG)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena bola v jednom smere odmietnutá a zavrela späť.
