# Čo sa dá ešte vyťažiť: RR a timeframe (2026-09-04)

Východisko: RR 2,5, Long only, všetky tri entry modely, S/R + likvidita, **bez
trailingu**, rok 2025-09-04 → 2026-09-04. Všetko bez poplatkov a s 1 BTC na obchod,
aby boli čísla porovnateľné s TradingView.

Kľúčové číslo je **break-even poplatok** — koľko smie brať burza za stranu, aby
stratégia vyšla na nulu. Binance berie 0,05 %.

## RR pomer

| RR | obchodov | WR | **PF** | hrubý PnL | na 10k | **break-even** | držanie |
|---|---|---|---|---|---|---|---|
| 1,5 | 183 | 45,9 % | 1,313 | +5 880 | +58,7 % | 0,0181 % | 0:36 |
| 2,0 | 181 | 38,7 % | 1,234 | +4 928 | +49,1 % | 0,0153 % | 0:46 |
| 2,5 | 179 | 36,3 % | 1,360 | +7 572 | +75,5 % | 0,0237 % | 0:54 |
| 3,0 | 178 | 32,0 % | 1,300 | +6 590 | +66,1 % | 0,0209 % | 1:03 |
| 3,5 | 177 | 31,1 % | 1,449 | +9 835 | +98,8 % | 0,0314 % | 1:07 |
| 4,0 | 177 | 29,4 % | 1,433 | +9 651 | +96,9 % | 0,0308 % | 1:12 |
| **5,0** | 176 | 27,8 % | **1,515** | **+11 691** | **+117,4 %** | **0,0375 %** | 1:20 |
| 6,0 | 176 | 25,6 % | 1,472 | +10 984 | +110,3 % | 0,0353 % | 1:28 |
| 7,0 | 175 | 25,1 % | 1,482 | +11 124 | +111,7 % | 0,0359 % | 1:37 |
| 8,0 | 172 | 25,0 % | 1,460 | +10 520 | +105,3 % | 0,0345 % | 1:43 |
| 10,0 | 172 | 23,8 % | 1,482 | +11 138 | +111,5 % | 0,0365 % | 1:49 |

Krivka stúpa do RR 5 a potom sa vyrovná. Oproti pôvodnému RR 1 (break-even
0,0050 %) je to **7,5× viac** — ale stále 1,33× pod tým, čo berie Binance.

### Ten zisk už nerobí take profit

Rozloženie výstupov ukazuje, čo sa v skutočnosti deje:

| | RR 2,5 | RR 3,5 | RR 5,0 |
|---|---|---|---|
| TP | 55 (+24 591) | 41 (+25 513) | 31 (+23 019) |
| **koniec seansy** | 12 (+3 756) | 16 (+5 930) | **20 (+11 063)** |
| SL | 112 (−20 843) | 120 (−21 698) | 125 (−22 485) |

Pri RR 5 sa TP a SL takmer vyrušia (+23 019 proti −22 485) a **celý čistý zisk
prichádza z obchodov zavretých na konci seansy** — tých je 20 a 18 z nich je
ziskových (90 %).

To nie je zásluha RR pomeru. Vysoké RR len odsunie TP tak ďaleko, že sa naň
nedosiahne, a obchod sa drží do konca seansy. Skutočné zistenie znie:
**obchod, ktorý prežije do konca seansy, je s 90 % pravdepodobnosťou ziskový.**
To je samostatná hypotéza, ktorá si zaslúži vlastný test, nie parameter na ladenie.

## Vyšší timeframe grafu

| graf | detekčný TF | obchodov | WR | PF | break-even |
|---|---|---|---|---|---|
| **3m** | 5m | 179 | 36,3 % | **1,360** | **0,0237 %** |
| 5m | 15m | 79 | 34,2 % | 1,106 | 0,0097 % |
| 15m | 30m | 26 | 46,2 % | **0,959** | −0,0054 % |

**Slepá ulička.** Na 15m grafe je edge už záporný a obchodov je 26 za rok.

Hlavný dôvod je, že `*MaxBars` limity sú v **baroch**: `state1MaxBars 10 +
state2MaxBars 15 + state3MaxBars 1 + state4MaxBars 10 + state5MaxBars 10` je na 3m
grafe 138 minút, ale na 15m 690 minút — teda 11,5 hodiny, čo je viac než ktorákoľvek
obchodná seansa. Väčšina zón sa tak do vstupu nedostane.

Zároveň prahy v bodoch (`minImbSizePoints 2,5`, `pbMinRangePoints 2`) neboli
preškálované, takže na 15m baroch prejde filtrom skoro všetko. Čistý test vyššieho
timeframu by vyžadoval preškálovať oboje — ale pri 26 obchodoch za rok to nemá zmysel
riešiť.

## Záver

1. **RR 5 je vrchol** in-sample, ale zisk už nerobí take profit — robí ho držanie
   do konca seansy.
2. **Vyšší timeframe je slepá ulička**, a to hlavne kvôli bar-based limitom.
3. Ani najlepšia konfigurácia nedosiahne na poplatky Binance: 0,0375 % proti 0,05 %.
## Out-of-sample: prvýkrát to obstálo

RR 5 pustené na roky, na ktorých sa nič neladilo:

| okno | obchodov | WR | **hrubý PF** | hrubý PnL | na 10k | break-even |
|---|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 209 | 21,5 % | **1,322** | +6 257 | +138,5 % | 0,0373 % |
| 2022-10 → 2023-10 | 248 | 25,0 % | **1,060** | +820 | +13,2 % | 0,0030 % |
| 2023-10 → 2024-10 | 212 | 21,2 % | **1,022** | +489 | +7,1 % | 0,0019 % |
| 2024-09 → 2025-09 | 181 | 21,5 % | **1,266** | +7 334 | +68,0 % | 0,0212 % |
| **2025-09 → 2026-09** (ladené) | 176 | 27,8 % | **1,515** | +11 691 | +117,4 % | 0,0375 % |

**Všetkých päť rokov je hrubo ziskových.** To je zásadný rozdiel oproti profilu
z hyperoptu ([HYPEROPT_btcusdt_2026-09-04.md](HYPEROPT_btcusdt_2026-09-04.md)), kde
boli **všetky štyri** out-of-sample roky stratové (−11 % až −65 %).

Rozdiel je v tom, čo sa menilo. Hyperopt ladil desať prahov v jednotke `atr` na
~150 obchodoch za rok — to je učebnicové pretrénovanie. Tu sa menil **jeden**
parameter, a to taký, ktorý mení štruktúru obchodu (ako dlho sa drží), nie
citlivosť filtra. Také zistenia prežívajú naprieč rokmi.

Edge je teda reálny — ale malý a nestabilný: priemerný break-even poplatok cez štyri
out-of-sample roky je **0,0159 %**, teda stále **3,2× pod** tým, čo berie Binance.
Dva z tých rokov (2022-23 a 2023-24) sú prakticky na nule.

S reálnymi poplatkami a peňaženkou 10 000 USDT dá RR 5 za posledný rok
**−5,72 %** (PF 0,86, DD 11,10 %) — najlepší čistý výsledok zo všetkého, čo sme
merali, ale stále v mínuse.

## Záver

1. **RR 5 je vrchol** in-sample, ale zisk už nerobí take profit — robí ho držanie
   do konca seansy.
2. **Vyšší timeframe je slepá ulička**, a to hlavne kvôli bar-based limitom.
3. **Edge je reálny a prežil out-of-sample** — päť z piatich rokov hrubo ziskových.
4. Ani tak nedosiahne na poplatky Binance: 0,0159 % priemerne proti 0,05 %.
5. Najsľubnejšia stopa nie je ďalší parameter, ale hypotéza z rozloženia výstupov:
   **obchod, ktorý sa dožije konca seansy, je s 90 % pravdepodobnosťou ziskový.**
   Ak to platí aj na iných rokoch, patrí to do vstupnej logiky, nie do RR pomeru.
