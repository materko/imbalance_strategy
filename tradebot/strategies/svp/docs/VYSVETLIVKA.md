# Volume Profile POC 1.0 — ako funguje

> V jednej vete: stratégia spočíta, pri akej cene sa v seanse najviac obchodovalo (POC), a obchoduje návrat ceny k tejto úrovni — pod POC predáva, nad POC kupuje.

## Ako vznikne obchod
1. **Profil** — počas New York seansy sa objem každej sviečky rozloží do cenových riadkov. **POC** = riadok s najväčším objemom, **value area** = pásmo s ~70 % objemu.
2. **Úroveň** — POC predošlej seansy, alebo vyvíjajúci sa POC dnešnej.
3. **Strana** — cena je nad / pod POC; zmena strany zavretím je prieraz.
4. **Vstup** pri návrate k POC z tej strany, kde je cena (odraz), alebo retest po prieraze: limitka na POC, alebo po dotyku IBS imbalance / pin bar.
5. Voliteľne **Fibonacci** — POC musí ležať v pásme návratu poslednej nohy.

## Stop a cieľ
- Stop v ATR alebo bodoch, cieľ RR alebo hrana value area.

## Slovníček
- **POC (point of control)** — cena s najväčším objemom v profile.
- **Value area** — pásmo, kde prebehla väčšina (~70 %) obchodov.
- **Imbalance (FVG)** — medzera medzi 1. a 3. sviečkou trojice: cena sa pohla tak rýchlo, že časť ceny „preskočila“.
- **Pin bar** — sviečka s malým telom a dlhým knôtom: cena bola v jednom smere odmietnutá a zavrela späť.
