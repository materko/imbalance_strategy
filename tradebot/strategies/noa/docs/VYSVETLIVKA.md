# NOA 1.0 — Noise Area (Concretum) — ako funguje

> V jednej vete: zistí, aký veľký pohyb od otvorenia je pre danú hodinu „normálny" (šum), a keď ho cena na polhodinovej kontrole prekoná, ide v smere pohybu — kým sa cena nevráti pod VWAP alebo hranicu pásma, najneskôr do 16:00.

## Ako vznikne obchod (MNQ, seansa New York 9:30–16:00)
1. Pre každú minútu seansy sa spočíta priemerný pohyb od otvorenia (|close / open − 1|) za posledných **14 dní** = **pásmo šumu**.
2. Hranice: horná = max(open, včerajšie zavretie) × (1 + pásmo), dolná = min(open, včerajšie zavretie) × (1 − pásmo).
3. **Kontrola o celej a o pol** (10:00, 10:30 … 15:30): zavretie **nad hornou hranicou = long**, **pod dolnou = short**. Vstup market.

## Stop, cieľ a koniec dňa
- **Stop** je výstup na kontrole (pod VWAP / hranicou pásma); u brokera stojí len poistka 1 % z ceny. **Cieľ** nie je — obchod drží trend dňa.
- Rozhoduje sa **len na kontrolách**: long sa zavrie, keď zavretie klesne pod **max(horná hranica, VWAP)**, short zrkadlovo. Medzi kontrolami sa nič nerobí — preto obchod neodstreľuje bežný šum.
- **O 16:00 sa zatvára všetko** (žiadna pozícia cez noc).
- Po výstupe sa na ďalšej kontrole smie vstúpiť znova.
- Pevný stop u brokera je len **poistka** (1 % z ceny) proti prudkému pohybu medzi kontrolami.

## Čo od nej čakať
Nízky win rate (~40 %), ale veľké výhry v trendových dňoch — drží celý pohyb dňa. Iný typ než IBS či VWAP ORB, preto dobrá diverzifikácia.

## Pôvod
Zarattini, Aziz, Barbon (2024), Concretum Research: „Beat the Market — An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)". SPY 2007–2024: +1 985 %, Sharpe 1,33 (po nákladoch). V TradeBote od 16. 10. 2026 (záloha `noisearea` mala chybu: stop u brokera namiesto výstupu len na kontrolách).

## Slovníček
- **Pásmo šumu** — o koľko sa cena v danú hodinu bežne pohne od otvorenia; únik za neho = nezvyčajný pohyb, ktorý zvykne pokračovať.
- **VWAP** — priemerná cena dňa vážená objemom (od 9:30); nad ním majú prevahu kupujúci.
- **Kontrola** — moment (každú polhodinu), keď stratégia rozhoduje o vstupe aj výstupe.
