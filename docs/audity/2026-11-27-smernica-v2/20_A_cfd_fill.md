# 20 A — Kritika 19_B (CFD fill): prepočítané na `tester/live/mirror.sqlite`, skripty B + vlastné kontroly (len čítanie)

## 1. Overenie meraní
- **m1 = bid: platí, ale dôkaz B je slabý.** „100/100 sell fillov v rozpätí sviečky“ by prešlo aj pre mid (rozpätie minúty ≫ ½ spreadu).
  Skutočný dôkaz je asymetria: buy − bid open +1,45 b, sell −0,11 b, buy nad high 7×, sell mimo 0×. Prijímam (M).
- **n je nafúknuté duplikátmi.** Demo aj Server3 bežia tie isté stratégie. V detaile sú rovnaké obchody 2× (fib:374, fib:988, nv:806)
  a US100 má 7 minút so vstupom na oboch účtoch. XAU SL_L „n=5“ = 3 nezávislé, US500 SL „n=4“ ≈ 3. Pri n ≤ 4 nie je p75 ani rozptyl.
  US500/XAU čísla sú **hranice, nie parametre** (US500 S ∈ 0,2–1,2 b, XAU S ∈ 0,10–0,40 $).
- **S US100 = 1,45 b je šum ±0,5 b.** Kontrola na sell filloch má IQR −1,0…+1,4 b, SE mediánu ≈ 0,45 b (95 % ~0,6–2,4).
  Dva short SL dokazujú S ≥ 1,64 b práve v chvíľach plnenia stopov. **§3 V2 káže p75 → 2,45 b; B dal medián proti vlastnej smernici.**
- **Hranica prechodu nie je zmeraná, len nevyvrátená.** Buy limity: nevyplnené max −3,75 b, vyplnené min +2,40 b, medzi nimi
  **0 pozorovaní** — teda práve v zóne [0, S], o ktorej pravidlo „S“ hovorí. Sell: nevyplnené max −0,78, vyplnené min +0,31 — „dotyk stačí“
  stojí na jednom bode.
- **Výber: B vyhodil nepohodlné prípady.** 4 limity dotknuté hlboko a nevyplnené (US100 114 b; US500 SHORT_216 8,45 b „EXPIRED“,
  nv:532 a nv:562 13 b „retest nevyplnený“) označil „u brokera zjavne neboli“ bez dôkazu. Na US500 sú to 3 zo 7 dotknutých limitov.
  Je to exekučná chyba (order neodišiel, expirácia), ktorú backtest nevidí a stojí výhry. Treba ju dohľadať v logu EA, nie odfiltrovať.
- **3h posun nie je „jeden fill“:** 2 obchody, 4 filly (tks:21157, noa:9822, 20. 10., účet Demo), ft aj bt v čase servera (EEST +3 h).
  Do porovnania so sviečkou nevošli (bar = None), ale do sklzu voči úrovni áno a okno dostali zlé. Okolo DST (25. 10. EU, 1. 11. US)
  hrozí posun 1–3 h. Pre krok 12 (čas ±1 sviečka) je to fatálne. „Presnosť 1 s“ je chyba EA: MT5 má `DEAL_TIME_MSC`.
- **59,5 b short SL (tks:22395)** je gap (open minúty 53 b nad SL). Sklz sa meria voči úrovni, takže gapy sa miešajú so sklzom.
  Správne je merať voči min(stop, prvý tik) ako v §3. Medián to unesie, p75/p90 nie.
- **NY open n=2, správy n=0:** S×2/×4/×5 sú literatúra (O). Smú slúžiť len ako stres, nie ako kalibrácia. SPRÁVY XAU vstupuje
  9:40, 10:15, 11:15 a 15:55 ET, teda **mimo ±5 min**. Okno ±5 min ju vôbec nepostihuje; rozhoduje spread 5–15 min po správe, nezmeraný.
- **Chýba noc / mimo RTH.** Spread US100 mimo 9:30–16:00 je u CFD väčší. B má jediné „normal“ a XAU hodinovú zmenu (0,10 vs 0,35 $) len poznamenal.

## 2. Je „0 / S“ dosť konzervatívne?
Smer je správny (graf = bid), ale S nie je konštanta: v ťahu, keď sa plnia SL a limity, je spread najširší. Preto:
nákup `bid ≤ L − S_p75(okno)`, ask = bid + S_p75 podľa okna (RTH / NY open 10 min / ±5 min správy / mimo RTH). Na predaj malá rezerva
**+0,25 b US100 / +0,05 b US500 / +0,05 $ XAU**, lebo „dotyk“ má 1 pozorovanie. Tick 0,01 ako rezerva nemá zmysel. Zlepšenie limitu/TP nepočítať (súhlas s B).

## 3. Zapadnutie do V2
- **MNQ:** NT SL sklz medián 2 ticky (n=14, short 3,5 pri n=8). Je to sim engine, takže je to **dolná** hranica. §3 „+1 tick“ → **+2 ticky** na stop/market
  MNQ (a MYM, O). Náklad 1,75 ticku zo 16_C/17_C ostáva. Limit/TP v sim sedí presne, o fronte to nič nehovorí, preto 1 tick prechodu ostáva.
- **CFD je ~2× drahší ako MNQ:** US100 ~2,5 b na kolo vs MNQ ~1–1,4 b. Ladenie na futures/Dukascopy s nákladom MNQ sa nesmie prenášať na FTMO bez CFD modelu.
- **Krok 12 je dnes nesplniteľný.** „Sklz a spread ≤ model (medián)“ nemá z čoho počítať, lebo EA zahadzuje bid/ask. Blokér: MqlTick bid/ask pri
  odoslaní aj fille, `DEAL_TIME_MSC`, oprava `ToMs`. Dovtedy CFD hypotéza najviac 🟡. Prah prepočtu „> 1 S“ zmeniť na **> 0,5 S alebo > 0,01 R**:
  pri US500 SL 11 b je 1 S = 0,05 R, teda celý edge.

## 4. Dopad na živé (SL zo zrkadla, náklad na kolo ≈ S + sklz × podiel strát)
IBS EZ US100 (limit, SL med 67 b, p25 52) 0,03–0,05 R → PF 1,5 → **1,30–1,38**, plus stratené dotyky (~3–6 % longov, väčšinou výhry).
**B 1,25–1,35 je realistické.** NOA (limit, 89 b) ~0,025 R → −0,05 až −0,10 PF. VWAP ORB (market, SL 217–699 b, n=5) ≤ 0,012 R → −0,02 až −0,04.
B (SL 110–200) je tu prísnejší, ok. **B vynechal najhoršie:** US500 IBS EZ ES (SL 15 b) ~0,06 R a NY VA (11 b) ~0,08 R. Pri RR ≤ 1 to zjedá väčšinu edge.
XAU Fibo (16 $, p25 7 $) 0,04–0,09 R. SPRÁVY XAU (market, 32 $) ~0,02 R pri normálnom spreade, n=4, rozhoduje nezmeraný spread po správe.

## DOHODA (M = namerané, O = odhad; bod = 1,0 indexu / 1 $ zlata)
| symbol | S RTH | S mimo RTH | prechod predaj / nákup | sklz SL a stop | market | NY open | správy ±5 min |
|---|---|---|---|---|---|---|---|
| US100.cash | **2,0 b** (O z M: med 1,45, p75 2,45, ≥1,64 pri SL) | S×2 (O) | +0,25 b (O) / bid ≤ L−S (M smer) | 1,0 b (M, ~30 nezáv., bez gapov) | 0,5 b (M) | S×2, 2 b (O, n=2) | S×4, 4 b (O, n=0) |
| US500.cash | **0,8 b** (O; M hranice 0,2–1,2, n≈3) | S×2 (O) | +0,05 / L−S | 0,3 b (O, n≈3) | 0,3 b (O) | S×2, 1 b (O) | S×4, 2 b (O) |
| XAUUSD | **0,40 $** (O; M 0,10–0,40, n≈5) | podľa hodiny (O) | +0,05 $ / L−S | 0,25 $ (O, n=3) | 0,15 $ (O) | S×2, 0,5 $ (O) | S×5, 1,5 $ (O) |
| US30, EURUSD, BTCUSD | ako B (všetko O) | — | 0 / S | ako B (O) | ako B (O) | ako B (O) | ako B (O) |
| MNQ (NT) | — | — | 1 tick (§3) | **+2 ticky** (M sim, n=14) | +2 ticky (O) | — | — |
Podmienky: CFD hypotéza najviac 🟡, kým EA neloguje bid/ask a ms čas. 4 dotknuté nevyplnené limity sa vysvetlia, nie vyradia. Prepočet pri odchýlke > 0,5 S.
