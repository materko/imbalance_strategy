# 19 B — Fill a sklz na CFD (FTMO, MT5): čo je namerané a čo navrhujem

## Blokéry (čo chýba)
1. **Bid/ask a spread sa nezapisuje, overené.** EA posiela m1 len ako OHLCV (`TradeBotEA.mqh` ~1042, `MqlRates.spread` sa zahodí).
   Fill obsahuje len `price, qty, ft`. Spread sa dá preto len **odvodiť** z buy fillov proti bid sviečke.
2. **Obchodujeme len US100.cash, US500.cash a XAUUSD** (zrkadlo: 18 MT5 inštancií, účty FTMO-Demo a FTMO-Server3).
   **EURUSD** je len stará skúška `ibsnet` s MNQ profilom (0 fillov). **US30 a BTCUSD** nemajú ani inštanciu. Pre tieto
   tri symboly je všetko nižšie **odhad**.
3. Vzorky sú malé. US100 má 90 obchodov a 184 fillov, US500 8 obchodov, XAUUSD 8 obchodov.
   **V okne správ ±5 min nie je ani jeden MT5 fill.** Pri otvorení NY (9:30–9:40) sú 2.
4. Živé ordery nemali ani jeden **stop vstup** (len Limit a Market), takže sklz stop vstupu nie je zmeraný.
5. `DEAL_TIME` má presnosť 1 s, takže oneskorenie po odoslanie sa nedá zmerať pod 1 s. Jeden fill má čas
   posunutý o presne 3 h (10 799 920 ms). To vyzerá na nekonvertovaný čas servera v `ToMs`, treba to dohľadať.
6. Zmluvné parametre FTMO (spread a provízia podľa symbolu) nie sú v repe. Na webe som ich neoveril.

## 1. Merania (skripty `cfd_fill.py`, `cfd_fill_bars.py`, `cfd_tp_touch.py`, výstup `cfd_fill_out.txt`)
- **m1 brokera je bid.** Všetky sell fills (100 zo 100) ležia v rozpätí bid sviečky svojej minúty. Buy fills
  sú nad high v 7 zo 100 prípadov. Dukascopy je tiež bid (docs/DATA.md). Ask preto nemáme v žiadnych dátach.
- **Spread US100 ≈ 1,5 bodu.** Market buy fill v prvých 3 s minúty − bid open: medián 1,45 b (n=25, p75 2,45).
  Kontrola na sell filloch: −0,11 b (n=32). Market vstup proti signálu: long +1,85 b (n=17), short +0,20 b (n=21).
  Rozdiel ≈ 1,65 b. Hranice: 2× bol short SL vyplnený, hoci bid bol 1,64 a 0,38 b pod SL (SL sa spúšťa na ask).
  2× sa bid dostal 0,25 a 0,65 b pod short TP a fill neprišiel.
- **Prechod cez limit.** Buy limit sa vyplnil, až keď bid klesol aspoň 2,00 b pod limit (n=23, medián 7,1).
  Sell limit stačilo 0,31 b (n=24). Na správnej strane (bid pre predaj, ask pre nákup) teda stačí **dotyk**.
  Neprepadol žiadny limit, ktorého sa správna strana dotkla. 3 „dotknuté nevyplnené“ (US100 114 b, US500 8–13 b)
  sú ordery, ktoré u brokera zjavne neboli.
- **Limit a TP u FTMO nie sú pevná cena** (pri spustení idú trhom). Limit vstup: medián −0,18 b long a −0,59 b short
  (lepšie), p90 +0,75 / +0,25 b (horšie). TP: medián −0,75 / −0,48 b (lepšie), p90 +2,2 / +0,7 b.
- **SL US100:** long medián 0,65 b, p75 1,9 b (n=16). Short 1,22 b proti úrovni (n=18, jeden gap 59,5 b).
  US500: SL short 0,2–0,4 b (n=2), long 0 (n=2). XAUUSD: SL long medián 0,20 $ (n=5).
- **XAUUSD spread 0,10–0,40 $.** Buy − open 0,35 $ (n=2), sell −0,09 $ (n=3). Buy limit sa však vyplnil už pri
  prieniku bidu 0,10 $ (n=5), takže spread sa mení podľa hodiny. **US500:** spread ≥ 0,20 b (short SL pod bidom)
  a ≤ 1,20 b (buy limit, n=3).
- **Oneskorenie:** zavretie baru → order 0,11 s (medián, p90 0,25 s, n=43). Fill príde v tej istej sekunde.
- Mimochodom NT (MNQ, demo fill engine, nie burza): SL sklz **medián 2 ticky, p75 5** (n=12). V2 §3 počíta
  +1 tick, takže MNQ podceňuje. Limit a TP vychádzajú presne (sim).

## 2. Literatúra (neoverené pre FTMO)
Vyhľadávanie nenašlo čísla FTMO. Iní brokeri uvádzajú US500 ~0,35 b, zlato 0,17–0,39 $, EURUSD 0,1 pipu raw
alebo ~1 pip štandard, FX províziu ~3,5 $/lot/stranu a indexy bez provízie (gomarkets.com, pepperstone.com,
icmarkets.com). **Pri správach a pri otvorení NY sa spread CFD bežne zväčší 3–10×.** To je skúsenosť, nie meranie.
FTMO má zmluvný spread v MT5 („Specification“), treba ho odpísať.

## 3. Model pre backtest na CFD (graf = bid)
Prechod cez úroveň určujem **podľa strany v bodoch spreadu**, nie v tickoch a nie v % ATR:
- CFD nemá frontu na úrovni, takže „1 tick prechodu“ z futures tu nemá zmysel. Tick 0,01 je aj tak šum.
- Rozdiel medzi bidom a skutočnou cenou plnenia je presne spread (namerané: buy potrebuje ~S, sell 0).
- ATR rastie s volatilitou, ale spread nie, a v správach je to práve naopak.
Pravidlá:
- **Úrovne na strane predaja** (short limit, long TP, long SL) sa spúšťajú, keď bid dosiahne úroveň.
- **Úrovne na strane nákupu** (long limit, short TP, short SL, buy stop) sa spúšťajú, keď bid dosiahne úroveň − S.
- Market buy = bid + S + sklz, market sell = bid − sklz.
**Prepočet po zavedení logu:** S = p75 (ask − bid) v čase vstupov, zvlášť normal / NY open / správy.
Sklz = medián (fill − (bid alebo ask v čase spustenia)). Ak sa SL alebo market posunie o viac ako 1 S, prepočítať kroky 3–11.

## 4. Dopad (odhad)
Dnešné CFD čísla sa počítajú z futures alebo Dukascopy bidu bez ask korekcie. To zvýhodňuje backtest:
- long limity a short TP sa plnia skôr, ako by sa naozaj plnili,
- short SL sa spúšťa neskôr.
- **IBS EZ US100** (limit, RR 0,5, SL 50–93 b): S + sklz ≈ 0,02–0,03 R na obchod. K tomu ubudnú longy, ktoré sa
  limitu len dotkli (zväčša víťazi). **Odhad PF 1,5 → 1,25–1,35.** Pri stratégiách s RR 0,5 na indexe je to najväčšie riziko.
- **VWAP ORB US100** (market, SL 110–200 b): ≈ 2,5 b na obchod = 0,015 R. **Odhad PF −0,05 až −0,08.**

## NÁVRH (bod = 1,0 indexu / 1 $ zlata; EURUSD v pipoch; M = namerané, O = odhad)
| symbol | S spread (normal) | provízia / str. | prechod predaj / nákup | sklz SL a stop vstup | sklz market | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **1,5 b** (M, n=25+57; p75 → 2,0) | 0 (O) | 0 / S (M, n=47) | **1,0 b** (M, n=34, med 0,65–1,2) | 0,5 b (M, n=38) | S×2, sklz 2 b (O, n=2) | S×4, sklz 4 b (O, n=0) |
| US500.cash | 0,6 b (O; M hranice 0,2–1,2) | 0 (O) | 0 / S (M, n=5) | 0,3 b (M, n=4) | 0,3 b (O) | S×2, 1 b (O) | S×4, 2 b (O) |
| XAUUSD | 0,35 $ (M, n=5; rozptyl 0,1–0,4) | zo zmluvy (O) | 0 / S (M, n=7) | 0,25 $ (M, n=6) | 0,15 $ (O, n=4) | S×2, 0,5 $ (O) | S×5, 1,5 $ (O) |
| US30 | 3 b (O, neobchoduje sa) | 0 (O) | 0 / S | 2 b (O) | 1 b (O) | S×2 (O) | S×4 (O) |
| EURUSD | 0,3 pip (O, 0 fillov) | ~0,25 pip (O) | 0 / S | 0,2 pip (O) | 0,1 pip (O) | S×1,5 (O) | S×5, 1 pip (O) |
| BTCUSD | zo zmluvy × 1,5 (O, neobchoduje sa) | zo zmluvy | 0 / S | 0,02 % (O) | 0,02 % (O) | — | S×3 (O) |
Limit a TP: fill **za úroveň** (medián je lepší, p90 o 0,75 b horší). Konzervatívne sa nepočíta zlepšenie.
SL pred TP v jednej minúte ostáva.
