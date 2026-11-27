# 21 C — Kontrola 19_B a 20_A (CFD fill). Prepočítané na `tester/live/mirror.sqlite` (len čítanie), skripty v scratchpade C

## 1. Námietky A: čo platí
- **Duplikáty: pravda, ale US100 málo.** Nezávislé (stratégia, strana, minúta) sú takéto: US100 184 → 178, US500 16 → 12, XAU 16 → 12. Po odstránení
  duplikátov je spread US100 v RTH (buy fill − bid open, ≤ 3 s) **1,40 b (n=20)** a kontrola na predajoch −0,01 b (n=29). Odhad B (1,45) teda drží.
- **p75: A číta §3 zle.** 2,45 je p75 *zašumeného odhadu* (aj kontrola na predajoch má p75 +0,9 b), nie p75 spreadu. Ten sa z týchto dát zmerať nedá.
  2,0 b je teda **voľba** (+0,6 b nad mediánom), nie meranie. Ako voľbu ju prijímam a značím O.
- **4 dotknuté nevyplnené limity: obaja sa mýlia.** A píše, že „stoja výhry“. Overil som, že **cena vo všetkých 4 prešla aj cez SL**: nv:532 low 7697,35
  < SL 7698,65, nv:562 7694,4, SHORT_216 high 7571,05 = SL (na bide, ask je vyššie), LONG_398 prienik 114 b > SL 85,5 b. V backteste sú to 4× −1R,
  živé „nevyplnenie“ teda živému účtu pomohlo. B ich vyradil bez dôkazu, pritom dôkaz je v logu:
  - LONG_398: `10015 invalid price`. Nákupný limit odišiel, keď bid už bol 44 b pod L (`note`, 6. 11. 14:33).
  - US500 3×: event „order zadaný“, potom EXPIRED / „retest nevyplnený“. Bid bol 8–13 b za úrovňou a fill ani chyba nie sú zapísané. **Nevysvetlené.**
    Treba to overiť v histórii terminálu NAS-WIN11 (chýbajúci fill v zrkadle?). Kým sa to nevysvetlí, US500 exekúcia nie je overená.
  - fib:709 (XAU) obaja prehliadli. EA prešlo do `paused` a `deinit` (4. 11. 21:23), takže dotyk o 2 dni neskôr je chyba merania.
- **3h posun: pravda, ale nie „fatálne“.** Sú to 2 obchody a 4 filly, Demo 20. 10. Chyba je známa a opravená: EA bolo nasadené s posunom 0,
  `TradeBotEA.mqh:177`. Po prechode na zimný čas (od 2. 11.) má zrkadlo 146 MT5 fillov a žiadny predaj neleží mimo bid sviečky. Stačí vylúčiť Demo 20. 10.
- **DEAL_TIME_MSC: pravda.** EA berie `DEAL_TIME` (s), `TradeBotEA.mqh:1887`. Exekútor už berie `DEAL_TIME_MSC` (`TradeBotExecutor.mqh:390, 1130`), oprava je triviálna.
- **Dopad na US500: pravda.** SL zo zrkadla: IBS EZ ES medián 14,4 b, NY VA 9,9 b, RR ≈ 0,5. Náklad ≈ 0,9 b = 0,06–0,09 R. Pri WR 75 % je edge ≈ 0,10 R, teda zmizne.
- **MNQ „+2 ticky (M, n=14)“: nepravda.** Vo vzorke sú duplikáty DEMO9584400 a Tradeify. Bez nich je SL sklz **medián 1 tick, p75 5 (n=11)**.
  Medián preto podporuje dnešné +1 z §3. +2 smie ostať len ako konzervatívna voľba (O).

## 2. Čo obaja prehliadli
1. **Ask sa dá zmerať hneď, netreba čakať 8 týždňov.** `SpoolMinutes` zahadzuje `MqlRates.spread` (`TradeBotEA.mqh:1047`). Server FTMO však vydá históriu
   `CopyTicks` (bid/ask) aj `spread` v M1 spätne. Jednorazový skript MQL5 dá p75 spreadu podľa hodiny aj okolo správ už teraz. Dukascopy má aj ask sviečky,
   takže násobky okolo správ a pri otvorení NY sa dajú zmerať na rokoch 2021–26, nie z literatúry.
2. **Limit, ktorý je pri odoslaní už za cenou.** Emulátor (`_entry_fill` / `EntryFill`) ho vyplní na otvorení, teda za lepšiu cenu. MT5 ho odmietne (10015).
   Na bid open to bolo 3 zo 75 limitov US100: 2 sa vyplnili horšie o 0,45–0,75 b, 1 bol odmietnutý. Model musí mať pravidlo: „limit za trhom → neplní sa“.
3. **Fill v2 neexistuje ani pre futures.** V `emulator.py` ani v `McEmulator.cs` nie je spread, sklz ani prechod o 1 tick a prepínač `--fill` nikde nie je.
   Plnenie je dnes na dotyk, pri gape na otvorení. Veta §3 „platí už v ladení“ je preto zatiaľ blokér, nie stav.
4. **Krok 12 stratí silu.** S = 2,0 b je nad mediánom (1,4), takže „namerané ≤ model“ pri spreade prejde vždy. Porovnávať treba medián s mediánom
   a konzervatívne S nechať len na PF.
5. **Dukascopy a FTMO sa neprekrývajú.** Dukascopy NAS100 je 1/2021–4. 9. 2026, US500 2015–31. 8. 2026, XAU 2016–4. 9. 2026. M1 brokera má US100
   20. 10.–27. 11. (~5,5 týždňa), US500 21. 10.–5. 11. (~2 týždne), XAU 21. 10.–27. 11. Zhodu bidu Dukascopy a FTMO nemá kto overiť, preto treba aspoň mesiac prekryvu.

## 3. Implementácia
Je jednoduchá. Do `_entry_fill` / `_exit_fill` a `EntryFill` / `ExitFill` treba pridať posun podľa strany: nákup `low ≤ L − S`, predaj `high ≥ L + r`, SL/market ± sklz.
Prejsť musí parita C# = Python (`test_csharp_parity`). S podľa okna (RTH, otvorenie NY, správy, mimo RTH) potrebuje v oboch enginoch čas a `calendar_us.json`.
Freqtrade to nevie, CFD preto ide len cez emulátor. Backtest má k dispozícii roky na Dukascopy (bid) a krátke m1 brokera.

## FINÁLNA TABUĽKA (graf = bid; M = namerané po odstránení duplikátov, O = voľba alebo odhad)
| symbol | S RTH | S mimo RTH | spúšťač predaj / nákup | sklz SL a stop | market | NY open 9:30–9:40 | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **2,0 b** (O; M medián 1,4, n=20) | S×2 (O) | bid ≥ L+0,25 / bid ≤ L−S | 1,0 b (M med, n=33, p75 1,55) | 0,5 b (M) | S×2, +2 b (O, stres) | S×4, +4 b (O, stres) |
| US500.cash | 0,8 b (O; M hranice 0,2–1,2, n≈3) | S×2 (O) | L+0,05 / L−S | 0,3 b (O; M med 0,21, n=3) | 0,3 b (O) | S×2, +1 b (O) | S×4, +2 b (O) |
| XAUUSD | 0,40 $ (O; M 0,10–0,40) | podľa hodiny (O) | L+0,05 / L−S | 0,25 $ (O; M med 0,15, n=4, max 0,48) | 0,15 $ (O) | S×2, +0,5 $ (O) | S×5, +1,5 $ (O) |
| US30, EURUSD, BTCUSD | ako 19_B (všetko O, neobchodujú sa) | — | 0 / S | O | O | O | O |
| MNQ / MYM | — | — | 1 tick (§3) | **+2 ticky (O; M med 1, p75 5, n=11)** | +2 ticky (O) | — | — |
Doplnky: limit za trhom pri odoslaní sa neplní. Zlepšenie limitu a TP sa nepočíta. Ak minúta zasiahne SL aj TP, platí SL. Prepočet pri odchýlke > 0,5 S.

## VERDIKT: zapísať do smernice — ÁNO, s podmienkami
- Všetky CFD čísla sú O a CFD hypotéza je **najviac 🟡**, kým:
  (a) skript `CopyTicks` / M1 `spread` nenahradí S nameraným p75 podľa okna,
  (b) EA nezapisuje bid/ask a `DEAL_TIME_MSC`,
  (c) sa nevysvetlia 3 nevyplnené limity US500.
- §3 doplniť takto:
  - „spread zo zmluvy × 1,5“ nahradiť „p75 z histórie ticku brokera“,
  - pridať pravidlo „limit za trhom“,
  - pridať, že `--fill v2` treba ešte naprogramovať (dnes neexistuje).
- Krok 12 porovnáva medián s mediánom.
- Stratégie na US500 s SL < 15 b nejdú na demo, kým PF po tomto modeli nebude ≥ 1,15.
