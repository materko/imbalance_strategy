# SPX sila 1.0 — ako funguje

> V jednej vete: stratégia meria, ako silno sa po otvorení New Yorku hýbe S&P 500, a keď je pohyb veľký a Nasdaq ide s ním, obchoduje Nasdaq tým istým smerom.

## Ako vznikne obchod
1. Od 9:30 New York sa sleduje pohyb indexu **S&P 500** od otvorenia v %. Prepínačom **„Sila len zo SPX"** (default zapnutý) sa dá vypnúť — potom sa rátajú aj akcie **AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA** (Magnificent 7).
2. **Sila (−10 až +10)** = ako veľký je pohyb v porovnaní s bežným pohybom za posledných 20 dní (+ pri viacerých symboloch či idú rovnakým smerom).
3. **Meranie** od 10. minúty po otvorení (nastaviteľné); podmienky sa musia splniť do 30. minúty. Na 15m grafe sú to sviečky 9:30 a 9:45.
4. **Long**, keď sila ≥ +5 a cena Nasdaqu (MNQ) je zároveň **nad VWAP** od 9:30, **nad EMA** a **nad čiarou sily** (kde by Nasdaq bol, keby sa od 9:30 hýbal ako S&P 500). Short zrkadlovo. Jeden obchod za deň.

## Stop a cieľ
- Stop za otvorením NY (+ 2 body) alebo v bodoch; cieľ = 1,5 × stop.

## Prečo „SPX sila" a nie „Mag7"
- Stratégia vznikla ako „Mag7 + SPX sila". V TradingView skript 1.0 akcie do sily v skutočnosti nepustil (u akcií nezachytil začiatok nového dňa), takže všetky jeho výsledky boli **len zo S&P 500**. Preto sa premenovala a „len SPX" je default.
- Vypnutý prepínač = S&P 500 + 7 akcií (opravený skript Mag7 1.1). Za 10/2023–8/2026 menej obchodov (129 voči 495), od 12/2025 v TradingView aj tu okolo nuly (PF ~1,0).

## Slovníček
- **Magnificent 7** — sedem najväčších technologických firiem.
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia).
- **EMA** — exponenciálny kĺzavý priemer (sleduje trend).
