# MTK RANGE 1.0 (C# jadro) — ako funguje

_C# jadro tej istej stratégie (`va80`) — beží naživo v NinjaTraderi 8 a MetaTraderi 5; signály zhodné s Pythonom bar po bare._

> V jednej vete: keď Nasdaq otvorí mimo včerajšej „férovej“ zóny (value area) a vráti sa do nej, ide sa na jej druhú stranu — klasické pravidlo 80 % z Market Profile.

Prieskum 7. 11. 2026 na MNQ (2021–2026): edge v každom z 5 rokov, potvrdený aj na iných dátach Nasdaqu (NAS100); na S&P 500 a zlate nefunguje.

## Value area
- Zo včerajšej seansy **9:30–16:00 NY** sa spočíta, pri akých cenách sa obchodovalo najviac: **value area** (70 % objemu) s hranami **VAH** a **VAL** a **POC** (cena s najväčším objemom).

## Kedy vstúpi
- Dnešná seansa **otvorí nad VAH** (alebo **pod VAL**) — mimo včerajšej zóny.
- Prvá **30-minútová sviečka**, ktorá **zavrie späť vo value area**, otvorí obchod smerom dovnútra: po otvorení nad VAH short, pod VAL long.
- Najviac jeden obchod za deň, vstup najneskôr do 12:00 NY.

## Stop a cieľ
- **Stop** za extrémom dňa od otvorenia.
- **Cieľ** **opačný okraj** včerajšej value area (predvolene), alebo POC; obchod, ktorého cieľ je bližšie ako pol stopu (RR < 0,5), sa vynechá.
- Voliteľne sa vynechá deň, keď je stop ďalej ako zvolený násobok denného ATR (cena vybehla príliš ďaleko mimo VA).
- O **15:55 NY** sa pozícia zavrie — stratégia je len v rámci dňa.

## Slovníček
- **Value area (VA)** — pásmo cien, kde prebehlo 70 % objemu dňa; trh ho „akceptoval“.
- **POC** — cena s najväčším objemom.
- **Pravidlo 80 %** — keď sa trh vráti do včerajšej VA, často ju prejde celú.
