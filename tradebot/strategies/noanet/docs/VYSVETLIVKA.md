# NOA 1.0 (C# jadro) — ako funguje

> V jednej vete: presne tá istá stratégia ako **NOA 1.0 (Noise Area)**, len jadro je v C#, aby bežala aj naživo v NinjaTraderi a MetaTraderi 5.

Obchody sú sviečku po sviečke zhodné s NOA 1.0 (overuje to test parity bar po bare aj na nastaveniach, ktoré prešli smernicou). Filter trendu a volatility, potvrdenie sviečkou a limitku robí C# jadro samo, takže naživo platia rovnako ako v testoch.

## Ako vznikne obchod (5m graf NQ / MNQ, seansa New York 9:30–16:00)
1. **Pásmo šumu:** pre každú minútu dňa priemer toho, o koľko sa cena v tom čase vzdiali od otvorenia dňa, za posledných 14 dní.
2. **Hranice:** horná = max(open, včerajšie zavretie) × (1 + pásmo), dolná = min(…) × (1 − pásmo).
3. **Kontroly:** rozhoduje sa len každých 30 minút (10:00, 10:30, …). Zavretie nad hornou hranicou = LONG, pod dolnou = SHORT.
4. **Výstup** tiež len na kontrole: long sa zavrie, keď cena klesne pod vyššiu z (horná hranica, VWAP); short zrkadlovo. O 16:00 sa zatvára všetko.

## Stop a cieľ
- **Stop** je len poistka (1 % z ceny) proti prudkému pohybu medzi kontrolami.
- **Cieľ** nemá — víťazné obchody bežia, kým sa trend neotočí pod VWAP, alebo do 16:00.

## Slovníček
- **Pásmo šumu** — bežný pohyb ceny od otvorenia v danom čase dňa; pohyb za ním je skutočný ťah.
- **VWAP** — priemerná cena dňa vážená objemom.
- **C# jadro** — tá istá logika prepísaná do C#, ktorý vedia spustiť NinjaTrader aj MetaTrader 5.
