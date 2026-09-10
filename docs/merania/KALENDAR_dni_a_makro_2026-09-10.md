# Kalendár: deň v mesiaci a makro udalosti — 2026-09-10

Do analytiky pribudli kalendárne vlastnosti (deň v mesiaci, kalendárny mesiac, deň
rozhodnutia Fedu / inflácie / zamestnanosti, sviatky búrz v USA). Toto meranie ich hneď
overuje — sú to totiž presne tie vlastnosti, ktoré na zliatej vzorke vyzerajú
najpresvedčivejšie a najčastejšie neplatia.

## Čo hovorí zliata vzorka

1022 obchodov, konfigurácia A na desiatich trhoch:

```
Deň v mesiaci               obch.  break-even
do 9                          289     +0.1461
9 – 16                        246     +0.0726
16 – 23                       253     +0.0602
nad 23                        234     -0.0313

Makro udalosť v ten deň     obch.  break-even
CPI                            48     -0.0763
žiadna                        894     +0.0666
NFP                            51     +0.1104
FOMC                           28     +0.2585
```

Prvá tabuľka je presne to, čo sa o kalendári hovorieva („začiatok mesiaca je iný než
koniec") — rozdiel 0,177 percentuálneho bodu medzi prvou a poslednou štvrtinou.

## Čo hovorí rozklad na bunky

Každá bunka je jeden trh × jedno okno; do súčtu ide len tá, ktorá má obe skupiny aspoň
päť obchodov. Znamienkový test berie každú bunku ako jedno pozorovanie.

```
prvých 10 dní v mesiaci vs zvyšok
    22/36 buniek kladných (61 %), medián +0,0556, p = 0,12

      BTC/USD        3/4   +0.1998      NAS100/USD     2/5   -0.0345
      BTC/USDT:USDT  3/5   +0.0415      NGAS/USD       3/4   +0.2488
      DJ30/USD       1/1   +0.1658      WTI/USD        2/3   +0.1539
      ETH/USD        3/5   +0.0117      XAU/USD        1/2   +0.1421
      ETH/USDT:USDT  3/5   +0.1567      JP225/JPY      1/2   -0.0074
```

**Nepotvrdené.** 22 z 36 je pri hode mincou celkom bežné (p = 0,12) a ani jeden trh nemá
čisté skóre. Zliaty rozdiel 0,177 bodu je z veľkej časti tým, že sa do jednej hromady dali
rôzne trhy a roky.

Makro udalosti sa overiť **nedali**: na bunku pripadá tak málo obchodov v deň výpisu, že
podmienku „aspoň päť v oboch skupinách" splnilo sedem buniek z päťdesiatich (3/7, p = 0,77).
A rozdelenie „pred vyhlásením / po ňom" neprešlo ani raz — stratégia obchoduje NY seansu,
ktorá začína po 08:30, takže pred výpisom nevstupuje takmer nikdy.

## Záver

Kalendárne vlastnosti sú v analytike užitočné, ale zatiaľ **ako otázka, nie ako odpoveď**.
Konkrétne:

- **Deň v mesiaci neplatí** na tejto vzorke. Ak sa k nemu vracať, tak s desaťkrát väčším
  počtom obchodov, nie s jemnejším delením.
- **Makro dni sa z takejto vzorky vyhodnotiť nedajú.** Stratégia s ~30 obchodmi za rok má
  za rok tri dni s CPI; na porovnanie treba stratégiu, ktorá obchoduje denne, alebo
  mnohonásobne dlhšiu históriu.
- Čo z toho ostáva použiteľné hneď: **vidieť, že v ten deň bola udalosť**. To je pri
  čítaní jednotlivých obchodov cenné aj bez štatistiky.

Je to tá istá lekcia ako pri režimových filtroch
([REZIM_filtre_btcusdt_2026-09-10.md](REZIM_filtre_btcusdt_2026-09-10.md)): zliate číslo
presvedčí, rozklad na bunky rozhodne.
