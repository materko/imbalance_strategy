# Mag7 + SPX sila 1.1 — ako funguje

> V jednej vete: Nasdaq ťahajú najväčšie firmy (Magnificent 7); stratégia meria, ako silno a jednotne sa po otvorení New Yorku hýbu, a keď je sila veľká, obchoduje Nasdaq tým istým smerom.

## Ako vznikne obchod
1. Od 9:30 New York sa pre **AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA** a index **S&P 500** sleduje pohyb od otvorenia v %.
2. **Sila (−10 až +10)** = ako veľký je pohyb v porovnaní s bežným pohybom za posledných 20 dní + či idú všetky symboly rovnakým smerom.
3. **Meranie** od 10. minúty po otvorení (nastaviteľné); podmienky sa musia splniť do 30. minúty. Na 15m grafe sú to sviečky 9:30 a 9:45.
4. **Long**, keď sila ≥ +5 a cena Nasdaqu (MNQ) je zároveň **nad VWAP** od 9:30, **nad EMA** a **nad čiarou MAG7** (kde by Nasdaq bol, keby sa hýbal ako priemer Mag7). Short zrkadlovo. Jeden obchod za deň.

## Stop a cieľ
- Stop za otvorením NY (+ 2 body) alebo v bodoch; cieľ = 1,5 × stop.

## Verzie
- **1.1** pridala **váhu akcií**: 1 = sila zo všetkých 8 symbolov (pôvodne 1.0); 0 = sila len zo S&P 500 — tak to počíta TradingView, keď mu akcie vypadnú.

## Slovníček
- **Magnificent 7** — sedem najväčších technologických firiem.
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia).
- **EMA** — exponenciálny kĺzavý priemer (sleduje trend).
