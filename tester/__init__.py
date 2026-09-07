"""TradeBot Tester — podporné nástroje okolo produktu `tradebot`.

Dáta (sťahovanie z búrz, prevod surových exportov, archív), porovnávacie testy
(`compare/`: Pine ↔ port, MultiCharts ↔ emulátor ↔ Freqtrade), reporty a webová
aplikácia pre testerov. Závislosť ide **jedným smerom**: tester importuje
`tradebot`, produkt o testeri nevie.

Balík sa neinštaluje — spúšťa sa z koreňa repozitára (`python -m tester.webapp`),
aby sa meno `tester` nedostalo do globálneho Pythonu, kde beží MultiCharts.
"""
