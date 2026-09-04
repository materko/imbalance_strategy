# Rok na BINANCE BTC/USDT.P (3m) — 2025-09-04 → 2026-09-04

Nastavenia sú presne tie, čo boli v ten deň na TradingView grafe: profil
`btcusdt_3m_binance_tv` plus zapnuté `enableSrTrading` a `enableLqTrading`
(RR 1, Long only, IMB + Pin Bar, Engulfing vypnutý, trailing zapnutý).
Beh je cez celý Freqtrade s `--timeframe-detail 1m`.

Krátke okno Aug 24 – Sep 4 sedí s TradingView na cent
([GOLDEN_binance_2026-08-24.md](GOLDEN_binance_2026-08-24.md)), takže rozdiely
nižšie nie sú chybou portu — sú to náklady, ktoré TradingView nemodeluje.

## Výsledok

| | bez poplatkov (ako Pine) | reálne poplatky, peňaženka 10k |
|---|---|---|
| obchodov | 166 | 166 |
| TP / SL | 89 / 77 | 89 / 77 |
| winrate | 53,6 % | 36,7 % |
| PnL | +1 589 USDT hrubý | **−1 376,8 USDT** |
| ekvivalent na 10k účte | ≈ +15,9 % | **−13,77 %** |
| profit factor | 1,11 | 0,44 |
| max drawdown | — | 14,31 % |
| najdlhšia séria strát | 5 | 10 |

**Sú to tie isté obchody.** Exekúcia je od poplatkov nezávislá — 89 výstupov na TP
a 77 na SL v oboch behoch. Mení sa len to, koľko z nich ostane ziskových.

## Prečo to poplatky prevrátia

Binance berie 0,05 % za stranu, teda 0,10 % na obchod. Priemerný víťaz je
**+0,22 %** z nominálu, priemerný strácajúci −0,23 % — poplatok teda zožerie
takmer polovicu priemerného zisku a 28 z 89 víťazov prevráti do straty.

Za rok: 3,05 M USDT objemu → **1 527 USDT na poplatkoch** proti hrubému zisku
152 USDT pri tejto veľkosti pozície. Funding je zanedbateľný (−3 USDT).

**Break-even poplatok je 0,0050 % za stranu** — desaťkrát menej, než dáva Binance
na najlacnejšom tieri. Ani maker vstup (0,02 %) to nezachráni.

## RR 2,5: väčší edge, stále málo

Ten istý rok, zmenené len `rrRatio` na 2,5 (hodnota, ktorú našiel manuálny
prieskum v TradingView):

| | RR 1 | RR 2,5 |
|---|---|---|
| obchodov | 166 | 158 |
| hrubá winrate | 53,6 % | 35,4 % |
| **hrubý profit factor** | 1,093 | **1,198** |
| hrubý PnL pri 1 BTC/obchod | +1 589 | **+4 282** |
| **break-even poplatok** | 0,0050 %/strana | **0,0151 %/strana** |
| čistý PnL (0,05 %/strana, 10k) | −13,77 % | −10,34 % |
| max drawdown | 14,31 % | 13,11 % |

RR 2,5 **ztrojnásobí edge** a potvrdzuje zistenie z TradingView. Stále je ale
3,3× pod poplatkom, ktorý Binance reálne berie.

## Shorty situáciu zhoršujú

`tradeDirection = Both`, ten istý rok, reálne poplatky:

| | Long only | Both |
|---|---|---|
| obchodov | 166 | 300 (135 long / 165 short) |
| hrubý PnL | +152 | +99 |
| — z toho long | +153 (PF 1,124) | +153 (PF 1,124) |
| — z toho short | — | **−53 (PF 0,961)** |
| čistý PnL | −13,77 % | **−24,31 %** |
| max drawdown | 14,31 % | 24,49 % |

Krátka strana je stratová **už pred poplatkami** (PF 0,961 pri RR 1, 0,909 pri
RR 2,5) a pritom takmer zdvojnásobí objem, teda aj účet za poplatky. Parita so
shortmi je pritom overená — nie je to chyba portu, tá strana proste nemá edge.

## Čo z toho plynie

1. Edge existuje a je merateľný, ale je **rádovo menší než transakčné náklady**.
   Ladenie prahov na tom nič nezmení — treba buď dlhšie držané obchody
   (väčší pohyb na obchod), alebo výrazne lacnejšiu exekúciu.
2. RR je najsilnejšia páka, akú sme zatiaľ videli: 1 → 2,5 zmení break-even
   poplatok 3×. Stojí za to preskúmať aj vyššie RR a dlhší chart TF.
3. Long only mal proti sebe trh — BTC za toto okno klesol o 27,3 %.

## Ako to zopakovať

```bash
IBS_PROFILE=ibs/configs/btcusdt_3m_binance_tv.json .venv/bin/python -m freqtrade backtesting \
  --config platforms/freqtrade/config.binance.json \
  --userdir platforms/freqtrade/user_data --strategy IBSImbalanceStrategy \
  --timeframe-detail 1m --timerange 20250904-20260904
```

Pre porovnanie s TradingView pridaj `--fee 0 --dry-run-wallet 400000` (Pine nemá
`commission_value` a obchoduje 1 BTC bez ohľadu na veľkosť účtu).
