# Videá MatFinOg (Matteo Conti, bývalý market maker) — výťah a čo sme z nich overili (MacBook, 21. 10. 2026)

Len zhrnutie pravidiel a naše výsledky, nie prepis (autorské práva).

## 1. „How to IMPROVE FaberVaale Strategy“ — https://www.youtube.com/watch?v=wm6XQFw1GHI
**Stratégia (Fabio Valentini):** range prvých 30 min NY (9:30–10:00); 5m sviečka zavrie nad high → long; SL pod low rangu; TP 1R;
inak výstup 15:00 NY; 1 obchod denne; len long; pôvodne filter delty ≥ 200 na prierazovej sviečke.
**Základ:** štúdia *Market Intraday Momentum* (Gao, Han, Li, Zhou, JFE 2018) — prvá polhodina predpovedá zvyšok dňa (na SPY).
**Jeho výsledky (NQ, 2021–26):** 846 obch, WR 58 %, PF 1,33, zisk/DD 7,2. Delta nepomáha (test dvoch polovičiek: v 1. nič) → von.
Shorty bez náskoku. Edge hlavne po 2019 (Nasdaq trendovejší). **Vylepšenie: rovnaké riziko v $ na obchod** (volatility targeting,
Moreira & Muir; *The Impact of Volatility Targeting*) → zisk/DD 7,2 → 8,7, platí v oboch polovičkách.
**Naše overenie (MNQ, emulátor MC, 1 MNQ, poplatok 1,755e-05, 2021-10 – 2026-09; `skripty/fabio.py`, `fabio_eval.py`):**
| | obch | WR | PF | zisk | DD | zisk/DD |
|---|---|---|---|---|---|---|
| 1. polovica 21/10–24/03 | 393 | 56,0 % | 1,21 | +5 874 $ | 2 208 $ | 2,7 |
| 2. polovica 24/04–26/09 | 399 | 58,1 % | 1,25 | +8 151 $ | 3 663 $ | 2,2 |
| posledný rok 25/26 | 156 | 60,9 % | 1,33 | +4 575 $ | 3 663 $ | 1,2 |
| spolu len long | 792 | 57,1 % | 1,23 | +14 025 $ | 3 663 $ | 3,8 |
| long aj short | 1 239 | 53,8 % | 1,11 | +11 768 $ | 5 402 $ | 2,2 |
Profil pre `orb`: sessionMode ny, 9:30, nyRangeMinutes 30, koniec 15:00, Long only, entryMode close, breakBuffer 0, okno 300 min,
1/deň, min/max range 0 / 10 %, slMode opposite, slBuffer 0, tpMode rr, RR 1, closeAtSessionEnd, 5m graf.
S IBS EZ 1 na jednom účte 90 % obchodov bez zrážky (NOA 1: 95 %).
**Riziko v $ namiesto 1 kontraktu (zisk/DD 1. → 2. polovica):** Fabio ORB 2,7→4,5 a 2,2→3,1 (pomáha); VWAP ORB 1 10,2→10,8 a
4,0→3,0 (nie); NOA 1 7,0→6,5 a 9,0→15,4 (nejednoznačné); TKS 4 9,2→9,5 a 9,6→10,0 (mierne, treba strop kontraktov).
→ Naše živé stratégie nechať na pevnom kontrakte; IBS EZ už počíta z rizika.

## 2. „The Trading Strategy That Made HUNDREDS of MILLIONS“ — https://www.youtube.com/watch?v=rNC90QEgp-Q
Hlavne o jednoduchosti (zložitosť skrýva neznalosť; jasný vstup s 1–2 podmienkami, jednoduchý SL/TP; zložitosť pridávať zámerne;
ten istý systém skúšať na rôznych trhoch; AI na rýchle testovanie mnohých jednoduchých nápadov).
**Turtle (Richard Dennis):** 60m graf, NQ; nad SMA 200 len long, pod len short; vstup pri prierazu high/low posledných 40 sviečok;
výstup len stop 2× ATR; riziko 2 % účtu. Jeho výsledok: WR ~30 %, priem. výhra 4 850 $ vs strata 1 700 $, veľké DD a roky bez pohybu.
**NEtestované** — kandidát na MNQ aj MGC (swing; prop účty často nedovolia držať cez noc / víkend). Kód: `demo_breakout`
(Donchian) + filter SMA 200 + stop 2× ATR.

## 3. „I distilled liquid gold from 9 years of MBO data“ — https://www.youtube.com/watch?v=IeaFAj83Ufg
Výskum (nie hotová stratégia): predpovedá **najväčší jednotlivý obchod minúty** (MBO / Level 3, NQ, 5/2017 – 7/2026, agresor známy)
ďalší pohyb? Meranie: vstup na otvorení ďalšej sviečky, výstup o N min, bez SL/TP, pred nákladmi.
- Sviečka sama (farba, 1 min): +0,41 $/obch — nič. Veľryba ≥ 100 NQ v jej smere, 1 min: +1,88 $/obch (4,6×), WR 49 %.
- **Čas:** náskok rastie ~15 min, plató 13–23 min, vrchol ~19 min, po 30 min preč.
- **Veľkosť:** < 50 lotov nič; **70–190** rastie s veľkosťou; **> 200 zmizne / obráti sa** (bloky, stop kaskády, vyčerpanie).
- **Kontext:** 79 % v RTH; v noci nič. Držanie 15 min: 24 $/obch. Veľryba v **knôte** 34 $ vs v tele 8 $. Funguje pri **vyrovnanej
  knihe**, pri naklonenej nie.
- Finál (> 100 lotov, RTH, vyrovnaná kniha, knôt, 15 min, smer veľryby): 1 587 obch, **53 $/obch, PF 1,24 pred nákladmi**,
  long aj short rovnako. Po nákladoch tesné.
**Pre nás:** potrebuje tick / trades dáta s veľkosťou a stranou (Databento trades/MBO NQ alebo ticky z NinjaTradera) — z 1m ani
z TradingView footprintu to nejde. Náš výsledok „delta za sviečku nič nepridá“ s tým sedí (informácia je v jednom veľkom
príkaze, nie v súčte). Nápad: filter pre IBS / VWAP ORB (vstup len s veľrybou 70–190 NQ v smere za posledné minúty), horizont
15–20 min sedí s našimi obchodmi. Prahy sú pre NQ (100 NQ ≈ 1 000 MNQ). NEtestované.

## 4. „This Market Anomaly Pays While You Sleep (The Fed Proved It)“ — https://www.youtube.com/watch?v=ueVIjmC9glg
**Nočná anomália:** NQ 11 rokov, 1 kontrakt — kúpiť a držať +441 000 $, long len 9:30–16:00 +133 000 $, len noc (16:00→9:30)
+312 000 $ (~70 % výnosu v noci). Štúdia 2008 „Return differences between trading and non-trading hours: like night and day“
(SSRN); NY Fed 2020 „The Overnight Drift“. Príčiny: prémia za nočné riziko; prehnaná reakcia na nočné správy pri nízkej
likvidite (vysoké otvorenie a pokles v 1. hodine seansy — nápad: otočka v 1. hodine); **pozície market makerov** — cez deň
(najmä v červené dni) preberú predaje, cez noc ich držia so zľavou a zbavujú sa ich pri likvidite z Európy (~2:00–4:00 NY) →
posun najsilnejší pri otvorení Európy a **po červenom dni**.
Verzie (NQ 2021–26, 1 kontrakt, po nákladoch):
1. Overnight Range Breakout: range 16:00–17:00 NY, po znovuotvorení zavretie nad range → long, SL low, TP 1R, výstup 4:00 NY:
   521 obch, WR 53 %, PF 1,27, +57 000 $.
2. Každú noc long 18:00 → 4:00 NY: 1 424 obch, +141 000 $, ale 2021–23 spolu len ~7 000 $ (zisk takmer celý 2024–26).
3. **Len po červenom dni (seansa 9:30–16:00 v strate):** 628 obch, WR 58 %, PF 1,39, +137 000 $, 218 $/obch, 6/6 rokov v zisku
   (2021 +23 %, 2022 +10 %, 2023 +11 %, 2024 +2,7 % najhorší — v pokojnom raste málo červených dní).
**Pre nás:** blízko `nocpon` (NOC + PONDELOK, 15:55→3:00 + SMA 100) a záložnej `overnight`; nové = filter „po červenom dni“ a vstup
až 18:00. Obchod 18:00→4:00 je v jednom obchodnom dni CME → neporušuje EOD pravidlo propiek. Pozor na zrážky s IBS EZ 1
(nočná seansa 0:00–3:00 NY).
**Naše overenie (21. 10.; MNQ 1m 2019 – 2026-09, 1 MNQ, poplatok 1,755e-05 + 1 tick sklz na stranu, bez dní rolovania;
`skripty/noc.py`, `noc_eval.py`):**
| verzia | obch | WR | PF | zisk | DD | PF: 19–21/9 · 21/10–24/3 · 24/4–26/9 · posl. rok |
|---|---|---|---|---|---|---|
| A každú noc 18:00→4:00 | 1 819 | 53,3 % | 1,16 | +16 433 $ | 3 907 $ | 1,30 · 0,97 · 1,20 · 1,22 |
| **B len po červenom dni** | 835 | 55,8 % | **1,29** | +14 203 $ | **2 370 $** | **1,51 · 1,09 · 1,30 · 1,36** |
| B' len po zelenom dni | 984 | 51,2 % | 1,04 | +2 231 $ | 6 231 $ | 1,14 · 0,87 · 1,11 · 1,09 |
| C ORB 16–17 h, long | 695 | 53,1 % | 1,21 | +5 653 $ | 2 244 $ | 1,02 · 1,01 · 1,46 · 1,36 |
| D 15:55→3:00 (nocpon bez SMA) | 1 819 | 53,8 % | 1,14 | +16 586 $ | 5 819 $ | 1,27 · 1,09 · 1,11 · 1,18 |
| B + nad SMA 100 | 566 | 56,5 % | 1,30 | +9 558 $ | 2 071 $ | 1,41 · 1,03 · 1,33 · 1,35 |
B po rokoch: 19 +1 243 · 20 +2 389 · 21 +2 790 · 22 +693 · 23 +351 · 24 −23 · 25 +3 630 · 26 (do 9/) +3 129 $ — 7/8 rokov v zisku,
2024 najslabší (ako vo videu). SMA 100 navyše nepridá (menej obchodov, rovnaké PF). S IBS EZ 1 na jednom účte 97 % obchodov
bez zrážky. Obchod 18:00→4:00 je v jednom obchodnom dni CME (EOD 15:59 neporušuje). Kandidát na stratégiu (`nocpon` variant).

## 5. „The strategy that keeps MAKING BILLIONS to INSTITUTIONAL traders: PEAD“ — https://www.youtube.com/watch?v=EP4ptjamPYA
**PEAD (post-earnings announcement drift):** po prekonaní odhadov zisku akcia ďalej rastie týždne, pri sklamaní klesá.
Výskum: Ball & Brown 1968, Bernard & Thomas 1989 (41/48 kvartálov, ~60 dní), Livnat & Mendenhall 2006, prehľad 200+ štúdií 2021.
Príčina: pomalé spracovanie správy (fondy, analytici, retail) + limity arbitráže.
**Stratégia:** prekvapenie EPS vs konsenzus + reakcia ceny v rovnakom smere (súhlasný signál) → long / short na otvorení dňa po
reakcii; výstup po 60 obch. dňoch bez SL/TP; 10 % kapitálu na pozíciu. Dáta zadarmo zo Zacks.com. 20 veľkých US akcií
(rôzne sektory), 2018 – 4/2026, 658 vyhlásení.
| verzia | zisk (účet 100 k$) | max DD | |
|---|---|---|---|
| 1 súhlasný signál L+S | +131 000 $ | 17,4 % | PF 1,99, WR 61 %, ~12 %/rok, Calmar 0,68 |
| 2 bez súhlasu ceny | +251 000 $ | 32,5 % | Calmar 0,69 |
| 3 bez súhlasu, prekvapenie ≥ 5 % | +191 000 $ | 26 % | Calmar 0,67 |
| 4 oba filtre | +82 000 $ | 20 % | Calmar 0,36 — filtre spolu pokazili |
| **5 súhlasný, len long** | **+146 000 $** | 20 % | **PF 2,68, WR 63 %** |
Shorty vždy stratové (po 2010 sa zlé správy dostanú do ceny vopred). Silnejšie na malých / stredných firmách.
**Pre nás:** swing na akciách (portfólio) — do nášho futures jadra ani na prop účty priamo nepatrí. Nápad: pokračovanie NQ po
výsledkoch gigantov (NVDA, AAPL, MSFT…) — špekulatívne. Ponaučenie: filtre testovať aj v kombinácii. NEtestované.
