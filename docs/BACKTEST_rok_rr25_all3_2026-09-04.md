# Rok BTCUSDT.P (3m) — RR 2,5, Long only, všetky tri entry modely

Okno 2025-09-04 → 2026-09-04. Nastavenia zhodné s TradingView grafom: `rrRatio 2,5`,
`Long only`, IMB + Pin Bar + Engulfing, S/R aj likviditné obchodovanie zapnuté,
trailing zapnutý (aktivácia 1R, odstup 0,5R).

## Najprv bolo treba doimplementovať trailing stop

Pri všetkých predchádzajúcich meraniach bol `rrRatio = 1` — a **vtedy sa trailing
nikdy neprejaví**: aktivuje sa presne tam, kde už je TP, takže obchod skončí skôr.
Port ho preto síce vypočítal (`TrailingPlan`), ale nikto ho neaplikoval a nikomu to
nechýbalo. Pri RR 2,5 je TP ďaleko a trailing rozhoduje o **84 zo 184 výstupov**.

Bez neho dal port na overovacom okne 5 obchodov a +1 694 USDT tam, kde TradingView
ukázal 6 obchodov a +189. Po doimplementovaní sedí všetkých šesť.

### Poradie pohybu vnútri sviečky nie je detail

Broker emulátor v TradingView prejde bar v poradí `open → bližší extrém →
vzdialenejší extrém → close`. Pri pevnom SL/TP je to jedno, pri trailingu na tom
závisí všetko — či sa stop stihol posunúť skôr, než cena prišla po neho.

Reálny bar (2026-08-28 16:51, 3m): open 79 250,0, high 79 490,6, low 79 245,7. Low je
od openu 4,3 bodu, high 240,6 — cena teda šla najprv dole, trailing sa aktivoval až
na konci baru a obchod pokračoval ešte 6 minút. Bez tohto pravidla ho port zavrel
o 77,6 bodu nižšie.

Emulujú sa obe nohy baru vrátane návratu k `close` — inak vyjde raz výstup priskoro
a inokedy vôbec. Stráži to `ibs/tests/test_trailing.py`.

## Parita s TradingView (Aug 24 – Sep 4)

| # | vstup | TradingView | Freqtrade | PnL |
|---|---|---|---|---|
| 1 | 79 419,5 | → 79 538,3 | rovnaké | +118,8 |
| 2 | 79 022,0 | → 78 541,2 | rovnaké | −480,8 |
| 3 | 80 516,0 | → 80 458,9 | 80 516,1 → 80 459,0 | −57,1 |
| 4 | 78 110,3 | → 78 386,1 | rovnaké | +275,8 / +270,3 |
| 5 | 78 765,1 | → 78 822,3 (qty 2) | rovnaké | +114,4 |
| 6 | 79 250,0 | → 79 467,6 | rovnaké | +217,6 |

Štyri z týchto šiestich výstupov sú trailing. Spolu +188,7 (TV) proti +183,2 (FT);
rozdiel je funding pri obchode 4.

## Výsledok za rok

| | bez poplatkov (ako Pine) | reálne poplatky, peňaženka 10k |
|---|---|---|
| obchodov | 184 | 184 |
| trailing / TP / SL | 84 / 12 / 88 | 84 / 12 / 88 |
| winrate | 51,6 % | 37,0 % |
| PnL | +5 476 USDT hrubý | **−1 248,0 USDT** |
| ekvivalent na 10k účte | ≈ **+54,8 %** | **−12,48 %** |
| profit factor | **1,32** | 0,57 |
| max drawdown | — | 13,01 % |
| najdlhšia séria strát | 5 | 10 |

**Toto je zatiaľ najlepšia konfigurácia.** Hrubý profit factor 1,32 oproti 1,11 pri
RR 1 a Engulfingu vypnutom — potvrdzuje sa aj to, čo ukázal manuálny prieskum
v TradingView (Engulfing pridáva výraznú hodnotu, RR okolo 2,5).

### Poplatky ju stále prevážia

Break-even poplatok je **0,0140 % za stranu** proti 0,05 %, ktoré berie Binance.
Je to trojnásobne lepšie než pri RR 1 (0,0050 %), ale stále 3,6× pod skutočnou cenou
exekúcie. Za rok: 3,45 M USDT objemu → **1 729 USDT na poplatkoch** proti hrubému
zisku 486 USDT pri tejto veľkosti pozície.

Zaujímavé je, že trailing **nezvýšil** hrubý edge oproti behu bez neho (PF 1,32 vs
1,38 bez trailingu) — skracuje víťazov, ale zároveň ich chráni. Na poplatkoch je
horší, lebo víťazi sú menší.

## Ako to zopakovať

```bash
IBS_PROFILE=<profil s rrRatio 2.5 a vsetkymi 3 modelmi> \
.venv/bin/python -m freqtrade backtesting \
  --config platforms/freqtrade/config.binance.json \
  --userdir platforms/freqtrade/user_data --strategy IBSImbalanceStrategy \
  --timeframe-detail 1m --timerange 20250904-20260904 --cache none
```

Pre porovnanie s TradingView pridaj `--fee 0 --dry-run-wallet 400000`.
Report: `python -m ibs.tools.report`.
